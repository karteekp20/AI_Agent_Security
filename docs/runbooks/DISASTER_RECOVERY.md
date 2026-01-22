# Disaster Recovery Runbook

**Version:** 1.0
**Last Updated:** 2026-01-17
**Owner:** Platform Engineering Team

---

## Table of Contents

1. [Overview](#overview)
2. [Recovery Objectives](#recovery-objectives)
3. [Contact Information](#contact-information)
4. [Scenario 1: Database Failure](#scenario-1-database-failure)
5. [Scenario 2: Redis Failure](#scenario-2-redis-failure)
6. [Scenario 3: ECS Service Failure](#scenario-3-ecs-service-failure)
7. [Scenario 4: Region Failure](#scenario-4-region-failure)
8. [Scenario 5: Data Corruption](#scenario-5-data-corruption)
9. [Scenario 6: Security Incident](#scenario-6-security-incident)
10. [Testing Schedule](#testing-schedule)
11. [Post-Incident Review](#post-incident-review)

---

## Overview

This runbook provides step-by-step procedures for recovering Sentinel AI Security Platform from various disaster scenarios. Follow these procedures in order of priority to minimize downtime and data loss.

### Architecture Summary

```
                    ┌─────────────────┐
                    │   CloudFront    │
                    │   (Frontend)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │       ALB       │
                    │ (Load Balancer) │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────────┐   ┌─▼──────────┐  ┌▼────────────┐
     │   ECS Fargate   │   │   Celery   │  │   Redis     │
     │   (API Server)  │   │  Workers   │  │   Cache     │
     └────────┬────────┘   └─────┬──────┘  └─────────────┘
              │                  │
              └──────────┬───────┘
                         │
                ┌────────▼────────┐
                │    RDS (Multi-  │
                │  AZ PostgreSQL) │
                └─────────────────┘
```

---

## Recovery Objectives

| Scenario | RTO (Recovery Time) | RPO (Recovery Point) |
|----------|---------------------|----------------------|
| Database Failure (Single AZ) | 5 minutes | 0 minutes |
| Database Failure (Complete) | 30 minutes | 1 hour |
| Redis Failure | 15 minutes | 5 minutes |
| ECS Service Failure | 10 minutes | 0 minutes |
| Region Failure | 2 hours | 1 hour |
| Data Corruption | 1 hour | Variable |
| Security Incident | 30 minutes | N/A |

---

## Contact Information

### On-Call Rotation

| Role | Contact | Escalation |
|------|---------|------------|
| Primary On-Call | PagerDuty Auto-Notify | Immediate |
| Secondary On-Call | PagerDuty Auto-Escalate | After 15 min |
| Engineering Lead | [Name] - [Phone] | After 30 min |
| CTO | [Name] - [Phone] | Critical only |

### External Contacts

| Service | Contact | Account ID |
|---------|---------|------------|
| AWS Support | Premium Support Console | [Account ID] |
| PagerDuty | support@pagerduty.com | [Service ID] |
| SendGrid | support@sendgrid.com | [Account ID] |

---

## Scenario 1: Database Failure

### Symptoms
- API returns 500 errors
- Database connection timeouts
- CloudWatch alarm: `sentinel-rds-connections`

### Diagnosis

```bash
# Check RDS status
aws rds describe-db-instances --db-instance-identifier sentinel-db --query 'DBInstances[0].DBInstanceStatus'

# Check recent events
aws rds describe-events --source-identifier sentinel-db --source-type db-instance --duration 60

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=sentinel-db \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average
```

### Recovery Steps

#### Option A: Multi-AZ Failover (Automatic)
If Multi-AZ is enabled, AWS automatically fails over to the standby. Wait 1-2 minutes for DNS propagation.

```bash
# Verify failover completed
aws rds describe-db-instances --db-instance-identifier sentinel-db \
  --query 'DBInstances[0].[DBInstanceStatus, AvailabilityZone]'
```

#### Option B: Restore from Snapshot

```bash
# 1. List available snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier sentinel-db \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime,Status]' \
  --output table

# 2. Restore from latest snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier sentinel-db-recovery \
  --db-snapshot-identifier <SNAPSHOT_ID> \
  --db-instance-class db.t3.medium \
  --vpc-security-group-ids <SECURITY_GROUP_ID> \
  --db-subnet-group-name sentinel-db-subnet \
  --multi-az \
  --no-publicly-accessible

# 3. Wait for instance to be available (10-15 minutes)
aws rds wait db-instance-available --db-instance-identifier sentinel-db-recovery

# 4. Get new endpoint
NEW_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier sentinel-db-recovery \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# 5. Update Secrets Manager
aws secretsmanager update-secret \
  --secret-id sentinel/database-url \
  --secret-string "postgresql://sentinel_admin:PASSWORD@${NEW_ENDPOINT}:5432/sentinel"

# 6. Restart ECS services
aws ecs update-service --cluster sentinel-production --service sentinel-api --force-new-deployment
aws ecs update-service --cluster sentinel-production --service sentinel-celery --force-new-deployment
```

#### Option C: Point-in-Time Recovery

```bash
# Restore to specific point in time
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier sentinel-db \
  --target-db-instance-identifier sentinel-db-pitr \
  --restore-time "2026-01-17T10:00:00Z" \
  --db-instance-class db.t3.medium \
  --vpc-security-group-ids <SECURITY_GROUP_ID>
```

### Verification

```bash
# Test database connectivity
psql $DATABASE_URL -c "SELECT 1"

# Verify API health
curl -f https://api.sentinel.ai/health

# Check recent audit logs
curl -H "Authorization: Bearer $TOKEN" https://api.sentinel.ai/audit-logs?limit=10
```

---

## Scenario 2: Redis Failure

### Symptoms
- Slow API responses
- Session errors
- Celery tasks not processing

### Diagnosis

```bash
# Check ElastiCache status
aws elasticache describe-cache-clusters --cache-cluster-id sentinel-redis

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name CurrConnections \
  --dimensions Name=CacheClusterId,Value=sentinel-redis \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average
```

### Recovery Steps

```bash
# 1. If Redis is down, create new cluster from snapshot
aws elasticache describe-snapshots --cache-cluster-id sentinel-redis

# 2. Create new cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id sentinel-redis-recovery \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --cache-subnet-group-name sentinel-redis-subnet \
  --security-group-ids <SECURITY_GROUP_ID> \
  --snapshot-name <SNAPSHOT_NAME>

# 3. Wait for cluster to be available
aws elasticache wait cache-cluster-available --cache-cluster-id sentinel-redis-recovery

# 4. Get new endpoint
NEW_REDIS=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id sentinel-redis-recovery \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text)

# 5. Update Secrets Manager
aws secretsmanager update-secret \
  --secret-id sentinel/redis-url \
  --secret-string "redis://${NEW_REDIS}:6379/0"

# 6. Restart services
aws ecs update-service --cluster sentinel-production --service sentinel-api --force-new-deployment
aws ecs update-service --cluster sentinel-production --service sentinel-celery --force-new-deployment
```

### Notes
- Redis data loss is acceptable (cache only, sessions will require re-login)
- Rate limiting counters will reset

---

## Scenario 3: ECS Service Failure

### Symptoms
- API returning 503
- No healthy targets in ALB
- ECS tasks in STOPPED state

### Diagnosis

```bash
# Check ECS service status
aws ecs describe-services --cluster sentinel-production --services sentinel-api sentinel-celery

# Check stopped tasks
aws ecs list-tasks --cluster sentinel-production --desired-status STOPPED

# Get task details and stop reason
TASK_ARN=$(aws ecs list-tasks --cluster sentinel-production --desired-status STOPPED --query 'taskArns[0]' --output text)
aws ecs describe-tasks --cluster sentinel-production --tasks $TASK_ARN --query 'tasks[0].stoppedReason'

# Check CloudWatch logs
aws logs tail /ecs/sentinel-api --since 30m
```

### Recovery Steps

```bash
# 1. Force new deployment
aws ecs update-service \
  --cluster sentinel-production \
  --service sentinel-api \
  --force-new-deployment

# 2. If deployment fails, check task definition
aws ecs describe-task-definition --task-definition sentinel-api

# 3. If image issue, deploy previous version
aws ecs update-service \
  --cluster sentinel-production \
  --service sentinel-api \
  --task-definition sentinel-api:PREVIOUS_VERSION

# 4. Scale up if needed
aws ecs update-service \
  --cluster sentinel-production \
  --service sentinel-api \
  --desired-count 3

# 5. Wait for stability
aws ecs wait services-stable --cluster sentinel-production --services sentinel-api
```

---

## Scenario 4: Region Failure

### Prerequisites
- Cross-region RDS snapshot replication enabled
- DR region infrastructure pre-provisioned (eu-west-1)

### Recovery Steps

```bash
# 1. Confirm primary region is down
aws ec2 describe-availability-zones --region us-east-1

# 2. Switch to DR region
export AWS_DEFAULT_REGION=eu-west-1

# 3. Restore database from cross-region snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier sentinel-db-dr \
  --db-snapshot-identifier sentinel-db-cross-region-latest \
  --db-instance-class db.t3.medium \
  --vpc-security-group-ids <DR_SECURITY_GROUP_ID> \
  --db-subnet-group-name sentinel-db-subnet-dr

# 4. Wait for database
aws rds wait db-instance-available --db-instance-identifier sentinel-db-dr

# 5. Deploy ECS services in DR region
aws ecs create-service \
  --cluster sentinel-dr \
  --service-name sentinel-api \
  --task-definition sentinel-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-dr-1,subnet-dr-2],securityGroups=[sg-dr],assignPublicIp=DISABLED}"

# 6. Update Route 53 to point to DR
aws route53 change-resource-record-sets \
  --hosted-zone-id <HOSTED_ZONE_ID> \
  --change-batch file://dr-dns-update.json

# 7. Update CloudFront origin
aws cloudfront update-distribution \
  --id <DISTRIBUTION_ID> \
  --distribution-config file://dr-cloudfront-config.json

# 8. Notify customers
# Send notification via backup email system
```

### Failback Procedure

After primary region is restored:

1. Verify primary region health
2. Replicate DR database changes back to primary
3. Update DNS with low TTL
4. Switch traffic gradually (10% → 50% → 100%)
5. Monitor for issues
6. Decommission DR resources

---

## Scenario 5: Data Corruption

### Symptoms
- Invalid data in API responses
- Audit logs showing incorrect information
- User reports of incorrect data

### Diagnosis

```bash
# Identify corruption timeline
psql $DATABASE_URL -c "
  SELECT MIN(created_at), MAX(created_at)
  FROM audit_logs
  WHERE <corruption_condition>
"

# Check for recent deployments or changes
aws ecs describe-services --cluster sentinel-production --services sentinel-api \
  --query 'services[0].deployments[*].[createdAt,status]'
```

### Recovery Steps

```bash
# 1. Stop writes to affected tables
# Option: Put API in read-only mode or maintenance mode

# 2. Identify clean point in time
# Review audit logs and backups

# 3. Create PITR restore
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier sentinel-db \
  --target-db-instance-identifier sentinel-db-clean \
  --restore-time "2026-01-17T09:00:00Z"

# 4. Compare data between instances
pg_dump -t affected_table $CLEAN_DB_URL > clean_data.sql
pg_dump -t affected_table $CORRUPT_DB_URL > corrupt_data.sql
diff clean_data.sql corrupt_data.sql

# 5. Restore clean data
# Option A: Full table restore
pg_dump -t affected_table $CLEAN_DB_URL | psql $DATABASE_URL

# Option B: Selective restore
psql $DATABASE_URL -c "
  DELETE FROM affected_table WHERE <corruption_condition>;
  INSERT INTO affected_table SELECT * FROM dblink('$CLEAN_DB_URL', 'SELECT * FROM affected_table WHERE <condition>');
"

# 6. Verify data integrity
psql $DATABASE_URL -c "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM affected_table"

# 7. Resume normal operations
```

---

## Scenario 6: Security Incident

### Symptoms
- Unusual API access patterns
- PII data access alerts
- Injection attack alerts
- Unauthorized access attempts

### Immediate Response (First 15 minutes)

```bash
# 1. Assess severity
# Check security alerts in Grafana/CloudWatch

# 2. If active breach, isolate affected systems
# Revoke compromised API keys
aws ecs update-service --cluster sentinel-production --service sentinel-api --desired-count 0

# 3. Rotate secrets
aws secretsmanager rotate-secret --secret-id sentinel/jwt-secret
aws secretsmanager rotate-secret --secret-id sentinel/database-url

# 4. Block suspicious IPs at WAF
aws wafv2 update-ip-set \
  --name sentinel-blocklist \
  --scope REGIONAL \
  --id <IP_SET_ID> \
  --addresses <SUSPICIOUS_IP>/32 \
  --lock-token <LOCK_TOKEN>

# 5. Preserve evidence
aws logs create-export-task \
  --task-name incident-$(date +%Y%m%d%H%M%S) \
  --log-group-name /ecs/sentinel-api \
  --from $(date -u -d '24 hours ago' +%s000) \
  --to $(date -u +%s000) \
  --destination sentinel-incident-logs
```

### Investigation

```bash
# Export audit logs for analysis
aws logs filter-log-events \
  --log-group-name /ecs/sentinel-api \
  --start-time $(date -u -d '24 hours ago' +%s000) \
  --filter-pattern '{ $.status >= 400 }' \
  > suspicious_requests.json

# Check for unusual access patterns
psql $DATABASE_URL -c "
  SELECT api_key_id, COUNT(*), array_agg(DISTINCT threat_details->>'category')
  FROM audit_logs
  WHERE created_at > NOW() - INTERVAL '24 hours'
  AND is_threat = true
  GROUP BY api_key_id
  ORDER BY COUNT(*) DESC
  LIMIT 20
"
```

### Recovery

1. Revoke all potentially compromised credentials
2. Force password reset for affected users
3. Rotate all secrets and API keys
4. Deploy updated security rules
5. Restore services gradually
6. Monitor closely for 48 hours

---

## Testing Schedule

| Test Type | Frequency | Last Tested | Next Scheduled |
|-----------|-----------|-------------|----------------|
| Database snapshot restore | Monthly | 2026-01-01 | 2026-02-01 |
| Redis failover | Monthly | 2026-01-01 | 2026-02-01 |
| ECS service recovery | Weekly | 2026-01-15 | 2026-01-22 |
| Full DR simulation | Quarterly | 2025-12-15 | 2026-03-15 |
| Security incident drill | Quarterly | 2025-11-01 | 2026-02-01 |
| Region failover | Annually | 2025-06-01 | 2026-06-01 |

### Test Procedure

1. Announce test window to team
2. Document start time
3. Execute recovery steps
4. Measure RTO/RPO
5. Document issues encountered
6. Update runbook with improvements
7. Report results to leadership

---

## Post-Incident Review

After every incident, complete within 48 hours:

### Template

```markdown
## Incident Report: [TITLE]

**Date:** [DATE]
**Duration:** [DURATION]
**Severity:** [P1/P2/P3/P4]
**Impact:** [Description of user/business impact]

### Timeline
- HH:MM - [Event]
- HH:MM - [Event]

### Root Cause
[Description of root cause]

### Resolution
[Steps taken to resolve]

### Lessons Learned
1. [Lesson]
2. [Lesson]

### Action Items
- [ ] [Action] - Owner: [Name] - Due: [Date]
- [ ] [Action] - Owner: [Name] - Due: [Date]

### Metrics
- Time to Detection: [X minutes]
- Time to Resolution: [X minutes]
- Customer Impact: [X users / X% requests]
```

---

## Appendix: Useful Commands

### Quick Health Check

```bash
# All-in-one health check script
#!/bin/bash

echo "=== RDS Status ==="
aws rds describe-db-instances --db-instance-identifier sentinel-db --query 'DBInstances[0].DBInstanceStatus'

echo "=== Redis Status ==="
aws elasticache describe-cache-clusters --cache-cluster-id sentinel-redis --query 'CacheClusters[0].CacheClusterStatus'

echo "=== ECS Services ==="
aws ecs describe-services --cluster sentinel-production --services sentinel-api sentinel-celery --query 'services[*].[serviceName,runningCount,desiredCount]'

echo "=== ALB Health ==="
aws elbv2 describe-target-health --target-group-arn <TG_ARN> --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State]'

echo "=== API Health ==="
curl -s -o /dev/null -w "%{http_code}" https://api.sentinel.ai/health
```

---

**Document Owner:** Platform Engineering
**Review Cycle:** Quarterly
**Last Review:** 2026-01-17
