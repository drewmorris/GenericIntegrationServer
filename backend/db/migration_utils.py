"""
Utility functions for migrating data between old and new CC-Pair architecture
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db import models as m
from backend.db import cc_pairs as cc_pair_ops
from backend.schemas.cc_pairs import ConnectorCreate, ConnectorCredentialPairCreate


async def migrate_connector_profiles_to_cc_pairs(
    db: AsyncSession,
    organization_id: Optional[uuid.UUID] = None,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Migrate existing ConnectorProfiles to the new CC-Pair architecture
    
    Args:
        db: Database session
        organization_id: Optional organization filter
        dry_run: If True, only simulate the migration without making changes
    
    Returns:
        Migration summary with counts and any errors
    """
    summary: Dict[str, Any] = {
        "profiles_processed": 0,
        "connectors_created": 0,
        "cc_pairs_created": 0,
        "errors": [],
        "dry_run": dry_run,
        "created_connectors": [],
        "created_cc_pairs": [],
        "skipped_profiles": []
    }
    
    try:
        # Get all ConnectorProfiles to migrate
        query = select(m.ConnectorProfile).options(
            selectinload(m.ConnectorProfile.organization),
            selectinload(m.ConnectorProfile.user)
        )
        
        if organization_id:
            query = query.where(m.ConnectorProfile.organization_id == organization_id)
        
        result = await db.execute(query)
        profiles = result.scalars().all()
        
        # Group profiles by (source, input_type, config) to create reusable connectors
        connector_groups: Dict[tuple, List[m.ConnectorProfile]] = {}
        
        for profile in profiles:
            # Determine input_type based on source (following legacy patterns)
            input_type = _determine_input_type(profile.source)
            
            # Create a key for grouping similar connectors
            config_key = _normalize_config_for_grouping(profile.connector_config or {})
            group_key = (profile.source, input_type, config_key)
            
            if group_key not in connector_groups:
                connector_groups[group_key] = []
            connector_groups[group_key].append(profile)
        
        summary["profiles_processed"] = len(profiles)
        
        # Create connectors and CC-Pairs
        for group_key, group_profiles in connector_groups.items():
            source, input_type, config_key = group_key
            
            # Use the first profile as the template for the connector
            template_profile = group_profiles[0]
            
            # Create connector name
            connector_name = f"{source.replace('_', ' ').title()} Connector"
            if len(group_profiles) > 1:
                connector_name += f" ({len(group_profiles)} profiles)"
            
            if not dry_run:
                # Create the connector
                connector_data = ConnectorCreate(
                    name=connector_name,
                    source=source,
                    input_type=input_type,
                    connector_specific_config=template_profile.connector_config or {},
                    refresh_freq=template_profile.interval_minutes * 60 if template_profile.interval_minutes else None,
                    prune_freq=None  # Not available in old profiles
                )
                
                connector = await cc_pair_ops.create_connector(db, connector_data)
                summary["connectors_created"] += 1
                summary["created_connectors"].append({
                    "id": connector.id,
                    "name": connector.name,
                    "source": connector.source,
                    "profiles_count": len(group_profiles)
                })
            else:
                # Simulate connector creation
                connector = type('MockConnector', (), {
                    'id': f"mock_{len(summary['created_connectors'])}",
                    'name': connector_name,
                    'source': source
                })()
                summary["created_connectors"].append({
                    "id": connector.id,
                    "name": connector.name,
                    "source": connector.source,
                    "profiles_count": len(group_profiles)
                })
            
            # Create CC-Pairs for each profile in the group
            for profile in group_profiles:
                if not profile.credential_id:
                    summary["skipped_profiles"].append({
                        "profile_id": str(profile.id),
                        "name": profile.name,
                        "reason": "No credential associated"
                    })
                    continue
                
                cc_pair_name = profile.name or f"{source} - {profile.user.email if profile.user else 'Unknown'}"
                
                if not dry_run:
                    cc_pair_data = ConnectorCredentialPairCreate(
                        name=cc_pair_name,
                        connector_id=connector.id,
                        credential_id=profile.credential_id,
                        destination_target_id=None,  # Migration: no destination initially
                        organization_id=profile.organization_id,
                        creator_id=profile.user_id,
                        status=m.ConnectorCredentialPairStatus.ACTIVE if profile.status == "active" else m.ConnectorCredentialPairStatus.PAUSED,
                        access_type=m.AccessType.PRIVATE,  # Default to private
                        auto_sync_options=None  # Not available in old profiles
                    )
                    
                    cc_pair = await cc_pair_ops.create_cc_pair(db, cc_pair_data)
                    summary["cc_pairs_created"] += 1
                    summary["created_cc_pairs"].append({
                        "id": cc_pair.id,
                        "name": cc_pair.name,
                        "connector_id": connector.id,
                        "profile_id": str(profile.id)
                    })
                else:
                    # Simulate CC-Pair creation
                    summary["cc_pairs_created"] += 1
                    summary["created_cc_pairs"].append({
                        "id": f"mock_{summary['cc_pairs_created']}",
                        "name": cc_pair_name,
                        "connector_id": connector.id,
                        "profile_id": str(profile.id)
                    })
        
        if not dry_run:
            await db.commit()
        
    except Exception as e:
        if not dry_run:
            await db.rollback()
        summary["errors"].append(f"Migration failed: {str(e)}")
    
    return summary


async def migrate_sync_runs_to_index_attempts(
    db: AsyncSession,
    organization_id: Optional[uuid.UUID] = None,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Migrate existing SyncRuns to IndexAttempts for CC-Pairs
    
    This should be run after migrate_connector_profiles_to_cc_pairs
    """
    summary: Dict[str, Any] = {
        "sync_runs_processed": 0,
        "index_attempts_created": 0,
        "errors": [],
        "dry_run": dry_run,
        "created_attempts": [],
        "skipped_runs": []
    }
    
    try:
        # Get all SyncRuns
        query = select(m.SyncRun).options(selectinload(m.SyncRun.profile))
        
        if organization_id:
            query = query.join(m.ConnectorProfile).where(
                m.ConnectorProfile.organization_id == organization_id
            )
        
        result = await db.execute(query)
        sync_runs = result.scalars().all()
        
        summary["sync_runs_processed"] = len(sync_runs)
        
        for sync_run in sync_runs:
            if not sync_run.profile:
                summary["skipped_runs"].append({
                    "sync_run_id": str(sync_run.id),
                    "reason": "Profile not found"
                })
                continue
            
            # Find the corresponding CC-Pair
            # This is a simplified approach - in practice, you might need a mapping table
            cc_pairs_result = await db.execute(
                select(m.ConnectorCredentialPair).where(
                    and_(
                        m.ConnectorCredentialPair.organization_id == sync_run.profile.organization_id,
                        m.ConnectorCredentialPair.credential_id == sync_run.profile.credential_id
                    )
                ).limit(1)
            )
            cc_pair = cc_pairs_result.scalar_one_or_none()
            
            if not cc_pair:
                summary["skipped_runs"].append({
                    "sync_run_id": str(sync_run.id),
                    "reason": "No corresponding CC-Pair found"
                })
                continue
            
            if not dry_run:
                # Create IndexAttempt
                index_attempt = m.IndexAttempt(
                    connector_credential_pair_id=cc_pair.id,
                    status=_convert_sync_status_to_indexing_status(sync_run.status),
                    from_beginning=False,  # Assume incremental
                    new_docs_indexed=sync_run.records_synced or 0,
                    total_docs_indexed=sync_run.records_synced or 0,
                    docs_removed_from_index=0,
                    time_created=sync_run.started_at,
                    time_started=sync_run.started_at,
                    time_updated=sync_run.finished_at or sync_run.started_at
                )
                
                db.add(index_attempt)
                await db.flush()
                await db.refresh(index_attempt)
                
                summary["index_attempts_created"] += 1
                summary["created_attempts"].append({
                    "id": index_attempt.id,
                    "cc_pair_id": cc_pair.id,
                    "sync_run_id": str(sync_run.id),
                    "status": index_attempt.status.value
                })
            else:
                summary["index_attempts_created"] += 1
                summary["created_attempts"].append({
                    "id": f"mock_{summary['index_attempts_created']}",
                    "cc_pair_id": cc_pair.id,
                    "sync_run_id": str(sync_run.id),
                    "status": _convert_sync_status_to_indexing_status(sync_run.status).value
                })
        
        if not dry_run:
            await db.commit()
        
    except Exception as e:
        if not dry_run:
            await db.rollback()
        summary["errors"].append(f"SyncRun migration failed: {str(e)}")
    
    return summary


def _determine_input_type(source: str) -> str:
    """Determine InputType based on connector source"""
    # Based on legacy patterns
    polling_sources = {"slack", "gmail", "zulip", "teams", "discord"}
    
    if source.lower() in polling_sources:
        return "POLL"
    else:
        return "LOAD_STATE"


def _normalize_config_for_grouping(config: Dict[str, Any]) -> str:
    """Create a normalized string representation of config for grouping"""
    # Remove user-specific or instance-specific fields
    normalized = {}
    
    # Keep only structural configuration, not credentials or user-specific data
    exclude_keys = {
        "access_token", "api_token", "api_key", "password", "secret",
        "client_id", "client_secret", "refresh_token", "oauth_token",
        "user_id", "email", "username"
    }
    
    for key, value in config.items():
        if key.lower() not in exclude_keys:
            normalized[key] = value
    
    # Sort keys for consistent grouping
    return str(sorted(normalized.items()))


def _convert_sync_status_to_indexing_status(sync_status: str) -> m.IndexingStatus:
    """Convert old SyncStatus to new IndexingStatus"""
    status_mapping = {
        "pending": m.IndexingStatus.NOT_STARTED,
        "running": m.IndexingStatus.IN_PROGRESS,
        "success": m.IndexingStatus.SUCCESS,
        "failure": m.IndexingStatus.FAILED
    }
    
    return status_mapping.get(sync_status.lower(), m.IndexingStatus.FAILED)


async def get_migration_preview(
    db: AsyncSession,
    organization_id: Optional[uuid.UUID] = None
) -> Dict[str, Any]:
    """
    Get a preview of what would be migrated without making changes
    """
    profile_summary = await migrate_connector_profiles_to_cc_pairs(
        db, organization_id, dry_run=True
    )
    
    sync_run_summary = await migrate_sync_runs_to_index_attempts(
        db, organization_id, dry_run=True
    )
    
    return {
        "connector_profiles": profile_summary,
        "sync_runs": sync_run_summary,
        "total_profiles": profile_summary["profiles_processed"],
        "total_sync_runs": sync_run_summary["sync_runs_processed"],
        "estimated_connectors": profile_summary["connectors_created"],
        "estimated_cc_pairs": profile_summary["cc_pairs_created"],
        "estimated_index_attempts": sync_run_summary["index_attempts_created"]
    }
