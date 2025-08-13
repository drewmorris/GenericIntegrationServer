import asyncio
import tempfile
import uuid
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import AsyncSessionLocal
from backend.db import models as m
from backend.orchestrator.tasks import sync_connector


async def _create_profile(session: AsyncSession, src_dir: str, dump_dir: str) -> m.ConnectorProfile:
	org_id = uuid.uuid4()
	user_id = uuid.uuid4()
	profile = m.ConnectorProfile(
		id=uuid.uuid4(),
		organization_id=org_id,
		user_id=user_id,
		name="File→CSV Profile",
		source="file",
		connector_config={
			"destination": "csvdump",
			"csvdump": {"dump_dir": dump_dir},
			"file": {"path": src_dir},
		},
	)
	session.add(profile)
	await session.commit()
	await session.refresh(profile)
	return profile


def test_file_connector_to_csvdump():
	async def _run():
		with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
			# create a sample text file
			p = Path(src) / "sample.txt"
			p.write_text("hello world")
			async with AsyncSessionLocal() as session:
				profile = await _create_profile(session, src, out)
				sync_connector.apply(args=[str(profile.id), str(profile.user_id), str(profile.organization_id)])
				files = list(Path(out).glob('*.json'))
				assert len(files) >= 1
	asyncio.get_event_loop().run_until_complete(_run()) 