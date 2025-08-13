import asyncio
import sys
import types
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import AsyncSessionLocal
from backend.db import models as m
from backend.orchestrator.tasks import sync_connector


class _StubCheckpoint:
	def __init__(self, val: str):
		self.val = val
	def model_dump(self):
		return {"val": self.val}


class _StubConnector:
	def __init__(self, **kwargs):
		self.kwargs = kwargs
	def load_credentials(self, creds):
		self.creds = creds
	def validate_checkpoint_json(self, s: str):
		# Accept any json string
		return _StubCheckpoint("parsed")


class _StubRunner:
	def __init__(self, connector, batch_size=10, include_permissions=False, time_range=None):
		self.connector = connector
	def run(self, checkpoint):
		# yield one batch and return checkpoint
		batch = [{"id": str(uuid.uuid4()), "raw_text": "stub"}]
		yield (batch, None, _StubCheckpoint("next"))


async def _create_profile(session: AsyncSession) -> m.ConnectorProfile:
	org_id = uuid.uuid4()
	user_id = uuid.uuid4()
	profile = m.ConnectorProfile(
		id=uuid.uuid4(),
		organization_id=org_id,
		user_id=user_id,
		name="Stub Profile",
		source="test_stub",
		connector_config={"destination": "csv"},
	)
	session.add(profile)
	await session.commit()
	await session.refresh(profile)
	return profile


def test_stub_checkpoint_persistence(monkeypatch):
	# Monkeypatch the onyx modules used by orchestrator
	factory_mod = types.ModuleType('connectors.onyx.connectors.factory')
	def _identify(source, *args, **kwargs):
		return _StubConnector
	factory_mod.identify_connector_class = _identify
	sys.modules['connectors.onyx.connectors.factory'] = factory_mod

	runner_mod = types.ModuleType('connectors.onyx.connectors.connector_runner')
	runner_mod.ConnectorRunner = _StubRunner
	sys.modules['connectors.onyx.connectors.connector_runner'] = runner_mod

	const_mod = types.ModuleType('connectors.onyx.configs.constants')
	class _DS(str):
		pass
	def _getattr(name):
		return type('DS', (), {'value': 'test_stub'})
	class _DocumentSource:
		TEST_STUB = 'test_stub'
	const_mod.DocumentSource = type('DocumentSource', (), {})
	setattr(const_mod.DocumentSource, 'TEST_STUB', 'test_stub')
	def _docsrc_getattr(attr):
		return 'test_stub'
	setattr(const_mod, 'DocumentSource', types.SimpleNamespace(**{'TEST_STUB': 'test_stub'}))
	# get attribute upper lookup will map to 'TEST_STUB'
	sys.modules['connectors.onyx.configs.constants'] = const_mod

	async def _run():
		async with AsyncSessionLocal() as session:
			profile = await _create_profile(session)
			# Run sync task
			sync_connector.apply(args=[str(profile.id), str(profile.user_id), str(profile.organization_id)])
			refreshed = (await session.execute(select(m.ConnectorProfile).where(m.ConnectorProfile.id == profile.id))).scalar_one()
			assert refreshed.checkpoint_json is not None
			assert refreshed.checkpoint_json.get('val') == 'next'
	asyncio.get_event_loop().run_until_complete(_run()) 