"""
Intelligent alerting system for destination and CC-Pair health monitoring
Extends Onyx's monitoring patterns with proactive alerting capabilities
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

from backend.monitoring.destination_metrics import DestinationStatus, CCPairStatus

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning" 
    INFO = "info"


class AlertType(str, Enum):
    """Types of alerts"""
    DESTINATION_DOWN = "destination_down"
    DESTINATION_DEGRADED = "destination_degraded"
    CC_PAIR_SYNC_FAILED = "cc_pair_sync_failed"
    CC_PAIR_SYNC_SLOW = "cc_pair_sync_slow"
    HIGH_ERROR_RATE = "high_error_rate"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    HEALTH_CHECK_FAILED = "health_check_failed"


@dataclass
class Alert:
    """Alert data structure"""
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    organization_id: str
    destination_name: Optional[str] = None
    cc_pair_id: Optional[str] = None
    target_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class AlertRule:
    """Alert rule configuration"""
    alert_type: AlertType
    severity: AlertSeverity
    condition: Callable[[Dict[str, Any]], bool]
    title_template: str
    message_template: str
    cooldown_minutes: int = 30  # Prevent alert spam
    enabled: bool = True


class AlertManager:
    """
    Intelligent alert manager that monitors metrics and triggers alerts
    Follows Onyx's monitoring patterns with enhanced alerting logic
    """
    
    def __init__(self):
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._alert_rules: List[AlertRule] = []
        self._alert_handlers: List[Callable[[Alert], None]] = []
        self._last_alert_times: Dict[str, datetime] = {}
        
        # Initialize default alert rules
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """Setup default alerting rules based on Onyx patterns"""
        
        # Destination health alerts
        self.add_rule(AlertRule(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            condition=lambda metrics: metrics.get('destination_health_status', 1.0) == 0.0,
            title_template="Destination {destination_name} is DOWN",
            message_template="Destination {destination_name} for organization {organization_id} is not responding to health checks. Last error: {last_error}",
            cooldown_minutes=15
        ))
        
        self.add_rule(AlertRule(
            alert_type=AlertType.DESTINATION_DEGRADED,
            severity=AlertSeverity.WARNING,
            condition=lambda metrics: metrics.get('destination_health_status', 1.0) == 0.5,
            title_template="Destination {destination_name} is DEGRADED",
            message_template="Destination {destination_name} for organization {organization_id} is experiencing performance issues. Response time: {avg_response_time}s",
            cooldown_minutes=30
        ))
        
        # CC-Pair sync alerts
        self.add_rule(AlertRule(
            alert_type=AlertType.CC_PAIR_SYNC_FAILED,
            severity=AlertSeverity.CRITICAL,
            condition=lambda metrics: (
                metrics.get('sync_failure_count', 0) >= 3 and
                metrics.get('last_successful_sync_hours', 0) > 24
            ),
            title_template="CC-Pair {cc_pair_id} sync repeatedly failing",
            message_template="CC-Pair {cc_pair_id} ({connector_source} -> {destination_name}) has failed {failure_count} times. Last successful sync: {last_success_time}",
            cooldown_minutes=60
        ))
        
        self.add_rule(AlertRule(
            alert_type=AlertType.CC_PAIR_SYNC_SLOW,
            severity=AlertSeverity.WARNING,
            condition=lambda metrics: metrics.get('avg_sync_duration_minutes', 0) > 60,
            title_template="CC-Pair {cc_pair_id} sync is slow",
            message_template="CC-Pair {cc_pair_id} sync duration is {avg_sync_duration_minutes} minutes, which exceeds the 60-minute threshold",
            cooldown_minutes=120
        ))
        
        # Error rate alerts
        self.add_rule(AlertRule(
            alert_type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.WARNING,
            condition=lambda metrics: (
                metrics.get('error_rate_percent', 0) > 10 and
                metrics.get('total_requests', 0) > 10
            ),
            title_template="High error rate for {destination_name}",
            message_template="Destination {destination_name} has {error_rate_percent}% error rate over the last hour ({error_count}/{total_requests} requests)",
            cooldown_minutes=45
        ))
        
        # Rate limiting alerts
        self.add_rule(AlertRule(
            alert_type=AlertType.RATE_LIMIT_EXCEEDED,
            severity=AlertSeverity.WARNING,
            condition=lambda metrics: metrics.get('rate_limit_remaining', 100) < 10,
            title_template="Rate limit approaching for {destination_name}",
            message_template="Destination {destination_name} has only {rate_limit_remaining} requests remaining in the current window",
            cooldown_minutes=30
        ))
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule"""
        self._alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.alert_type.value}")
    
    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler (e.g., email, Slack, webhook)"""
        self._alert_handlers.append(handler)
        logger.info("Added alert handler")
    
    def evaluate_metrics(
        self,
        organization_id: str,
        destination_name: Optional[str] = None,
        cc_pair_id: Optional[str] = None,
        target_id: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> List[Alert]:
        """
        Evaluate metrics against alert rules and trigger alerts if needed
        """
        if not metrics:
            return []
        
        triggered_alerts = []
        
        for rule in self._alert_rules:
            if not rule.enabled:
                continue
            
            try:
                # Check if condition is met
                if rule.condition(metrics):
                    alert_key = self._get_alert_key(
                        rule.alert_type, organization_id, destination_name, cc_pair_id, target_id
                    )
                    
                    # Check cooldown period
                    if self._is_in_cooldown(alert_key, rule.cooldown_minutes):
                        continue
                    
                    # Create alert
                    alert = Alert(
                        alert_type=rule.alert_type,
                        severity=rule.severity,
                        title=rule.title_template.format(
                            destination_name=destination_name or "unknown",
                            cc_pair_id=cc_pair_id or "unknown",
                            organization_id=organization_id,
                            **metrics
                        ),
                        message=rule.message_template.format(
                            destination_name=destination_name or "unknown",
                            cc_pair_id=cc_pair_id or "unknown",
                            organization_id=organization_id,
                            target_id=target_id or "unknown",
                            **metrics
                        ),
                        organization_id=organization_id,
                        destination_name=destination_name,
                        cc_pair_id=cc_pair_id,
                        target_id=target_id,
                        metadata=metrics.copy()
                    )
                    
                    # Store and trigger alert
                    self._active_alerts[alert_key] = alert
                    self._alert_history.append(alert)
                    self._last_alert_times[alert_key] = datetime.utcnow()
                    
                    triggered_alerts.append(alert)
                    
                    # Send to handlers
                    self._send_alert(alert)
                    
                    logger.warning(f"Alert triggered: {alert.title}")
                
                else:
                    # Check if we should resolve an existing alert
                    alert_key = self._get_alert_key(
                        rule.alert_type, organization_id, destination_name, cc_pair_id, target_id
                    )
                    
                    if alert_key in self._active_alerts:
                        alert = self._active_alerts[alert_key]
                        if not alert.resolved:
                            alert.resolved = True
                            alert.resolved_at = datetime.utcnow()
                            logger.info(f"Alert resolved: {alert.title}")
                            
                            # Optionally send resolution notification
                            self._send_alert_resolution(alert)
            
            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule.alert_type}: {e}")
        
        return triggered_alerts
    
    def _get_alert_key(
        self,
        alert_type: AlertType,
        organization_id: str,
        destination_name: Optional[str] = None,
        cc_pair_id: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> str:
        """Generate unique key for alert deduplication"""
        parts = [alert_type.value, organization_id]
        if destination_name:
            parts.append(f"dest:{destination_name}")
        if cc_pair_id:
            parts.append(f"cc:{cc_pair_id}")
        if target_id:
            parts.append(f"target:{target_id}")
        return "|".join(parts)
    
    def _is_in_cooldown(self, alert_key: str, cooldown_minutes: int) -> bool:
        """Check if alert is in cooldown period"""
        if alert_key not in self._last_alert_times:
            return False
        
        last_alert = self._last_alert_times[alert_key]
        cooldown_period = timedelta(minutes=cooldown_minutes)
        return datetime.utcnow() - last_alert < cooldown_period
    
    def _send_alert(self, alert: Alert) -> None:
        """Send alert to all registered handlers"""
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error sending alert to handler: {e}")
    
    def _send_alert_resolution(self, alert: Alert) -> None:
        """Send alert resolution notification"""
        # Create a copy of the alert marked as resolved for handlers
        resolution_alert = Alert(
            alert_type=alert.alert_type,
            severity=AlertSeverity.INFO,
            title=f"RESOLVED: {alert.title}",
            message=f"Alert has been resolved: {alert.message}",
            organization_id=alert.organization_id,
            destination_name=alert.destination_name,
            cc_pair_id=alert.cc_pair_id,
            target_id=alert.target_id,
            metadata=alert.metadata,
            resolved=True,
            resolved_at=alert.resolved_at
        )
        
        self._send_alert(resolution_alert)
    
    def get_active_alerts(
        self,
        organization_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get active alerts, optionally filtered"""
        alerts = [alert for alert in self._active_alerts.values() if not alert.resolved]
        
        if organization_id:
            alerts = [alert for alert in alerts if alert.organization_id == organization_id]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def get_alert_history(
        self,
        organization_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Alert]:
        """Get alert history for the specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        alerts = [
            alert for alert in self._alert_history
            if alert.timestamp >= cutoff_time
        ]
        
        if organization_id:
            alerts = [alert for alert in alerts if alert.organization_id == organization_id]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_key: str) -> bool:
        """Acknowledge an active alert"""
        if alert_key in self._active_alerts:
            alert = self._active_alerts[alert_key]
            alert.metadata['acknowledged'] = True
            alert.metadata['acknowledged_at'] = datetime.utcnow().isoformat()
            logger.info(f"Alert acknowledged: {alert.title}")
            return True
        return False


# =============================================================================
# Default Alert Handlers
# =============================================================================

def log_alert_handler(alert: Alert) -> None:
    """Simple log-based alert handler"""
    level = logging.ERROR if alert.severity == AlertSeverity.CRITICAL else logging.WARNING
    logger.log(level, f"ALERT [{alert.severity.upper()}]: {alert.title} - {alert.message}")


def console_alert_handler(alert: Alert) -> None:
    """Console-based alert handler for development"""
    severity_emoji = {
        AlertSeverity.CRITICAL: "🚨",
        AlertSeverity.WARNING: "⚠️",
        AlertSeverity.INFO: "ℹ️"
    }
    
    emoji = severity_emoji.get(alert.severity, "📢")
    print(f"\n{emoji} ALERT [{alert.severity.upper()}] {emoji}")
    print(f"Title: {alert.title}")
    print(f"Message: {alert.message}")
    print(f"Organization: {alert.organization_id}")
    print(f"Time: {alert.timestamp.isoformat()}")
    if alert.resolved:
        print(f"✅ RESOLVED at {alert.resolved_at}")
    print("-" * 50)


# Global alert manager instance (singleton pattern like Onyx)
alert_manager = AlertManager()

# Add default handlers
alert_manager.add_handler(log_alert_handler)
alert_manager.add_handler(console_alert_handler)
