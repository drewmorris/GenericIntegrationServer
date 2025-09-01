"""
Alert management API endpoints
Provides REST API for viewing and managing alerts
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.deps import get_current_org_id
from backend.monitoring.alerting import alert_manager, Alert, AlertSeverity, AlertType

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# =============================================================================
# Pydantic Models
# =============================================================================

class AlertResponse(BaseModel):
    """Alert response model"""
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    organization_id: str
    destination_name: Optional[str] = None
    cc_pair_id: Optional[str] = None
    target_id: Optional[str] = None
    timestamp: str
    resolved: bool
    resolved_at: Optional[str] = None
    acknowledged: bool = False
    
    @classmethod
    def from_alert(cls, alert: Alert) -> "AlertResponse":
        """Convert Alert to AlertResponse"""
        return cls(
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            message=alert.message,
            organization_id=alert.organization_id,
            destination_name=alert.destination_name,
            cc_pair_id=alert.cc_pair_id,
            target_id=alert.target_id,
            timestamp=alert.timestamp.isoformat(),
            resolved=alert.resolved,
            resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
            acknowledged=alert.metadata.get('acknowledged', False)
        )


class AlertSummary(BaseModel):
    """Alert summary statistics"""
    total_active: int
    critical_count: int
    warning_count: int
    info_count: int
    resolved_last_24h: int


class AcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert"""
    alert_key: str


# =============================================================================
# API Endpoints
# =============================================================================

@router.get(
    "/active",
    response_model=List[AlertResponse],
    summary="Get active alerts",
    description="Retrieve all active (unresolved) alerts for the current organization"
)
async def get_active_alerts(
    org_id: str = Depends(get_current_org_id),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity level")
) -> List[AlertResponse]:
    """Get active alerts for the organization"""
    
    active_alerts = alert_manager.get_active_alerts(
        organization_id=org_id,
        severity=severity
    )
    
    return [AlertResponse.from_alert(alert) for alert in active_alerts]


@router.get(
    "/history",
    response_model=List[AlertResponse],
    summary="Get alert history",
    description="Retrieve alert history for the specified time period"
)
async def get_alert_history(
    org_id: str = Depends(get_current_org_id),
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve (1-168)")
) -> List[AlertResponse]:
    """Get alert history for the organization"""
    
    alert_history = alert_manager.get_alert_history(
        organization_id=org_id,
        hours=hours
    )
    
    return [AlertResponse.from_alert(alert) for alert in alert_history]


@router.get(
    "/summary",
    response_model=AlertSummary,
    summary="Get alert summary",
    description="Get summary statistics of alerts for the organization"
)
async def get_alert_summary(
    org_id: str = Depends(get_current_org_id)
) -> AlertSummary:
    """Get alert summary statistics"""
    
    active_alerts = alert_manager.get_active_alerts(organization_id=org_id)
    history_24h = alert_manager.get_alert_history(organization_id=org_id, hours=24)
    
    # Count by severity
    critical_count = len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL])
    warning_count = len([a for a in active_alerts if a.severity == AlertSeverity.WARNING])
    info_count = len([a for a in active_alerts if a.severity == AlertSeverity.INFO])
    
    # Count resolved in last 24h
    resolved_24h = len([a for a in history_24h if a.resolved])
    
    return AlertSummary(
        total_active=len(active_alerts),
        critical_count=critical_count,
        warning_count=warning_count,
        info_count=info_count,
        resolved_last_24h=resolved_24h
    )


@router.post(
    "/acknowledge",
    summary="Acknowledge alert",
    description="Acknowledge an active alert to prevent further notifications"
)
async def acknowledge_alert(
    request: AcknowledgeRequest,
    org_id: str = Depends(get_current_org_id)
) -> dict:
    """Acknowledge an alert"""
    
    # Verify the alert belongs to the organization
    active_alerts = alert_manager.get_active_alerts(organization_id=org_id)
    alert_keys = [
        alert_manager._get_alert_key(
            alert.alert_type,
            alert.organization_id,
            alert.destination_name,
            alert.cc_pair_id,
            alert.target_id
        )
        for alert in active_alerts
    ]
    
    if request.alert_key not in alert_keys:
        raise HTTPException(
            status_code=404,
            detail="Alert not found or does not belong to your organization"
        )
    
    success = alert_manager.acknowledge_alert(request.alert_key)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )
    
    return {"message": "Alert acknowledged successfully"}


@router.get(
    "/types",
    response_model=List[str],
    summary="Get alert types",
    description="Get list of available alert types"
)
async def get_alert_types() -> List[str]:
    """Get available alert types"""
    return [alert_type.value for alert_type in AlertType]


@router.get(
    "/severities",
    response_model=List[str],
    summary="Get alert severities",
    description="Get list of available alert severity levels"
)
async def get_alert_severities() -> List[str]:
    """Get available alert severities"""
    return [severity.value for severity in AlertSeverity]


@router.get(
    "/health",
    summary="Alert system health",
    description="Check the health of the alerting system"
)
async def get_alert_system_health() -> dict:
    """Get alerting system health status"""
    
    active_count = len(alert_manager.get_active_alerts())
    total_rules = len(alert_manager._alert_rules)
    enabled_rules = len([r for r in alert_manager._alert_rules if r.enabled])
    handler_count = len(alert_manager._alert_handlers)
    
    return {
        "status": "healthy",
        "active_alerts": active_count,
        "total_rules": total_rules,
        "enabled_rules": enabled_rules,
        "alert_handlers": handler_count,
        "last_evaluation": "continuous"  # Since we run continuous monitoring
    }


