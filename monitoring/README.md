# Integration Server Monitoring Stack

This directory contains a complete monitoring solution for the Integration Server, built on industry-standard tools and following Onyx's monitoring patterns.

## 🏗️ Architecture Overview

The monitoring stack consists of:

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards  
- **Alertmanager**: Alert routing and notification
- **Node Exporter**: System metrics collection

## 📊 Available Dashboards

### 1. Destination Overview (`destination-overview.json`)
- Document delivery rates (success/error)
- Destination health status
- Response time percentiles
- Error rates by type
- Active CC-Pair syncs

### 2. CC-Pair Sync Monitoring (`cc-pair-sync-monitoring.json`)
- Sync success/error rates
- Sync duration percentiles
- Documents processed rates
- Active sync counts
- Sync attempts by source/destination
- Last sync times table

## 🚨 Alert Rules

### Destination Alerts
- **DestinationDown**: Destination health status = 0 for 5+ minutes
- **DestinationDegraded**: Destination health status = 0.5 for 10+ minutes
- **HighDestinationErrorRate**: Error rate > 0.1/second for 5+ minutes
- **SlowDestinationResponse**: 95th percentile > 30s for 10+ minutes

### CC-Pair Alerts
- **CCPairSyncFailed**: 3+ failures in 1 hour
- **CCPairSyncSlow**: 95th percentile sync time > 1 hour for 15+ minutes
- **CCPairNoRecentSync**: No successful sync in 24+ hours
- **TooManyActiveSyncs**: More than 10 active syncs for 5+ minutes

### System Alerts
- **IntegrationServerDown**: API not responding for 1+ minute
- **HighMemoryUsage**: Memory usage > 90% for 5+ minutes
- **HighCPUUsage**: CPU usage > 80% for 10+ minutes
- **DiskSpaceLow**: Disk space < 10% for 5+ minutes

## 🚀 Quick Start

### 1. Start the Monitoring Stack

```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Access the Services

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

### 3. Configure Integration Server

Ensure your Integration Server is exposing metrics at `/metrics/prometheus`:

```python
# This is already configured in backend/routes/metrics.py
app.include_router(metrics_router.router)
```

### 4. Import Dashboards

Dashboards are automatically provisioned from the `grafana/dashboards/` directory.

## 📈 Key Metrics

### Destination Metrics
```promql
# Document delivery rate
rate(destination_documents_sent_total[5m])

# Health status (1=healthy, 0.5=degraded, 0=down)
destination_health_status

# Response time percentiles
histogram_quantile(0.95, rate(destination_request_duration_seconds_bucket[5m]))

# Error rate
rate(destination_errors_total[5m])
```

### CC-Pair Metrics
```promql
# Sync success rate
rate(cc_pair_sync_attempts_total{status="success"}[5m])

# Sync duration percentiles
histogram_quantile(0.95, rate(cc_pair_sync_duration_seconds_bucket[5m]))

# Documents processed rate
rate(cc_pair_documents_processed_total[5m])

# Active syncs
cc_pair_active_syncs
```

## 🔧 Configuration

### Prometheus Configuration
- **Scrape Interval**: 15s (configurable in `prometheus/prometheus.yml`)
- **Retention**: 200h (configurable via command line)
- **Targets**: Integration Server API, Node Exporter, PostgreSQL, Redis

### Grafana Configuration
- **Admin Credentials**: admin/admin (change in production)
- **Data Source**: Prometheus (auto-provisioned)
- **Dashboards**: Auto-imported from `grafana/dashboards/`

### Alertmanager Configuration
- **Email Notifications**: Configure SMTP settings in `alertmanager/alertmanager.yml`
- **Webhook Integration**: Sends alerts to Integration Server webhook endpoint
- **Routing**: Critical alerts have shorter repeat intervals

## 🔍 Troubleshooting

### Common Issues

1. **Metrics not appearing**
   - Check Integration Server is running and accessible
   - Verify `/metrics/prometheus` endpoint returns data
   - Check Prometheus targets status at http://localhost:9090/targets

2. **Dashboards not loading**
   - Verify Grafana can connect to Prometheus
   - Check dashboard JSON syntax
   - Ensure proper data source configuration

3. **Alerts not firing**
   - Check Prometheus rules syntax: `promtool check rules prometheus/rules/*.yml`
   - Verify Alertmanager configuration
   - Check alert evaluation in Prometheus UI

### Logs
```bash
# View service logs
docker-compose -f docker-compose.monitoring.yml logs prometheus
docker-compose -f docker-compose.monitoring.yml logs grafana
docker-compose -f docker-compose.monitoring.yml logs alertmanager
```

## 🔒 Security Considerations

### Production Deployment
1. **Change default passwords**
2. **Enable HTTPS/TLS**
3. **Configure proper authentication**
4. **Restrict network access**
5. **Use secrets management**

### Example Production Changes
```yaml
# In docker-compose.monitoring.yml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
  - GF_SERVER_PROTOCOL=https
  - GF_SERVER_CERT_FILE=/etc/ssl/certs/grafana.crt
  - GF_SERVER_CERT_KEY=/etc/ssl/private/grafana.key
```

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Integration Server API Documentation](../docs/api.md)

## 🤝 Contributing

When adding new metrics:

1. **Define the metric** in `backend/monitoring/destination_metrics.py`
2. **Instrument the code** to record the metric
3. **Add dashboard panels** in Grafana
4. **Create alert rules** if needed
5. **Update documentation**

### Example: Adding a New Metric
```python
# In destination_metrics.py
new_metric_counter = Counter(
    'new_metric_total',
    'Description of new metric',
    ['label1', 'label2']
)

# In your code
new_metric_counter.labels(label1="value1", label2="value2").inc()
```
