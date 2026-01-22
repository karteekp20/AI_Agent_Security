# Sentinel AI Agent Security Platform

## Project Overview
Multi-tenant SaaS security platform for AI/LLM agents. Provides PII detection, prompt injection prevention, content moderation, and compliance reporting.

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Celery
- **Database:** PostgreSQL (with RLS for multi-tenancy), Redis
- **Frontend:** React, TypeScript (in `frontend/`)
- **Infrastructure:** Docker, AWS (ECS, RDS, ElastiCache)

## Directory Structure

```
sentinel/                    # Main Python package
├── input_guard.py          # PII detection, injection prevention
├── output_guard.py         # Response validation
├── state_monitor.py        # Loop/cost detection
├── gateway.py              # LangGraph orchestration
├── content_moderation.py   # Content safety
├── schemas.py              # Pydantic models
│
├── saas/                   # Multi-tenant SaaS layer
│   ├── server.py          # FastAPI app entry point
│   ├── database.py        # DB connection, session
│   ├── config.py          # Settings
│   ├── models/            # SQLAlchemy models
│   │   ├── organization.py
│   │   ├── user.py
│   │   ├── workspace.py
│   │   ├── policy.py      # Custom security policies
│   │   ├── api_key.py
│   │   └── report.py
│   ├── routers/           # API endpoints
│   │   ├── auth.py        # Login, registration
│   │   ├── organizations.py
│   │   ├── workspaces.py
│   │   ├── policies.py
│   │   ├── api_keys.py
│   │   ├── dashboard.py   # Analytics endpoints
│   │   ├── audit.py       # Audit log queries
│   │   └── reports.py     # Compliance reports
│   ├── schemas/           # Pydantic request/response
│   ├── auth/              # JWT, password, API key auth
│   ├── services/          # Business logic
│   ├── tasks/             # Celery async tasks
│   └── reports/           # Compliance (SOC2, HIPAA, GDPR, PCI-DSS)
│
├── meta_learning/         # ML/Pattern discovery
│   ├── pattern_discoverer.py  # Auto-discover attack patterns
│   ├── threat_intelligence.py # External threat feeds
│   ├── rule_manager.py
│   ├── approval_workflow.py
│   └── schemas.py
│
├── storage/               # Database adapters
│   ├── postgres_adapter.py
│   └── redis_adapter.py
│
├── observability/         # Monitoring
│   ├── metrics.py         # Prometheus metrics
│   ├── tracing.py         # OpenTelemetry
│   └── logging.py
│
└── resilience/            # Reliability patterns
    ├── circuit_breaker.py
    ├── rate_limiter.py
    └── retry.py

frontend/                   # React frontend
infrastructure/            # AWS/Docker configs
docs/                      # Documentation
└── roadmap/              # Implementation guides
    ├── MONTH_1_2_INFRASTRUCTURE_GUIDE.md
    ├── MONTH_3_4_ADVANCED_SECURITY_GUIDE.md
    ├── MONTH_3_4_BACKEND_IMPLEMENTATION.md
    └── MONTH_3_4_FRONTEND_IMPLEMENTATION.md
```

## Key Models

### Organization (Tenant)
- `org_id`, `org_name`, `subscription_tier`
- Has many: users, workspaces, policies

### Policy (Custom Security Rules)
- `policy_id`, `org_id`, `policy_name`, `policy_type`
- `policy_config` (JSONB) - flexible configuration
- `status`: draft → testing → active → archived
- `test_percentage` - for A/B testing
- `parent_policy_id` - version chain

### User
- `user_id`, `org_id`, `email`, `role`
- Roles: owner, admin, member, viewer

## API Structure
- Base: `/api/v1/`
- Auth: `/auth/login`, `/auth/register`
- Resources: `/organizations`, `/workspaces`, `/policies`, `/api-keys`
- Analytics: `/dashboard/metrics`, `/dashboard/recent-threats`
- Audit: `/audit/logs`, `/audit/export`

## Running Locally
```bash
# Backend
docker-compose up -d
uvicorn sentinel.saas.server:app --reload

# Frontend
cd frontend && npm run dev
```

## Month 3-4: New Code Structure (To Be Implemented)

### New Directories
```
sentinel/
├── ml/                          # NEW: ML Pipeline
│   ├── __init__.py
│   ├── anomaly_detector.py      # Main detection service
│   ├── feature_engineering.py   # Extract features from audit logs
│   ├── behavioral_analysis.py   # User behavior profiling
│   ├── models/
│   │   ├── isolation_forest.py  # Anomaly detection model
│   │   └── autoencoder.py       # Deep learning model
│   └── training/
│       ├── pipeline.py          # Training pipeline
│       └── scheduler.py         # Scheduled retraining
│
├── policy/                      # NEW: Advanced Policy Engine
│   └── dsl/
│       ├── __init__.py
│       ├── grammar.py           # PLY lexer/parser for DSL
│       ├── evaluator.py         # Execute parsed DSL
│       └── validator.py         # Syntax validation
│
├── integrations/                # NEW: External Integrations
│   ├── __init__.py
│   ├── webhooks.py              # Webhook delivery with HMAC
│   ├── slack.py                 # Slack Bot integration
│   ├── teams.py                 # MS Teams integration
│   └── siem.py                  # Syslog/CEF/Splunk export
│
├── analytics/                   # NEW: Security Analytics
│   ├── __init__.py
│   ├── pipeline.py              # Time-series aggregation
│   ├── trend_analyzer.py        # Trend detection
│   └── risk_scoring.py          # Org-level risk scores
│
└── meta_learning/
    └── feed_connectors.py       # NEW: AlienVault, MISP, abuse.ch

sentinel/saas/
├── services/                    # NEW Services
│   ├── policy_versioning.py     # Git-like version control
│   ├── ab_testing.py            # A/B test framework
│   └── policy_templates.py      # Template library
│
├── models/                      # NEW Models
│   ├── ml_model.py              # ML model metadata
│   ├── user_baseline.py         # Behavioral baselines
│   ├── webhook.py               # Webhook configs
│   ├── webhook_delivery.py      # Delivery logs
│   └── integration.py           # Integration configs
│
└── routers/                     # NEW Endpoints
    ├── ml.py                    # /ml/anomaly/analyze, /ml/models
    ├── ab_tests.py              # /ab-tests
    ├── templates.py             # /policies/templates
    ├── webhooks.py              # /webhooks
    └── integrations.py          # /integrations/slack, /integrations/siem
```

### New Database Tables
```sql
ml_models         -- Model metadata, version, metrics, S3 path
user_baselines    -- Per-user behavioral feature vectors
webhooks          -- Webhook URLs, secrets, subscribed events
webhook_deliveries-- Delivery attempts, status, retries
integrations      -- Slack/Teams/SIEM configurations
```

### New API Endpoints
```
POST /api/v1/ml/anomaly/analyze     -- Real-time anomaly detection
GET  /api/v1/ml/models              -- List ML models
POST /api/v1/ml/models/train        -- Trigger training

GET  /api/v1/policies/{id}/versions -- Version history
POST /api/v1/policies/{id}/versions -- Create version
POST /api/v1/policies/{id}/rollback -- Rollback to version
GET  /api/v1/policies/templates     -- List templates
POST /api/v1/policies/templates/instantiate

POST /api/v1/ab-tests               -- Create A/B test
GET  /api/v1/ab-tests/{id}/results  -- Test metrics
POST /api/v1/ab-tests/{id}/conclude -- End test

POST /api/v1/webhooks               -- Create webhook
GET  /api/v1/webhooks               -- List webhooks
POST /api/v1/webhooks/{id}/test     -- Test delivery

POST /api/v1/integrations/slack     -- Setup Slack
POST /api/v1/integrations/siem/export
```

### Key Classes to Implement

**ML Pipeline:**
- `FeatureExtractor` - Extract 17 features from audit logs
- `AnomalyDetector` - Isolation Forest wrapper
- `BehavioralAnalyzer` - User baseline management
- `AnomalyDetectionService` - Real-time inference API

**Policy Engine:**
- `PolicyVersionControl` - Version history, diff, rollback
- `ABTestingService` - Traffic splitting, metrics
- `DSLParser` - PLY-based parser for policy DSL
- `PolicyTemplateService` - Template instantiation

**Integrations:**
- `WebhookService` - Delivery with retry, HMAC signing
- `SlackIntegration` - Block Kit messages
- `SIEMExporter` - Syslog/CEF/Splunk formats

### Implementation Reference
See detailed code examples in:
- `docs/roadmap/MONTH_3_4_BACKEND_IMPLEMENTATION.md`
- `docs/roadmap/MONTH_3_4_FRONTEND_IMPLEMENTATION.md`

## Code Conventions
- Type hints required
- Pydantic for validation
- SQLAlchemy 2.0 style
- Async where possible
- RLS for tenant isolation
