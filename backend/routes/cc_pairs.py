"""
API routes for Connector-Credential Pair management
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.db import cc_pairs as cc_pair_ops
from backend.db import models as m
from backend.deps import get_current_user, get_current_org_id
from backend.schemas.cc_pairs import (
    ConnectorCreate, ConnectorUpdate, ConnectorOut, ConnectorWithCCPairs,
    ConnectorCredentialPairCreate, ConnectorCredentialPairUpdate, 
    ConnectorCredentialPairOut, ConnectorCredentialPairWithDetails,
    IndexAttemptCreate, IndexAttemptUpdate, IndexAttemptOut
)

router = APIRouter(prefix="/cc-pairs", tags=["CC-Pairs"])


# ===== CONNECTOR ENDPOINTS =====

@router.post("/connectors", response_model=ConnectorOut, status_code=status.HTTP_201_CREATED)
async def create_connector(
    connector_data: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user)
) -> m.Connector:
    """Create a new reusable connector configuration"""
    try:
        connector = await cc_pair_ops.create_connector(db, connector_data)
        await db.commit()
        return connector
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create connector: {str(e)}"
        )


@router.get("/connectors", response_model=List[ConnectorOut])
async def list_connectors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    source: Optional[str] = Query(None, description="Filter by connector source"),
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user)
) -> List[m.Connector]:
    """List all connector configurations"""
    connectors = await cc_pair_ops.get_connectors(db, skip=skip, limit=limit, source=source)
    return list(connectors)


@router.get("/connectors/{connector_id}", response_model=ConnectorWithCCPairs)
async def get_connector(
    connector_id: int,
    include_cc_pairs: bool = Query(False, description="Include associated CC-Pairs"),
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user)
) -> m.Connector:
    """Get a specific connector configuration"""
    connector = await cc_pair_ops.get_connector(db, connector_id)
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found"
        )
    
    if include_cc_pairs:
        # Load CC-Pairs for this connector
        cc_pairs = await cc_pair_ops.get_cc_pairs(db, connector_id=connector_id)
        connector.connector_credential_pairs = list(cc_pairs)
    
    return connector


@router.put("/connectors/{connector_id}", response_model=ConnectorOut)
async def update_connector(
    connector_id: int,
    connector_data: ConnectorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user)
) -> m.Connector:
    """Update a connector configuration"""
    try:
        connector = await cc_pair_ops.update_connector(db, connector_id, connector_data)
        if not connector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connector not found"
            )
        await db.commit()
        return connector
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update connector: {str(e)}"
        )


@router.delete("/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connector(
    connector_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user)
):
    """Delete a connector configuration (only if no CC-Pairs exist)"""
    try:
        success = await cc_pair_ops.delete_connector(db, connector_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connector not found"
            )
        await db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete connector: {str(e)}"
        )


# ===== CC-PAIR ENDPOINTS =====

@router.post("/", response_model=ConnectorCredentialPairOut, status_code=status.HTTP_201_CREATED)
async def create_cc_pair(
    cc_pair_data: ConnectorCredentialPairCreate,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> m.ConnectorCredentialPair:
    """Create a new Connector-Credential Pair"""
    # Ensure organization_id matches current user's org
    cc_pair_data.organization_id = uuid.UUID(current_org_id)
    cc_pair_data.creator_id = current_user.id
    
    try:
        # Verify connector exists
        connector = await cc_pair_ops.get_connector(db, cc_pair_data.connector_id)
        if not connector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connector not found"
            )
        
        # Verify credential exists and belongs to user's org
        from backend.db.models import Credential
        from sqlalchemy import select
        result = await db.execute(
            select(Credential).where(
                Credential.id == cc_pair_data.credential_id,
                Credential.organization_id == uuid.UUID(current_org_id)
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found or not accessible"
            )
        
        cc_pair = await cc_pair_ops.create_cc_pair(db, cc_pair_data)
        await db.commit()
        return cc_pair
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create CC-Pair: {str(e)}"
        )


@router.get("/", response_model=List[ConnectorCredentialPairOut])
async def list_cc_pairs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    connector_id: Optional[int] = Query(None, description="Filter by connector ID"),
    credential_id: Optional[str] = Query(None, description="Filter by credential ID"),
    cc_pair_status: Optional[m.ConnectorCredentialPairStatus] = Query(None, description="Filter by status"),
    include_connector: bool = Query(True, description="Include connector details"),
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> List[m.ConnectorCredentialPair]:
    """List CC-Pairs for the current organization"""
    credential_uuid = None
    if credential_id:
        try:
            credential_uuid = uuid.UUID(credential_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid credential ID format"
            )
    
    cc_pairs = await cc_pair_ops.get_cc_pairs(
        db,
        organization_id=uuid.UUID(current_org_id),
        connector_id=connector_id,
        credential_id=credential_uuid,
        status=cc_pair_status,
        skip=skip,
        limit=limit,
        include_connector=include_connector
    )
    return list(cc_pairs)


@router.get("/{cc_pair_id}", response_model=ConnectorCredentialPairWithDetails)
async def get_cc_pair(
    cc_pair_id: int,
    include_latest_attempt: bool = Query(True, description="Include latest index attempt"),
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> ConnectorCredentialPairWithDetails:
    """Get a specific CC-Pair with details"""
    cc_pair = await cc_pair_ops.get_cc_pair_with_details(
        db, cc_pair_id, organization_id=uuid.UUID(current_org_id)
    )
    if not cc_pair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CC-Pair not found or not accessible"
        )
    
    # Create the response object with additional details
    response_data = ConnectorCredentialPairWithDetails.model_validate(cc_pair)
    
    if include_latest_attempt:
        latest_attempt = await cc_pair_ops.get_latest_index_attempt(db, cc_pair_id)
        response_data.latest_index_attempt = IndexAttemptOut.model_validate(latest_attempt) if latest_attempt else None
        
        active_attempts = await cc_pair_ops.get_active_index_attempts(db, cc_pair_id)
        response_data.active_index_attempts = [IndexAttemptOut.model_validate(attempt) for attempt in active_attempts]
    
    return response_data


@router.put("/{cc_pair_id}", response_model=ConnectorCredentialPairOut)
async def update_cc_pair(
    cc_pair_id: int,
    cc_pair_data: ConnectorCredentialPairUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> m.ConnectorCredentialPair:
    """Update a CC-Pair"""
    # Verify CC-Pair belongs to user's org
    cc_pair = await cc_pair_ops.get_cc_pair(db, cc_pair_id)
    if not cc_pair or str(cc_pair.organization_id) != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CC-Pair not found or not accessible"
        )
    
    try:
        updated_cc_pair = await cc_pair_ops.update_cc_pair(db, cc_pair_id, cc_pair_data)
        if not updated_cc_pair:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CC-Pair not found"
            )
        await db.commit()
        return updated_cc_pair
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update CC-Pair: {str(e)}"
        )


@router.delete("/{cc_pair_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cc_pair(
    cc_pair_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
):
    """Delete a CC-Pair"""
    # Verify CC-Pair belongs to user's org
    cc_pair = await cc_pair_ops.get_cc_pair(db, cc_pair_id)
    if not cc_pair or str(cc_pair.organization_id) != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CC-Pair not found or not accessible"
        )
    
    try:
        success = await cc_pair_ops.delete_cc_pair(db, cc_pair_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CC-Pair not found"
            )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete CC-Pair: {str(e)}"
        )


# ===== INDEX ATTEMPT ENDPOINTS =====

@router.post("/{cc_pair_id}/index-attempts", response_model=IndexAttemptOut, status_code=status.HTTP_201_CREATED)
async def create_index_attempt(
    cc_pair_id: int,
    attempt_data: IndexAttemptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> m.IndexAttempt:
    """Create a new index attempt for a CC-Pair"""
    # Verify CC-Pair belongs to user's org
    cc_pair = await cc_pair_ops.get_cc_pair(db, cc_pair_id)
    if not cc_pair or str(cc_pair.organization_id) != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CC-Pair not found or not accessible"
        )
    
    # Set the CC-Pair ID
    attempt_data.connector_credential_pair_id = cc_pair_id
    
    try:
        attempt = await cc_pair_ops.create_index_attempt(db, attempt_data)
        await db.commit()
        return attempt
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create index attempt: {str(e)}"
        )


@router.get(
    "/{cc_pair_id}/index-attempts", 
    response_model=List[IndexAttemptOut],
    summary="List index attempts",
    description="Retrieve index attempts (sync operations) for a CC-Pair with real-time progress data. "
                "Shows detailed sync status, progress, batch completion, and heartbeat information "
                "for monitoring active and historical sync operations."
)
async def list_index_attempts(
    cc_pair_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    index_status: Optional[m.IndexingStatus] = Query(None, description="Filter by status (IN_PROGRESS, SUCCESS, FAILED, etc.)"),
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> List[m.IndexAttempt]:
    """List index attempts for a CC-Pair"""
    # Verify CC-Pair belongs to user's org
    cc_pair = await cc_pair_ops.get_cc_pair(db, cc_pair_id)
    if not cc_pair or str(cc_pair.organization_id) != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CC-Pair not found or not accessible"
        )
    
    attempts = await cc_pair_ops.get_index_attempts(
        db, cc_pair_id=cc_pair_id, status=index_status, skip=skip, limit=limit
    )
    return list(attempts)


@router.get("/index-attempts/{attempt_id}", response_model=IndexAttemptOut)
async def get_index_attempt(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> m.IndexAttempt:
    """Get a specific index attempt"""
    attempt = await cc_pair_ops.get_index_attempt(db, attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index attempt not found"
        )
    
    # Verify the CC-Pair belongs to user's org
    cc_pair = await cc_pair_ops.get_cc_pair(db, attempt.connector_credential_pair_id)
    if not cc_pair or str(cc_pair.organization_id) != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index attempt not accessible"
        )
    
    return attempt


@router.put("/index-attempts/{attempt_id}", response_model=IndexAttemptOut)
async def update_index_attempt(
    attempt_id: int,
    attempt_data: IndexAttemptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> m.IndexAttempt:
    """Update an index attempt"""
    attempt = await cc_pair_ops.get_index_attempt(db, attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index attempt not found"
        )
    
    # Verify the CC-Pair belongs to user's org
    cc_pair = await cc_pair_ops.get_cc_pair(db, attempt.connector_credential_pair_id)
    if not cc_pair or str(cc_pair.organization_id) != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index attempt not accessible"
        )
    
    try:
        updated_attempt = await cc_pair_ops.update_index_attempt(db, attempt_id, attempt_data)
        if not updated_attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Index attempt not found"
            )
        await db.commit()
        return updated_attempt
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update index attempt: {str(e)}"
        )


@router.post(
    "/index-attempts/{attempt_id}/cancel", 
    response_model=IndexAttemptOut,
    summary="Cancel index attempt",
    description="Request cancellation of an active index attempt (sync operation). "
                "Sets the cancellation_requested flag which the worker will check periodically. "
                "The actual cancellation may take some time depending on the current batch processing."
)
async def cancel_index_attempt(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> m.IndexAttempt:
    """Cancel a running index attempt"""
    attempt = await cc_pair_ops.get_index_attempt(db, attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index attempt not found"
        )
    
    # Verify the CC-Pair belongs to user's org
    cc_pair = await cc_pair_ops.get_cc_pair(db, attempt.connector_credential_pair_id)
    if not cc_pair or str(cc_pair.organization_id) != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index attempt not accessible"
        )
    
    try:
        success = await cc_pair_ops.cancel_index_attempt(db, attempt_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel this index attempt (not running or already completed)"
            )
        
        await db.commit()
        # Return the updated attempt
        updated_attempt = await cc_pair_ops.get_index_attempt(db, attempt_id)
        if not updated_attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Index attempt not found after cancellation"
            )
        return updated_attempt
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel index attempt: {str(e)}"
        )


@router.get(
    "/active-syncs",
    response_model=List[IndexAttemptOut],
    summary="Get active syncs",
    description="Retrieve all currently active (in-progress) sync operations across the organization. "
                "Useful for monitoring dashboard to show real-time sync status, progress bars, "
                "and overall system activity. Includes heartbeat and progress information."
)
async def get_active_syncs(
    db: AsyncSession = Depends(get_db),
    current_user: m.User = Depends(get_current_user),
    current_org_id: str = Depends(get_current_org_id)
) -> List[m.IndexAttempt]:
    """Get all active index attempts for the organization"""
    try:
        active_attempts = await cc_pair_ops.get_active_index_attempts_for_org(db, current_org_id)
        return list(active_attempts)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active syncs: {str(e)}"
        )
