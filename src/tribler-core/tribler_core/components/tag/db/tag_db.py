import datetime
import logging
from typing import List, Optional

from pony import orm

from tribler_core.components.tag.community.tag_payload import TagOperationEnum, TagOperation
from tribler_core.utilities.unicode import hexlify


class TagDatabase:
    def __init__(self, filename: Optional[str] = None):
        self.instance = orm.Database()
        self.define_binding(self.instance)
        self.instance.bind('sqlite', filename or ':memory:', create_db=True)
        self.instance.generate_mapping(create_tables=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def define_binding(db):
        class LocalPeer(db.Entity):  # pylint: disable=unused-variable
            counter = orm.Required(int, default=0, size=64)

        class Peer(db.Entity):
            id = orm.PrimaryKey(int, auto=True)
            public_key = orm.Required(bytes, unique=True)
            added_at = orm.Optional(datetime.datetime, default=datetime.datetime.utcnow)
            operations = orm.Set(lambda: TorrentTagOp)

        class Torrent(db.Entity):
            id = orm.PrimaryKey(int, auto=True)
            infohash = orm.Required(bytes, unique=True)
            tags = orm.Set(lambda: TorrentTag)

        class TorrentTag(db.Entity):
            id = orm.PrimaryKey(int, auto=True)
            torrent = orm.Required(lambda: Torrent)
            tag = orm.Required(lambda: Tag)
            operations = orm.Set(lambda: TorrentTagOp)

            added_count = orm.Required(int, default=0)
            removed_count = orm.Required(int, default=0)

            local_operation = orm.Optional(int)  # in case user don't (or do) want to see it locally

            orm.composite_key(torrent, tag)

            def update_counter(self, operation: TagOperationEnum, increment: int = 1, is_local_peer: bool = False):
                """ Update TorrentTag's counter
                Args:
                    operation: Tag operation
                    increment:
                    is_local_peer: The flag indicates whether do we performs operations from a local user or from
                        a remote user. In case of the local user, his operations will be considered as
                        authoritative for his (only) local Tribler instance.

                Returns:
                """
                if is_local_peer:
                    self.local_operation = operation
                if operation == TagOperationEnum.ADD:
                    self.added_count += increment
                if operation == TagOperationEnum.REMOVE:
                    self.removed_count += increment

        class Tag(db.Entity):
            id = orm.PrimaryKey(int, auto=True)
            name = orm.Required(str, unique=True)
            torrents = orm.Set(lambda: TorrentTag)

        class TorrentTagOp(db.Entity):
            id = orm.PrimaryKey(int, auto=True)

            torrent_tag = orm.Required(lambda: TorrentTag)
            peer = orm.Required(lambda: Peer)

            operation = orm.Required(int)
            timestamp = orm.Required(int)
            signature = orm.Required(bytes)
            updated_at = orm.Required(datetime.datetime, default=datetime.datetime.utcnow)

            orm.composite_key(torrent_tag, peer)

    @staticmethod
    def _get_or_create(cls, create_kwargs=None, **kwargs):  # pylint: disable=bad-staticmethod-argument
        """Get or create db entity.
        Args:
            cls: Entity's class, eg: `self.instance.Peer`
            create_kwargs: Additional arguments for creating new entity
            **kwargs: Arguments for selecting or for creating in case of missing entity

        Returns: Entity's instance
        """
        obj = cls.get_for_update(**kwargs)
        if not obj:
            if create_kwargs:
                kwargs.update(create_kwargs)
            obj = cls(**kwargs)
        return obj

    def add_tag_operation(self, operation: TagOperation, signature: bytes, is_local_peer: bool = False):
        """ Add the operation that will be applied to the tag.
        Args:
            operation: the class describes the adding operation
            signature: the signature of the operation
            is_local_peer: local operations processes differently than remote operations. They affects
                `TorrentTag.local_operation` field which is used in `self.get_tags()` function.

        Returns:
        """
        self.logger.debug(f'Add tag operation. Infohash: {hexlify(operation.infohash)}, tag: {operation.tag}')
        peer = self._get_or_create(self.instance.Peer, public_key=operation.creator_public_key)
        tag = self._get_or_create(self.instance.Tag, name=operation.tag)
        torrent = self._get_or_create(self.instance.Torrent, infohash=operation.infohash)
        torrent_tag = self._get_or_create(self.instance.TorrentTag, tag=tag, torrent=torrent)
        op = self.instance.TorrentTagOp.get_for_update(torrent_tag=torrent_tag, peer=peer)

        if not op:  # then insert
            self.instance.TorrentTagOp(torrent_tag=torrent_tag, peer=peer, operation=operation.operation,
                                       timestamp=operation.timestamp, signature=signature)
            torrent_tag.update_counter(operation.operation, is_local_peer=is_local_peer)
            return

        # if it is a message from the past, then return
        if operation.timestamp <= op.timestamp:
            return

        # To prevent endless incrementing of the operation, we apply the following logic:

        # 1. Decrement previous operation
        torrent_tag.update_counter(op.operation, increment=-1, is_local_peer=is_local_peer)
        # 2. Increment new operation
        torrent_tag.update_counter(operation.operation, is_local_peer=is_local_peer)
        # 3. Update the operation entity
        op.set(operation=operation.operation, timestamp=operation.timestamp, signature=signature,
               updated_at=datetime.datetime.utcnow())

    def get_tags(self, infohash: bytes) -> List[str]:
        """ Get all tags for this particular torrent.

        Returns: A list of tags
        """
        self.logger.debug(f'Get tags. Infohash: {hexlify(infohash)}')

        torrent = self.instance.Torrent.get(infohash=infohash)
        if not torrent:
            return []

        def show_condition(torrent_tag):
            return torrent_tag.local_operation == TagOperationEnum.ADD.value or \
                   not torrent_tag.local_operation and torrent_tag.added_count >= 2

        query = torrent.tags.select(show_condition)
        query = orm.select(tt.tag.name for tt in query)
        return list(query)

    def get_next_operation_counter(self) -> int:
        """ Get counter of last operation and increment this counter in DB.
        Returns: Counter that represented by integer (starts from 1).
        """
        local_peer = self._get_or_create(self.instance.LocalPeer)
        next_operation_counter = local_peer.counter + 1
        local_peer.set(counter=next_operation_counter)

        return next_operation_counter

    def get_tags_operations_for_gossip(self, time_delta, count: int = 10) -> List:
        """ Get random operations from the DB that older than time_delta.

        Args:
            time_delta: a dictionary for `datetime.timedelta`
            count: a limit for a resulting query
        """
        updated_at = datetime.datetime.utcnow() - datetime.timedelta(**time_delta)
        return list(self.instance.TorrentTagOp
                    .select(lambda tto: tto.updated_at <= updated_at)
                    .random(count))

    def shutdown(self) -> None:
        self.instance.disconnect()