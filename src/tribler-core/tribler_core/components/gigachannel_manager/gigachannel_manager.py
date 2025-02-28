import asyncio
from asyncio import CancelledError, wait_for
from pathlib import Path

from ipv8.taskmanager import TaskManager, task

from pony.orm import db_session

from tribler_common.simpledefs import DLSTATUS_SEEDING, NTFY

from tribler_core.components.libtorrent.download_manager.download_config import DownloadConfig
from tribler_core.components.libtorrent.download_manager.download_manager import DownloadManager
from tribler_core.components.libtorrent.torrentdef import TorrentDef
from tribler_core.components.metadata_store.db.orm_bindings.channel_node import COMMITTED
from tribler_core.components.metadata_store.db.serialization import CHANNEL_TORRENT
from tribler_core.components.metadata_store.db.store import MetadataStore
from tribler_core.notifier import Notifier
from tribler_core.utilities.unicode import hexlify

PROCESS_CHANNEL_DIR = 1
REMOVE_CHANNEL_DOWNLOAD = 2
CLEANUP_UNSUBSCRIBED_CHANNEL = 3


class GigaChannelManager(TaskManager):
    """
    This class represents the main manager for gigachannels.
    It provides methods to manage channels, download new channels or remove existing ones.
    """

    def __init__(
        self,
        state_dir: Path = None,
        metadata_store: MetadataStore = None,
        notifier: Notifier = None,
        download_manager: DownloadManager = None,
    ):
        super().__init__()
        self.notifier = notifier
        self.download_manager = download_manager
        self.mds = metadata_store
        self.state_dir = state_dir

        # We queue up processing of the channels because we do it in a separate thread, and we don't want
        # to run more that one of these simultaneously
        self.channels_processing_queue = {}
        self.processing = False

    def start(self):
        """
        The Metadata Store checks the database at regular intervals to see if new channels are available for preview
        or subscribed channels require updating.
        """

        self.register_task("Check and regen personal channels", self.check_and_regen_personal_channels)

        channels_check_interval = 5.0  # seconds
        self.register_task(
            "Process channels download queue and remove cruft", self.service_channels, interval=channels_check_interval
        )

    async def check_and_regen_personal_channels(self):
        # Test if our channels are there, but we don't share these because Tribler was closed unexpectedly
        try:
            with db_session:
                for channel in self.mds.ChannelMetadata.get_my_channels().where(lambda g: g.status == COMMITTED):
                    channel_download = self.download_manager.get_download(bytes(channel.infohash))
                    if channel_download is None:
                        self._logger.warning(
                            "Torrent for personal channel %s %i does not exist.",
                            hexlify(channel.public_key),
                            channel.id_,
                        )
                        self.regenerate_channel_torrent(channel.public_key, channel.id_)
                    else:
                        self.register_task(
                            f"Check personal channel {hexlify(channel.public_key), channel.id_}",
                            self.check_and_regen_personal_channel_torrent,
                            channel.public_key,
                            channel.id_,
                            channel_download,
                        )
        except Exception:
            self._logger.exception("Error when tried to resume personal channel seeding on GigaChannel Manager startup")

    @task
    async def regenerate_channel_torrent(self, channel_pk, channel_id):
        self._logger.info("Regenerating personal channel %s %i", hexlify(channel_pk), channel_id)
        with db_session:
            channel = self.mds.ChannelMetadata.get(public_key=channel_pk, id_=channel_id)
            if channel is None:
                self._logger.warning("Tried to regenerate non-existing channel %s %i", hexlify(channel_pk), channel_id)
                return None
            channel_dirname = channel.dirname
        for d in self.download_manager.get_downloads_by_name(channel_dirname):
            await self.download_manager.remove_download(d, remove_content=True)
        with db_session:
            channel = self.mds.ChannelMetadata.get_for_update(public_key=channel_pk, id_=channel_id)
            regenerated = channel.consolidate_channel_torrent()
            # If the user created their channel, but added no torrents to it,
            # the channel torrent will not be created.
            if regenerated is None:
                return None
        tdef = TorrentDef.load_from_dict(regenerated)
        self.updated_my_channel(tdef)
        return tdef

    async def check_and_regen_personal_channel_torrent(self, channel_pk, channel_id, channel_download, timeout=60):
        try:
            await wait_for(channel_download.wait_for_status(DLSTATUS_SEEDING), timeout=timeout)
        except asyncio.TimeoutError:
            self._logger.warning("Time out waiting for personal channel %s %i to seed", hexlify(channel_pk), channel_id)
            await self.regenerate_channel_torrent(channel_pk, channel_id)

    async def shutdown(self):
        """
        Stop the gigachannel manager.
        """
        await self.shutdown_task_manager()

    def remove_cruft_channels(self):
        """
        Assembles a list of obsolete channel torrents to be removed.
        The list is formed from older versions of channels we are subscribed to and from channel torrents we are not
        subscribed to (i.e. we recently unsubscribed from these). The unsubscribed channels are removed completely
        with their contents, while in the case of older versions the files are left in place because the newer version
        possibly uses them.
        :return: list of tuples (download_to_remove=download, remove_files=Bool)
        """
        with db_session:
            # FIXME: if someone is subscribed to more than 1000 channels, they are in trouble...
            channels = self.mds.get_entries(last=1000, subscribed=True, metadata_type=CHANNEL_TORRENT)
            subscribed_infohashes = [bytes(c.infohash) for c in list(channels)]
            dirnames = [c.dirname for c in channels]

        # TODO: add some more advanced logic for removal of older channel versions
        cruft_list = [
            (d, d.get_def().get_name_utf8() not in dirnames)
            for d in self.download_manager.get_channel_downloads()
            if bytes(d.get_def().infohash) not in subscribed_infohashes
        ]

        for d, remove_content in cruft_list:
            self.channels_processing_queue[d.get_def().infohash] = (REMOVE_CHANNEL_DOWNLOAD, (d, remove_content))

    async def service_channels(self):
        if self.processing:
            return
        try:
            self.clean_unsubscribed_channels()
        except Exception:
            self._logger.exception("Error when deleting unsubscribed channels")
        try:
            self.remove_cruft_channels()
        except Exception:
            self._logger.exception("Error when tried to check for cruft channels")
        try:
            self.check_channels_updates()
        except Exception:
            self._logger.exception("Error when checking for channel updates")
        try:
            self.process_queued_channels()
        except Exception:
            self._logger.exception("Error when tried to start processing queued channel torrents changes")

    @task
    async def process_queued_channels(self):
        self.processing = True
        while self.channels_processing_queue:
            infohash, (action, data) = next(iter(self.channels_processing_queue.items()))
            self.channels_processing_queue.pop(infohash)
            if action == PROCESS_CHANNEL_DIR:
                await self.process_channel_dir_threaded(data)  # data is a channel object (used read-only!)
            elif action == REMOVE_CHANNEL_DOWNLOAD:
                await self.remove_channel_download(data)  # data is a tuple (download, remove_content bool)
            elif action == CLEANUP_UNSUBSCRIBED_CHANNEL:
                self.cleanup_channel(data)  # data is a tuple (public_key, id_)
        self.processing = False

    def check_channels_updates(self):
        """
        Check whether there are channels that are updated. If so, download the new version of the channel.
        """
        # FIXME: These naughty try-except-pass workarounds are necessary to keep the loop going in all circumstances

        with db_session:
            channels = list(self.mds.ChannelMetadata.get_updated_channels())

        for channel in channels:
            try:
                if self.download_manager.metainfo_requests.get(bytes(channel.infohash)):
                    continue
                if not self.download_manager.download_exists(bytes(channel.infohash)):
                    self._logger.info(
                        "Downloading new channel version %s ver %i->%i",
                        channel.dirname,
                        channel.local_version,
                        channel.timestamp,
                    )
                    self.download_channel(channel)
                elif (
                    self.download_manager.get_download(bytes(channel.infohash)).get_state().get_status()
                    == DLSTATUS_SEEDING
                ):
                    self._logger.info(
                        "Processing previously downloaded, but unprocessed channel torrent %s ver %i->%i",
                        channel.dirname,
                        channel.local_version,
                        channel.timestamp,
                    )
                    self.channels_processing_queue[channel.infohash] = (PROCESS_CHANNEL_DIR, channel)
            except Exception:
                self._logger.exception(
                    "Error when tried to download a newer version of channel %s", hexlify(channel.public_key)
                )

    async def remove_channel_download(self, to_remove):
        """
        :param to_remove: a tuple (download_to_remove=download, remove_files=Bool)
        """

        # TODO: make file removal from older versions safe (i.e. check if it overlaps with newer downloads)

        """
        files_to_remove = []
        for download in to_remove_list:
            files_to_remove.extend(self.safe_files_to_remove(download))
        """

        d, remove_content = to_remove
        try:
            await self.download_manager.remove_download(d, remove_content=remove_content)
        except Exception as e:
            self._logger.error("Error when removing the channel download: %s", e)

        """
        def _on_torrents_removed(torrent):
            print files_to_remove
        dl = DeferredList(removed_list)
        dl.addCallback(_on_torrents_removed)
        self.register_task(u'remove_channels_files-' + "_".join([d.tdef.get_name_utf8() for d in to_remove_list]), dl)
        """

    @task
    async def download_channel(self, channel):
        """
        Download a channel with a given infohash and title.
        :param channel: The channel metadata ORM object.
        """

        metainfo = await self.download_manager.get_metainfo(bytes(channel.infohash), timeout=60, hops=0)
        if metainfo is None:
            # Timeout looking for the channel metainfo. Probably, there are no seeds.
            # TODO: count the number of tries we had with the channel, so we can stop trying eventually
            return
        try:
            if metainfo[b'info'][b'name'].decode('utf-8') != channel.dirname:
                # Malformed channel
                # TODO: stop trying to download this channel until it is updated with a new infohash
                return
        except (KeyError, TypeError):
            return

        dcfg = DownloadConfig(state_dir=self.state_dir)
        dcfg.set_dest_dir(self.mds.channels_dir)
        dcfg.set_channel_download(True)
        tdef = TorrentDef(metainfo=metainfo)

        download = self.download_manager.start_download(tdef=tdef, config=dcfg, hidden=True)
        try:
            await download.future_finished
        except CancelledError:
            pass
        else:
            self.channels_processing_queue[channel.infohash] = (PROCESS_CHANNEL_DIR, channel)
        return download

    async def process_channel_dir_threaded(self, channel):
        mds: MetadataStore = self.mds

        def _process_download():
            channel_dirname = mds.get_channel_dir_path(channel)
            mds.process_channel_dir(channel_dirname, channel.public_key, channel.id_, external_thread=True)

        try:
            await mds.run_threaded(_process_download)
        except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
            self._logger.error("Error when processing channel dir download: %s", e)

        with db_session:
            updated_channel = self.mds.ChannelMetadata.get(public_key=channel.public_key, id_=channel.id_)
            channel_dict = updated_channel.to_simple_dict() if updated_channel else None
        if updated_channel:
            self.notifier.notify(NTFY.CHANNEL_ENTITY_UPDATED.value, channel_dict)

    def updated_my_channel(self, tdef):
        """
        Notify the core that we updated our channel.
        """
        with db_session:
            my_channel = self.mds.ChannelMetadata.get(infohash=tdef.get_infohash())
        if (
            my_channel
            and my_channel.status == COMMITTED
            and not self.download_manager.download_exists(bytes(my_channel.infohash))
        ):
            dcfg = DownloadConfig(state_dir=self.state_dir)
            dcfg.set_dest_dir(self.mds.channels_dir)
            dcfg.set_channel_download(True)
            return self.download_manager.start_download(tdef=tdef, config=dcfg)

    @db_session
    def clean_unsubscribed_channels(self):

        unsubscribed_list = list(
            self.mds.ChannelMetadata.select(
                lambda g: not g.subscribed and g.local_version > 0 and g.metadata_type == CHANNEL_TORRENT
            )
        )  # do not delete `g.metadata_type == CHANNEL_TORRENT` condition, it is used by partial index!

        for channel in unsubscribed_list:
            self.channels_processing_queue[channel.infohash] = (
                CLEANUP_UNSUBSCRIBED_CHANNEL,
                (channel.public_key, channel.id_),
            )

    def cleanup_channel(self, to_cleanup):
        public_key, id_ = to_cleanup
        # TODO: Maybe run it threaded?
        try:
            with db_session:
                channel = self.mds.ChannelMetadata.get_for_update(public_key=public_key, id_=id_)
                if not channel:
                    return
                channel.local_version = 0
                channel.contents.delete(bulk=True)
        except Exception as e:
            self._logger.warning("Exception while cleaning unsubscribed channel: %", str(e))
