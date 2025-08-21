from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.destinations import registry, get_destination
from backend.db.session import get_db
from backend.db import models as m
from backend.deps import get_current_org_id

router = APIRouter(prefix="/destinations", tags=["Destinations"])

@router.get(
    "/definitions",
    summary="List available destination definitions",
    description="Returns destination names and their configuration schemas for building UI forms.",
)
async def list_destination_definitions() -> list[dict]:
    defs = []
    for name, cls in registry.items():
        inst = cls()
        schema = inst.config_schema()
        defs.append({"name": name, "schema": schema})
    return defs

@router.get(
    "/{destination_name}/health",
    summary="Check destination health",
    description="Check the health status of a specific destination using organization's configuration.",
)
async def check_destination_health(
    destination_name: str,
    db: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
) -> dict:
    """Check health of a destination using the organization's target configuration"""
    
    # Get the destination target for this organization
    result = await db.execute(
        select(m.DestinationTarget).where(
            m.DestinationTarget.name == destination_name,
            m.DestinationTarget.organization_id == org_id
        )
    )
    target = result.scalar_one_or_none()
    
    if not target:
        raise HTTPException(
            status_code=404, 
            detail=f"Destination target '{destination_name}' not configured for organization"
        )
    
    try:
        destination_class = get_destination(destination_name)
        destination = destination_class()
        
        # Perform health check
        is_healthy = await destination.health_check(target.config)
        health_status = destination.get_health_status()
        
        return {
            "destination_name": destination_name,
            "target_id": str(target.id),
            "healthy": is_healthy,
            "status": health_status,
        }
        
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Destination '{destination_name}' not found in registry"
        )
    except Exception as e:
        return {
            "destination_name": destination_name,
            "target_id": str(target.id) if target else None,
            "healthy": False,
            "error": str(e),
        }

@router.post(
    "/{destination_name}/test",
    summary="Test destination configuration",
    description="Test a destination configuration without saving it.",
)
async def test_destination_config(
    destination_name: str,
    config: dict,
) -> dict:
    """Test a destination configuration"""
    
    try:
        destination_class = get_destination(destination_name)
        destination = destination_class()
        
        # Test the configuration
        is_healthy = await destination.health_check(config)
        health_status = destination.get_health_status()
        
        return {
            "destination_name": destination_name,
            "config_valid": is_healthy,
            "status": health_status,
        }
        
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Destination '{destination_name}' not found in registry"
        )
    except Exception as e:
        return {
            "destination_name": destination_name,
            "config_valid": False,
            "error": str(e),
        } 