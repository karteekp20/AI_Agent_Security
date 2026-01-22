# Month 1-2: Infrastructure & DevOps Implementation Guide

**Objective:** Production deployment and CI/CD automation
**Timeline:** 8 weeks
**Prerequisites:** Docker setup already exists (docker-compose.yml, Dockerfile)

---

## Table of Contents

1. [Week 1-2: AWS Production Setup](#week-1-2-aws-production-setup)
2. [Week 3-4: CI/CD Pipeline](#week-3-4-cicd-pipeline)
3. [Week 5-6: Monitoring & Alerting](#week-5-6-monitoring--alerting)
4. [Week 7-8: Backup & Disaster Recovery](#week-7-8-backup--disaster-recovery)

---

## Week 1-2: AWS Production Setup

### Step 1: AWS Account Setup

```bash
# 1.1 Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 1.2 Configure AWS credentials
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)

# 1.3 Verify configuration
aws sts get-caller-identity
```

### Step 2: Create VPC and Networking

```bash
# 2.1 Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=sentinel-vpc}]'
# Save VPC_ID from output

# 2.2 Create Subnets (2 public, 2 private for multi-AZ)
# Public subnet 1 (us-east-1a)
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=sentinel-public-1a}]'

# Public subnet 2 (us-east-1b)
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone us-east-1b --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=sentinel-public-1b}]'

# Private subnet 1 (us-east-1a)
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.3.0/24 --availability-zone us-east-1a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=sentinel-private-1a}]'

# Private subnet 2 (us-east-1b)
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.4.0/24 --availability-zone us-east-1b --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=sentinel-private-1b}]'

# 2.3 Create Internet Gateway
aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=sentinel-igw}]'
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

# 2.4 Create NAT Gateway (for private subnets)
aws ec2 allocate-address --domain vpc  # Get Elastic IP
aws ec2 create-nat-gateway --subnet-id $PUBLIC_SUBNET_1A --allocation-id $EIP_ALLOC_ID
```

### Step 3: Create RDS PostgreSQL

```bash
# 3.1 Create DB Subnet Group
aws rds create-db-subnet-group \
  --db-subnet-group-name sentinel-db-subnet \
  --db-subnet-group-description "Sentinel DB Subnets" \
  --subnet-ids $PRIVATE_SUBNET_1A $PRIVATE_SUBNET_1B

# 3.2 Create Security Group for RDS
aws ec2 create-security-group \
  --group-name sentinel-rds-sg \
  --description "Security group for Sentinel RDS" \
  --vpc-id $VPC_ID

# Allow PostgreSQL from ECS security group (port 5432)
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $ECS_SG_ID

# 3.3 Create RDS Instance
aws rds create-db-instance \
  --db-instance-identifier sentinel-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username sentinel_admin \
  --master-user-password "CHANGE_THIS_STRONG_PASSWORD" \
  --allocated-storage 100 \
  --storage-type gp3 \
  --vpc-security-group-ids $RDS_SG_ID \
  --db-subnet-group-name sentinel-db-subnet \
  --backup-retention-period 7 \
  --multi-az \
  --storage-encrypted \
  --no-publicly-accessible \
  --tags Key=Environment,Value=production
```

### Step 4: Create ElastiCache Redis

```bash
# 4.1 Create Cache Subnet Group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name sentinel-redis-subnet \
  --cache-subnet-group-description "Sentinel Redis Subnets" \
  --subnet-ids $PRIVATE_SUBNET_1A $PRIVATE_SUBNET_1B

# 4.2 Create Security Group for Redis
aws ec2 create-security-group \
  --group-name sentinel-redis-sg \
  --description "Security group for Sentinel Redis" \
  --vpc-id $VPC_ID

aws ec2 authorize-security-group-ingress \
  --group-id $REDIS_SG_ID \
  --protocol tcp \
  --port 6379 \
  --source-group $ECS_SG_ID

# 4.3 Create Redis Cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id sentinel-redis \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --cache-subnet-group-name sentinel-redis-subnet \
  --security-group-ids $REDIS_SG_ID \
  --snapshot-retention-limit 7 \
  --tags Key=Environment,Value=production
```

### Step 5: Create ECR Repository

```bash
# 5.1 Create ECR repositories
aws ecr create-repository --repository-name sentinel/api --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name sentinel/frontend --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name sentinel/celery --image-scanning-configuration scanOnPush=true

# 5.2 Get ECR login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 5.3 Build and push images
docker build -t sentinel/api -f docker/Dockerfile .
docker tag sentinel/api:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/sentinel/api:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/sentinel/api:latest
```

### Step 6: Create ECS Cluster and Services

```bash
# 6.1 Create ECS Cluster
aws ecs create-cluster --cluster-name sentinel-production --capacity-providers FARGATE FARGATE_SPOT

# 6.2 Create Task Execution Role
aws iam create-role \
  --role-name sentinelEcsTaskExecutionRole \
  --assume-role-policy-document file://infrastructure/ecs/ecs-trust-policy.json

aws iam attach-role-policy \
  --role-name sentinelEcsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# 6.3 Register Task Definition
aws ecs register-task-definition --cli-input-json file://infrastructure/ecs/api-task-definition.json

# 6.4 Create Application Load Balancer
aws elbv2 create-load-balancer \
  --name sentinel-alb \
  --subnets $PUBLIC_SUBNET_1A $PUBLIC_SUBNET_1B \
  --security-groups $ALB_SG_ID \
  --scheme internet-facing \
  --type application

# 6.5 Create Target Group
aws elbv2 create-target-group \
  --name sentinel-api-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30

# 6.6 Create ECS Service
aws ecs create-service \
  --cluster sentinel-production \
  --service-name sentinel-api \
  --task-definition sentinel-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_1A,$PRIVATE_SUBNET_1B],securityGroups=[$ECS_SG_ID],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=sentinel-api,containerPort=8000"
```

### Step 7: Create S3 Bucket for Frontend

```bash
# 7.1 Create S3 bucket
aws s3 mb s3://sentinel-frontend-production --region us-east-1

# 7.2 Configure for static website hosting
aws s3 website s3://sentinel-frontend-production --index-document index.html --error-document index.html

# 7.3 Create CloudFront distribution
aws cloudfront create-distribution --distribution-config file://infrastructure/cloudfront-config.json
```

### Step 8: Create Secrets in AWS Secrets Manager

```bash
# 8.1 Store database credentials
aws secretsmanager create-secret \
  --name sentinel/database-url \
  --secret-string "postgresql://sentinel_admin:PASSWORD@sentinel-db.xxxxxx.us-east-1.rds.amazonaws.com:5432/sentinel"

# 8.2 Store Redis URL
aws secretsmanager create-secret \
  --name sentinel/redis-url \
  --secret-string "redis://sentinel-redis.xxxxxx.cache.amazonaws.com:6379/0"

# 8.3 Store JWT secret
aws secretsmanager create-secret \
  --name sentinel/jwt-secret \
  --secret-string "$(openssl rand -base64 64)"

# 8.4 Store other secrets
aws secretsmanager create-secret \
  --name sentinel/smtp-password \
  --secret-string "your-sendgrid-api-key"
```

---

## Week 3-4: CI/CD Pipeline

### GitHub Actions Workflows

The CI/CD workflows are located at:
- `.github/workflows/ci.yml` - Continuous Integration (test, lint, security scan, build)
- `.github/workflows/deploy.yml` - Deployment to staging/production

### Configure GitHub Secrets

Go to GitHub Repository → Settings → Secrets and add:

```
AWS_ACCESS_KEY_ID          = <your-access-key>
AWS_SECRET_ACCESS_KEY      = <your-secret-key>
AWS_ACCOUNT_ID             = <12-digit-account-id>
CLOUDFRONT_DISTRIBUTION_ID = <distribution-id>
PRIVATE_SUBNET_IDS         = subnet-xxx,subnet-yyy
ECS_SG_ID                  = sg-xxx
SLACK_WEBHOOK_URL          = https://hooks.slack.com/services/xxx
```

---

## Week 5-6: Monitoring & Alerting

### CloudWatch Setup

```bash
# Create log groups
aws logs create-log-group --log-group-name /ecs/sentinel-api
aws logs create-log-group --log-group-name /ecs/sentinel-celery
aws logs create-log-group --log-group-name /ecs/sentinel-migrations

# Set retention period (30 days)
aws logs put-retention-policy --log-group-name /ecs/sentinel-api --retention-in-days 30
aws logs put-retention-policy --log-group-name /ecs/sentinel-celery --retention-in-days 30
```

### CloudWatch Alarms

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name sentinel-api-high-cpu \
  --alarm-description "API CPU utilization above 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=sentinel-production Name=ServiceName,Value=sentinel-api \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC_ARN

# 5xx error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name sentinel-api-5xx-errors \
  --alarm-description "API 5xx error rate above 1%" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=LoadBalancer,Value=app/sentinel-alb/xxxxx \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC_ARN
```

### Prometheus & Grafana

The monitoring stack configuration is located at:
- `infrastructure/monitoring/docker-compose.monitoring.yml`
- `infrastructure/monitoring/prometheus.yml`
- `infrastructure/monitoring/alertmanager.yml`
- `infrastructure/monitoring/alerts/sentinel-alerts.yml`

To deploy:
```bash
cd infrastructure/monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

---

## Week 7-8: Backup & Disaster Recovery

### RDS Automated Backups

```bash
# Enable automated backups
aws rds modify-db-instance \
  --db-instance-identifier sentinel-db \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --apply-immediately

# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier sentinel-db \
  --db-snapshot-identifier sentinel-db-manual-$(date +%Y%m%d)

# Copy snapshot to another region (disaster recovery)
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:ACCOUNT_ID:snapshot:sentinel-db-manual-20260117 \
  --target-db-snapshot-identifier sentinel-db-dr-20260117 \
  --source-region us-east-1 \
  --region eu-west-1
```

### S3 Backup for Audit Logs

The backup script is located at:
- `infrastructure/backup/backup-audit-logs.py`
- `infrastructure/backup/lifecycle-policy.json`

```bash
# Create backup bucket
aws s3 mb s3://sentinel-backups-production --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket sentinel-backups-production \
  --versioning-configuration Status=Enabled

# Apply lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket sentinel-backups-production \
  --lifecycle-configuration file://infrastructure/backup/lifecycle-policy.json
```

### Disaster Recovery Runbook

See: `docs/runbooks/DISASTER_RECOVERY.md`

---

## Success Metrics Checklist

### Infrastructure
- [ ] VPC with public/private subnets created
- [ ] RDS PostgreSQL running with Multi-AZ
- [ ] ElastiCache Redis cluster running
- [ ] ECS cluster with API and Celery services
- [ ] Application Load Balancer configured
- [ ] S3 + CloudFront for frontend

### CI/CD
- [ ] GitHub Actions workflows passing
- [ ] Automated testing on pull requests
- [ ] Security scanning (pip-audit, Trivy, Bandit)
- [ ] Automated deployment to staging
- [ ] Manual approval for production

### Monitoring
- [ ] CloudWatch log groups created
- [ ] CloudWatch alarms configured
- [ ] Prometheus + Grafana deployed
- [ ] PagerDuty integration working
- [ ] Slack notifications for alerts

### Backup & DR
- [ ] RDS automated backups (7-day retention)
- [ ] Cross-region snapshot replication
- [ ] Redis snapshots configured
- [ ] S3 lifecycle policies for audit logs
- [ ] Disaster recovery runbook documented
- [ ] DR test completed

---

## Estimated Costs (Monthly)

| Service | Cost |
|---------|------|
| ECS Fargate (2 tasks) | ~$50 |
| RDS db.t3.medium Multi-AZ | ~$100 |
| ElastiCache cache.t3.medium | ~$50 |
| ALB | ~$20 |
| S3 + CloudFront | ~$10 |
| CloudWatch | ~$20 |
| Secrets Manager | ~$5 |
| **Total** | **~$255/month** |

---

## Next Steps After Month 2

1. Add auto-scaling policies for ECS
2. Implement blue-green deployments
3. Add WAF (Web Application Firewall)
4. Set up AWS Shield for DDoS protection
5. Implement cost monitoring with AWS Budgets
