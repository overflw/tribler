import datetime
from dataclasses import dataclass
from itertools import count
from types import SimpleNamespace

from ipv8.test.base import TestBase

from pony.orm import commit, db_session

from tribler_core.components.tag.community.tag_payload import TagOperation, TagOperationEnum
from tribler_core.components.tag.db.tag_db import SHOW_THRESHOLD, TagDatabase

# pylint: disable=protected-access

@dataclass
class Tag:
    name: str
    count: int = 1


class TestTagDB(TestBase):
    def setUp(self):
        super().setUp()
        self.db = TagDatabase()

    async def tearDown(self):
        if self._outcome.errors:
            self.dump_db()

        await super().tearDown()

    @db_session
    def dump_db(self):
        print('\nPeer:')
        self.db.instance.Peer.select().show()
        print('\nTorrent:')
        self.db.instance.Torrent.select().show()
        print('\nTag')
        self.db.instance.Tag.select().show()
        print('\nTorrentTag')
        self.db.instance.TorrentTag.select().show()
        print('\nTorrentTagOp')
        self.db.instance.TorrentTagOp.select().show()

    def create_torrent_tag(self, tag='tag', infohash=b'infohash'):
        tag = self.db._get_or_create(self.db.instance.Tag, name=tag)
        torrent = self.db._get_or_create(self.db.instance.Torrent, infohash=infohash)
        torrent_tag = self.db._get_or_create(self.db.instance.TorrentTag, tag=tag, torrent=torrent)

        return torrent_tag

    @staticmethod
    def create_operation(infohash=b'infohash', tag='tag', peer=b'', operation=TagOperationEnum.ADD, clock=0):
        return TagOperation(infohash=infohash, tag=tag, operation=operation, clock=clock, creator_public_key=peer)

    def add_operation(self, infohash=b'infohash', tag='tag', peer=b'', operation=TagOperationEnum.ADD,
                      is_local_peer=False, clock=None):
        operation = self.create_operation(infohash, tag, peer, operation, clock)
        operation.clock = clock or self.db.get_clock(operation) + 1
        assert self.db.add_tag_operation(operation, signature=b'', is_local_peer=is_local_peer)
        commit()

    def add_operation_set(self, dictionary):
        index = count(0)

        def generate_n_peer_names(n):
            for _ in range(n):
                yield f'peer{next(index)}'.encode('utf8')

        for infohash, tags in dictionary.items():
            for tag in tags:
                for peer in generate_n_peer_names(tag.count):
                    self.add_operation(infohash, tag.name, peer)

    @db_session
    async def test_get_or_create(self):
        # Test that function get_or_create() works as expected:
        # it gets an entity if the entity is exist and create the entity otherwise
        assert self.db.instance.Peer.select().count() == 0

        # test create
        peer = self.db._get_or_create(self.db.instance.Peer, public_key=b'123')
        commit()
        assert peer.public_key == b'123'
        assert self.db.instance.Peer.select().count() == 1

        # test get
        peer = self.db._get_or_create(self.db.instance.Peer, public_key=b'123')
        assert peer.public_key == b'123'
        assert self.db.instance.Peer.select().count() == 1

    @db_session
    async def test_update_counter_add(self):
        torrent_tag = self.create_torrent_tag()

        # let's update ADD counter
        torrent_tag.update_counter(TagOperationEnum.ADD, increment=1)
        assert torrent_tag.added_count == 1
        assert torrent_tag.removed_count == 0
        assert not torrent_tag.local_operation

    @db_session
    async def test_update_counter_remove(self):
        torrent_tag = self.create_torrent_tag()

        # let's update REMOVE counter
        torrent_tag.update_counter(TagOperationEnum.REMOVE, increment=1)
        assert torrent_tag.added_count == 0
        assert torrent_tag.removed_count == 1
        assert not torrent_tag.local_operation

    @db_session
    async def test_update_counter_local(self):
        torrent_tag = self.create_torrent_tag()

        # let's update local operation
        torrent_tag.update_counter(TagOperationEnum.REMOVE, increment=1, is_local_peer=True)
        assert torrent_tag.added_count == 0
        assert torrent_tag.removed_count == 1
        assert torrent_tag.local_operation == TagOperationEnum.REMOVE

    @db_session
    async def test_remote_add_tag_operation(self):
        def assert_all_tables_have_the_only_one_entity():
            assert self.db.instance.Peer.select().count() == 1
            assert self.db.instance.Torrent.select().count() == 1
            assert self.db.instance.TorrentTag.select().count() == 1
            assert self.db.instance.Tag.select().count() == 1
            assert self.db.instance.TorrentTagOp.select().count() == 1

        # add the first operation
        self.add_operation(b'infohash', 'tag', b'peer1')
        assert_all_tables_have_the_only_one_entity()

        # add the same operation
        self.add_operation(b'infohash', 'tag', b'peer1')
        assert_all_tables_have_the_only_one_entity()

        # add an operation from the past
        self.add_operation(b'infohash', 'tag', b'peer1', clock=0)
        assert_all_tables_have_the_only_one_entity()

        # add a duplicate operation but from the future
        self.add_operation(b'infohash', 'tag', b'peer1', clock=1000)
        assert_all_tables_have_the_only_one_entity()

        assert self.db.instance.TorrentTagOp.get().operation == TagOperationEnum.ADD
        assert self.db.instance.TorrentTag.get().added_count == 1
        assert self.db.instance.TorrentTag.get().removed_count == 0

        # add a unique operation from the future
        self.add_operation(b'infohash', 'tag', b'peer1', operation=TagOperationEnum.REMOVE, clock=1001)
        assert_all_tables_have_the_only_one_entity()
        assert self.db.instance.TorrentTagOp.get().operation == TagOperationEnum.REMOVE
        assert self.db.instance.TorrentTag.get().added_count == 0
        assert self.db.instance.TorrentTag.get().removed_count == 1

    @db_session
    async def test_remote_add_multiple_tag_operations(self):
        self.add_operation(b'infohash', 'tag', b'peer1')
        self.add_operation(b'infohash', 'tag', b'peer2')
        self.add_operation(b'infohash', 'tag', b'peer3')

        assert self.db.instance.TorrentTag.get().added_count == 3
        assert self.db.instance.TorrentTag.get().removed_count == 0

        self.add_operation(b'infohash', 'tag', b'peer2', operation=TagOperationEnum.REMOVE)
        assert self.db.instance.TorrentTag.get().added_count == 2
        assert self.db.instance.TorrentTag.get().removed_count == 1

        self.add_operation(b'infohash', 'tag', b'peer1', operation=TagOperationEnum.REMOVE)
        assert self.db.instance.TorrentTag.get().added_count == 1
        assert self.db.instance.TorrentTag.get().removed_count == 2

        self.add_operation(b'infohash', 'tag', b'peer1')
        assert self.db.instance.TorrentTag.get().added_count == 2
        assert self.db.instance.TorrentTag.get().removed_count == 1

    @db_session
    async def test_multiple_tags(self):
        self.add_operation_set(
            {
                b'infohash1': [
                    Tag(name='tag1', count=2),
                    Tag(name='tag2', count=2),
                    Tag(name='tag3', count=1),
                ],
                b'infohash2': [
                    Tag(name='tag1', count=1),
                    Tag(name='tag2', count=1),
                    Tag(name='tag4', count=1),
                    Tag(name='tag5', count=1),
                    Tag(name='tag6', count=1),
                ]
            }
        )

        def assert_entities_count():
            assert self.db.instance.Torrent.select().count() == 2
            assert self.db.instance.TorrentTag.select().count() == 8
            assert self.db.instance.Tag.select().count() == 6
            assert self.db.instance.TorrentTagOp.select().count() == 10

        assert_entities_count()

        torrent1 = self.db.instance.Torrent.get(infohash=b'infohash1')
        tag1 = self.db.instance.Tag.get(name='tag1')
        torrent_tag = self.db.instance.TorrentTag.get(torrent=torrent1, tag=tag1)
        assert torrent_tag.added_count == 2
        assert torrent_tag.removed_count == 0

    @db_session
    async def test_get_tags_added(self):
        self.add_operation_set(
            {
                b'infohash1': [
                    Tag(name='tag1', count=1),
                    Tag(name='tag2', count=2),
                    Tag(name='tag3', count=3),
                ]
            }
        )

        assert not self.db.get_tags(b'missed infohash')
        assert self.db.get_tags(b'infohash1') == ['tag3', 'tag2']

    @db_session
    async def test_get_tags_removed(self):
        self.add_operation_set(
            {
                b'infohash1': [
                    Tag(name='tag1', count=2),
                    Tag(name='tag2', count=2)
                ]
            }
        )

        self.add_operation(infohash=b'infohash1', tag='tag2', peer=b'4', operation=TagOperationEnum.REMOVE)

        assert self.db.get_tags(b'infohash1') == ['tag1']

    @db_session
    async def test_show_local_tags(self):
        # Test that locally added tags have a priority to show.
        # That means no matter of other peers opinions, locally added tag should be visible.
        self.add_operation(b'infohash1', 'tag1', b'peer1', operation=TagOperationEnum.REMOVE)
        self.add_operation(b'infohash1', 'tag1', b'peer2', operation=TagOperationEnum.REMOVE)
        assert not self.db.get_tags(b'infohash1')

        # test local add
        self.add_operation(b'infohash1', 'tag1', b'peer3', operation=TagOperationEnum.ADD, is_local_peer=True)
        assert self.db.get_tags(b'infohash1') == ['tag1']

    @db_session
    async def test_hide_local_tags(self):
        # Test that locally removed tags should not be visible to local user.
        # No matter of other peers opinions, locally removed tag should be not visible.
        self.add_operation(b'infohash1', 'tag1', b'peer1')
        self.add_operation(b'infohash1', 'tag1', b'peer2')
        assert self.db.get_tags(b'infohash1') == ['tag1']

        # test local remove
        self.add_operation(b'infohash1', 'tag1', b'peer3', operation=TagOperationEnum.REMOVE, is_local_peer=True)
        assert self.db.get_tags(b'infohash1') == []

    @db_session
    async def test_suggestions(self):
        # Test whether the database returns the right suggestions.
        # Suggestions are tags that have not gathered enough support for display yet.
        self.add_operation(tag='tag1', peer=b'1')
        assert self.db.get_suggestions(b'infohash') == ["tag1"]

        self.add_operation(tag='tag1', peer=b'2')
        assert self.db.get_suggestions(b'infohash') == []  # This tag now has enough support

        self.add_operation(tag='tag1', peer=b'3', operation=TagOperationEnum.REMOVE)  # score:1
        assert self.db.get_suggestions(b'infohash') == ["tag1"]

        self.add_operation(tag='tag1', peer=b'4', operation=TagOperationEnum.REMOVE)  # score:0
        self.add_operation(tag='tag1', peer=b'5', operation=TagOperationEnum.REMOVE)  # score:-1
        self.add_operation(tag='tag1', peer=b'6', operation=TagOperationEnum.REMOVE)  # score:-2
        assert not self.db.get_suggestions(b'infohash')  # below the threshold

    @db_session
    async def test_get_clock_of_operation(self):
        operation = self.create_operation(tag='tag1')
        assert self.db.get_clock(operation) == 0

        self.add_operation(infohash=operation.infohash, tag=operation.tag, peer=operation.creator_public_key, clock=1)
        assert self.db.get_clock(operation) == 1

    @db_session
    async def test_get_tags_operations_for_gossip(self):
        time_delta = {'minutes': 1}
        self.add_operation_set(
            {
                b'infohash1': [
                    Tag(name='tag1', count=1),
                    Tag(name='tag2', count=1)
                ]
            }
        )
        # assert that immediately added torrents are not returned
        assert not self.db.get_tags_operations_for_gossip(time_delta)

        tag_operation = self.db.instance.TorrentTagOp.select().first()
        tag_operation.updated_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=2)

        # assert that only one torrent returned (the old one)
        assert len(self.db.get_tags_operations_for_gossip(time_delta)) == 1

    @db_session
    async def test_get_infohashes(self):
        self.add_operation_set(
            {
                b'infohash1': [
                    Tag(name='tag1', count=2),
                    Tag(name='tag2', count=1)
                ],
                b'infohash2': [
                    Tag(name='tag1', count=2)
                ],
                b'infohash3': [
                    Tag(name='tag1', count=1)
                ]
            }
        )

        # test that only tags above the threshold are associated with infohases
        assert self.db.get_infohashes('tag1') == [b'infohash1', b'infohash2']
        assert not self.db.get_infohashes('tag2')

    @db_session
    async def test_show_condition(self):
        assert TagDatabase._show_condition(SimpleNamespace(local_operation=TagOperationEnum.ADD))
        assert TagDatabase._show_condition(SimpleNamespace(local_operation=None, score=SHOW_THRESHOLD))
        assert not TagDatabase._show_condition(SimpleNamespace(local_operation=None, score=0))
