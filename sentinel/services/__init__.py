from typing import Dict, Any

class ServiceRegistry:
    """Central registry for all services"""

    _instances: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, service: Any) -> None:
        cls._instances[name] = service

    @classmethod
    def get(cls, name: str) -> Any:
        return cls._instances.get(name)


# Service initialization
def init_services(db, config):
    """Initialize all services"""
    from sentinel.ml.anomaly_detector import AnomalyDetectionService
    from sentinel.saas.services.policy_versioning import PolicyVersionControl
    from sentinel.saas.services.ab_testing import ABTestingService
    from sentinel.integrations.webhooks import WebhookService

    ServiceRegistry.register("anomaly", AnomalyDetectionService(
        model_path=config.get("ML_MODEL_PATH"),
        db_adapter=db,
    ))

    ServiceRegistry.register("policy_versions", PolicyVersionControl(db))
    ServiceRegistry.register("ab_testing", ABTestingService(db))
    ServiceRegistry.register("webhooks", WebhookService(db))