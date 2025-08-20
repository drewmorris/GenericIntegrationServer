"""
API routes for data migration between old and new CC-Pair architecture
"""
from __future__ import annotations

import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.db import models as m
from backend.db.migration_utils import (
    migrate_connector_profiles_to_cc_pairs,
    migrate_sync_runs_to_index_attempts,
    get_migration_preview
)
from backend.deps import get_current_user, get_current_org_id

router = APIRouter(prefix="/migration", tags=["Migration"])


@router.get("/preview")
async def preview_migration(
    organization_only: bool = Query(True, description="Only preview for current organization"),
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> Dict[str, Any]:
    """
    Preview what would be migrated from ConnectorProfiles to CC-Pairs
    """
    org_id = uuid.UUID(current_org_id) if organization_only else None
    
    try:
        preview = await get_migration_preview(db, org_id)
        return preview
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate migration preview: {str(e)}"
        )


@router.post("/profiles-to-cc-pairs")
async def migrate_profiles_to_cc_pairs(
    dry_run: bool = Query(True, description="Perform dry run without making changes"),
    organization_only: bool = Query(True, description="Only migrate current organization"),
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> Dict[str, Any]:
    """
    Migrate ConnectorProfiles to the new CC-Pair architecture
    """
    # Only allow admins to perform actual migrations
    if not dry_run and current_user.role not in [m.UserRole.ADMIN, m.UserRole.GLOBAL_CURATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform actual migrations"
        )
    
    org_id = uuid.UUID(current_org_id) if organization_only else None
    
    try:
        result = await migrate_connector_profiles_to_cc_pairs(db, org_id, dry_run)
        
        if not dry_run and result["errors"]:
            # If there were errors in a real migration, this is serious
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration completed with errors: {result['errors']}"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )


@router.post("/sync-runs-to-index-attempts")
async def migrate_sync_runs_to_index_attempts_endpoint(
    dry_run: bool = Query(True, description="Perform dry run without making changes"),
    organization_only: bool = Query(True, description="Only migrate current organization"),
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> Dict[str, Any]:
    """
    Migrate SyncRuns to IndexAttempts for CC-Pairs
    
    Note: This should be run after migrating profiles to CC-Pairs
    """
    # Only allow admins to perform actual migrations
    if not dry_run and current_user.role not in [m.UserRole.ADMIN, m.UserRole.GLOBAL_CURATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform actual migrations"
        )
    
    org_id = uuid.UUID(current_org_id) if organization_only else None
    
    try:
        result = await migrate_sync_runs_to_index_attempts(db, org_id, dry_run)
        
        if not dry_run and result["errors"]:
            # If there were errors in a real migration, this is serious
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration completed with errors: {result['errors']}"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )


@router.post("/full-migration")
async def perform_full_migration(
    dry_run: bool = Query(True, description="Perform dry run without making changes"),
    organization_only: bool = Query(True, description="Only migrate current organization"),
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> Dict[str, Any]:
    """
    Perform complete migration from old architecture to CC-Pairs
    
    This migrates both ConnectorProfiles and SyncRuns in sequence
    """
    # Only allow admins to perform actual migrations
    if not dry_run and current_user.role not in [m.UserRole.ADMIN, m.UserRole.GLOBAL_CURATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform actual migrations"
        )
    
    org_id = uuid.UUID(current_org_id) if organization_only else None
    
    try:
        # Step 1: Migrate ConnectorProfiles to CC-Pairs
        profiles_result = await migrate_connector_profiles_to_cc_pairs(db, org_id, dry_run)
        
        if profiles_result["errors"]:
            return {
                "status": "failed",
                "step": "profiles_to_cc_pairs",
                "profiles_migration": profiles_result,
                "sync_runs_migration": None,
                "error": "Profile migration failed, aborting full migration"
            }
        
        # Step 2: Migrate SyncRuns to IndexAttempts
        sync_runs_result = await migrate_sync_runs_to_index_attempts(db, org_id, dry_run)
        
        overall_status = "success" if not sync_runs_result["errors"] else "partial_success"
        
        return {
            "status": overall_status,
            "profiles_migration": profiles_result,
            "sync_runs_migration": sync_runs_result,
            "summary": {
                "total_profiles_processed": profiles_result["profiles_processed"],
                "total_connectors_created": profiles_result["connectors_created"],
                "total_cc_pairs_created": profiles_result["cc_pairs_created"],
                "total_sync_runs_processed": sync_runs_result["sync_runs_processed"],
                "total_index_attempts_created": sync_runs_result["index_attempts_created"],
                "total_errors": len(profiles_result["errors"]) + len(sync_runs_result["errors"])
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Full migration failed: {str(e)}"
        )


@router.get("/status")
async def get_migration_status(
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> Dict[str, Any]:
    """
    Get the current migration status and data counts
    """
    try:
        from sqlalchemy import select, func
        
        # Count existing data
        profiles_count = await db.scalar(
            select(func.count(m.ConnectorProfile.id)).where(
                m.ConnectorProfile.organization_id == uuid.UUID(current_org_id)
            )
        )
        
        sync_runs_count = await db.scalar(
            select(func.count(m.SyncRun.id)).join(m.ConnectorProfile).where(
                m.ConnectorProfile.organization_id == uuid.UUID(current_org_id)
            )
        )
        
        connectors_count = await db.scalar(select(func.count(m.Connector.id)))
        
        cc_pairs_count = await db.scalar(
            select(func.count(m.ConnectorCredentialPair.id)).where(
                m.ConnectorCredentialPair.organization_id == uuid.UUID(current_org_id)
            )
        )
        
        index_attempts_count = await db.scalar(
            select(func.count(m.IndexAttempt.id)).join(m.ConnectorCredentialPair).where(
                m.ConnectorCredentialPair.organization_id == uuid.UUID(current_org_id)
            )
        )
        
        return {
            "legacy_data": {
                "connector_profiles": profiles_count or 0,
                "sync_runs": sync_runs_count or 0
            },
            "new_data": {
                "connectors": connectors_count or 0,
                "cc_pairs": cc_pairs_count or 0,
                "index_attempts": index_attempts_count or 0
            },
            "migration_needed": (profiles_count or 0) > 0 and (cc_pairs_count or 0) == 0,
            "organization_id": current_org_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get migration status: {str(e)}"
        )
