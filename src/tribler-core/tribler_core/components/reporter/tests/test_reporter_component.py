import pytest

from tribler_core.components.base import Session
from tribler_core.components.key.key_component import KeyComponent
from tribler_core.components.reporter.reporter_component import ReporterComponent

pytestmark = pytest.mark.asyncio


# pylint: disable=protected-access
async def test_reporter_component(tribler_config):
    components = [KeyComponent(), ReporterComponent()]
    session = Session(tribler_config, components)
    with session:
        await session.start()

        comp = ReporterComponent.instance()
        assert comp.started_event.is_set() and not comp.failed

        await session.shutdown()
