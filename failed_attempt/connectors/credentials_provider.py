from __future__ import annotations

from typing import Any
from types import TracebackType
import os
import uuid
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

try:
	import redis  # type: ignore
except Exception:  # noqa: BLE001
	redis = None  # type: ignore

from connectors.onyx.connectors.interfaces import CredentialsProviderInterface  # type: ignore
from backend.db.models import Credential
from backend.security.crypto import maybe_decrypt_dict, encrypt_dict, needs_key_rotation, rotate_encryption
from backend.security.audit import AuditLogger

logger = logging.getLogger(__name__)


class DBCredentialsProvider(CredentialsProviderInterface["DBCredentialsProvider"]):
	"""Enhanced async-session friendly credentials provider with token refresh and audit logging."""

	def __init__(
		self, 
		tenant_id: str | None, 
		connector_name: str, 
		credential_id: str, 
		db: AsyncSession,
		audit_logger: AuditLogger | None = None
	):
		self._tenant_id = tenant_id
		self._connector_name = connector_name
		self._credential_id = credential_id
		self._db = db
		self._audit_logger = audit_logger or AuditLogger(db)
		self._lock: Any = None
		self._lock_key = f"gis:lock:connector:{connector_name}:cred:{credential_id}"
		self._redis = None
		self._credential_cache: Credential | None = None  # Cache the credential object
		
		if redis is not None:
			url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL")
			if url and url.startswith("redis://"):
				try:
					self._redis = redis.Redis.from_url(url)
				except Exception:  # noqa: BLE001
					self._redis = None

	def __enter__(self) -> "DBCredentialsProvider":
		if self._redis is not None:
			self._lock = self._redis.lock(self._lock_key, timeout=900)
			acquired = self._lock.acquire(blocking=True, blocking_timeout=900)
			if not acquired:
				raise RuntimeError(f"Could not acquire lock for key: {self._lock_key}")
		return self

	def __exit__(
		self,
		exc_type: type[BaseException] | None,
		exc_value: BaseException | None,
		traceback: TracebackType | None,
	) -> None:
		if self._lock is not None:
			try:
				self._lock.release()
			except Exception:  # noqa: BLE001
				pass

	def get_tenant_id(self) -> str | None:
		return self._tenant_id

	def get_provider_key(self) -> str:
		return str(self._credential_id)

	async def _get_credential(self) -> Credential:
		"""Get credential from database with caching."""
		if self._credential_cache is None:
			result = await self._db.execute(
				select(Credential).where(Credential.id == self._credential_id)
			)
			self._credential_cache = result.scalar_one()
		assert self._credential_cache is not None
		return self._credential_cache

	async def _update_credential_status(self, status: str, **kwargs) -> None:
		"""Update credential status and other fields."""
		update_data = {"status": status, "updated_at": datetime.utcnow()}
		update_data.update(kwargs)
		
		await self._db.execute(
			update(Credential)
			.where(Credential.id == self._credential_id)
			.values(**update_data)
		)
		await self._db.commit()
		
		# Invalidate cache
		self._credential_cache = None

	def get_credentials(self) -> dict[str, Any]:
		"""Get decrypted credentials with automatic refresh and rotation."""
		import asyncio
		
		async def _get_credentials_async() -> dict[str, Any]:
			try:
				cred = await self._get_credential()
				
				# Check if credential is expired or invalid
				if cred.status == "expired":
					await self._attempt_token_refresh(cred)
					cred = await self._get_credential()  # Refresh from DB
				
				# Check if encryption needs rotation
				if needs_key_rotation(cred.credential_json):
					logger.info("Rotating encryption for credential %s", cred.id)
					rotated_data = rotate_encryption(cred.credential_json)
					await self._db.execute(
						update(Credential)
						.where(Credential.id == cred.id)
						.values(
							credential_json=rotated_data,
							encryption_key_version=rotated_data.get("_enc_version", 1),
							updated_at=datetime.utcnow()
						)
					)
					await self._db.commit()
					cred.credential_json = rotated_data
				
				# Update last_used_at
				await self._db.execute(
					update(Credential)
					.where(Credential.id == cred.id)
					.values(last_used_at=datetime.utcnow())
				)
				await self._db.commit()
				
				# Audit log the access
				await self._audit_logger.log_credential_accessed(
					credential_id=cred.id,
					organization_id=cred.organization_id,
					result="success",
					context="connector_run"
				)
				
				decrypted = maybe_decrypt_dict(cred.credential_json)
				logger.debug("Retrieved credentials for connector %s", self._connector_name)
				return decrypted
				
			except Exception as e:
				logger.error("Failed to get credentials: %s", str(e))
				# Audit log the failure
				try:
					cred = await self._get_credential()
					await self._audit_logger.log_credential_accessed(
						credential_id=cred.id,
						organization_id=cred.organization_id,
						result="failure",
						context="connector_run"
					)
				except Exception:
					pass  # Don't fail on audit logging failure
				raise
		
		# Run async function in sync context
		try:
			# Check if a loop is running (no assignment to avoid lint warnings)
			asyncio.get_running_loop()
			# We're already in an event loop (e.g. inside worker/tests). Run in a thread.
			import concurrent.futures
			with concurrent.futures.ThreadPoolExecutor() as executor:
				future = executor.submit(asyncio.run, _get_credentials_async())
				return future.result()
		except RuntimeError:
			# No running loop, we can use asyncio.run
			return asyncio.run(_get_credentials_async())

	def set_credentials(self, credential_json: dict[str, Any]) -> None:
		"""Update credentials with encryption and audit logging."""
		import asyncio
		
		async def _set_credentials_async() -> None:
			try:
				cred = await self._get_credential()
				
				# Encrypt the new credentials
				encrypted_data = encrypt_dict(credential_json)
				
				# Update in database
				await self._db.execute(
					update(Credential)
					.where(Credential.id == cred.id)
					.values(
						credential_json=encrypted_data,
						encryption_key_version=encrypted_data.get("_enc_version", 1),
						status="active",
						updated_at=datetime.utcnow(),
						last_refreshed_at=datetime.utcnow(),
						refresh_attempts=0
					)
				)
				await self._db.commit()
				
				# Audit log the update
				await self._audit_logger.log_credential_updated(
					credential_id=cred.id,
					organization_id=cred.organization_id,
					user_id=cred.user_id,
					fields_updated=["credential_json"]
				)
				
				# Invalidate cache
				self._credential_cache = None
				
				logger.info("Updated credentials for connector %s", self._connector_name)
				
			except Exception as e:
				logger.error("Failed to set credentials: %s", str(e))
				await self._db.rollback()
				raise
		
		# Run async function in sync context
		try:
			# Check if a loop is running (no assignment to avoid lint warnings)
			asyncio.get_running_loop()
			import concurrent.futures
			with concurrent.futures.ThreadPoolExecutor() as executor:
				future = executor.submit(asyncio.run, _set_credentials_async())
				future.result()
		except RuntimeError:
			asyncio.run(_set_credentials_async())

	async def _attempt_token_refresh(self, cred: Credential) -> None:
		"""Attempt to refresh OAuth tokens if possible."""
		try:
			# Check if we've exceeded max refresh attempts
			if cred.refresh_attempts >= 3:
				logger.warning("Max refresh attempts exceeded for credential %s", cred.id)
				await self._update_credential_status("invalid")
				return
			
			decrypted_creds = maybe_decrypt_dict(cred.credential_json)
			
			# Check if this is an OAuth credential with refresh token
			if "refresh_token" not in decrypted_creds:
				logger.debug("No refresh token available for credential %s", cred.id)
				return
			
			# Try to refresh using the connector's OAuth capabilities
			from connectors.onyx.configs.constants import DocumentSource  # type: ignore
			from connectors.onyx.connectors.factory import identify_connector_class  # type: ignore
			from connectors.onyx.connectors.interfaces import OAuthConnector  # type: ignore
			
			try:
				src = getattr(DocumentSource, cred.connector_name.upper())
				conn_cls = identify_connector_class(src)
				
				if not issubclass(conn_cls, OAuthConnector):
					logger.debug("Connector %s does not support OAuth refresh", cred.connector_name)
					return
				
				# Attempt refresh (connector-specific; TODO: implement per provider)
				await self._db.execute(
					update(Credential)
					.where(Credential.id == cred.id)
					.values(
						refresh_attempts=cred.refresh_attempts + 1,
						last_refreshed_at=datetime.utcnow()
					)
				)
				await self._db.commit()
				
				# Audit log the refresh attempt
				await self._audit_logger.log_credential_refreshed(
					credential_id=cred.id,
					organization_id=cred.organization_id,
					result="attempted",
					error_message="Refresh not yet implemented for this connector"
				)
				
				logger.info("Token refresh attempted for credential %s", cred.id)
				
			except Exception as e:
				logger.error("Token refresh failed for credential %s: %s", cred.id, str(e))
				await self._update_credential_status(
					"expired",
					refresh_attempts=cred.refresh_attempts + 1,
					last_refreshed_at=datetime.utcnow()
				)
				
				await self._audit_logger.log_credential_refreshed(
					credential_id=cred.id,
					organization_id=cred.organization_id,
					result="failure",
					error_message=str(e)
				)
				
		except Exception as e:
			logger.error("Error during token refresh attempt: %s", str(e))

	def is_dynamic(self) -> bool:
		return True


class StaticCredentialsProvider(CredentialsProviderInterface["StaticCredentialsProvider"]):
	"""Static credentials provider for non-OAuth connectors."""
	
	def __init__(self, tenant_id: str | None, connector_name: str, credential_json: dict[str, Any]):
		self._tenant_id = tenant_id
		self._connector_name = connector_name
		self._credential_json = credential_json

	def __enter__(self) -> "StaticCredentialsProvider":
		return self

	def __exit__(
		self,
		exc_type: type[BaseException] | None,
		exc_value: BaseException | None,
		traceback: TracebackType | None,
	) -> None:
		pass

	def get_tenant_id(self) -> str | None:
		return self._tenant_id

	def get_provider_key(self) -> str:
		return "static"

	def get_credentials(self) -> dict[str, Any]:
		return self._credential_json

	def set_credentials(self, credential_json: dict[str, Any]) -> None:
		self._credential_json = credential_json

	def is_dynamic(self) -> bool:
		return False 