"""Training Scheduler for periodic model retraining"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import asyncio
import logging
from uuid import UUID

import numpy as np

from .pipeline import TrainingPipeline

logger = logging.getLogger(__name__)


class TrainingScheduler:
    """
    Schedules and manages model retraining jobs.

    Features:
    - Periodic retraining based on configurable intervals
    - Automatic retraining when data drift is detected
    - Per-organization training schedules
    """

    def __init__(
        self,
        training_pipeline: TrainingPipeline,
        db_adapter,
        default_interval_hours: int = 24,
        min_samples_for_training: int = 100,
    ):
        self.pipeline = training_pipeline
        self.db = db_adapter
        self.default_interval_hours = default_interval_hours
        self.min_samples = min_samples_for_training
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, interval_hours: Optional[int] = None):
        """Start the scheduler"""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._running = True
        interval = interval_hours or self.default_interval_hours
        self._task = asyncio.create_task(self._run_loop(interval))
        logger.info(f"Training scheduler started with {interval}h interval")

    async def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Training scheduler stopped")

    async def _run_loop(self, interval_hours: int):
        """Main scheduler loop"""
        while self._running:
            try:
                await self._check_and_train()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Training scheduler error: {e}")

            # Sleep until next check
            try:
                await asyncio.sleep(interval_hours * 3600)
            except asyncio.CancelledError:
                break

    async def _check_and_train(self):
        """Check which organizations need retraining and trigger"""
        logger.info("Checking organizations for retraining needs")

        orgs = await self._get_orgs_for_retraining()

        for org in orgs:
            org_id = org.get("org_id")
            try:
                logger.info(f"Collecting training data for org {org_id}")
                features = await self._collect_training_data(org_id)

                if len(features) < self.min_samples:
                    logger.info(f"Insufficient data for org {org_id}: {len(features)} samples")
                    continue

                logger.info(f"Training model for org {org_id} with {len(features)} samples")
                result = await self.pipeline.train_isolation_forest(
                    org_id=str(org_id),
                    feature_data=features,
                )
                logger.info(f"Training complete for org {org_id}: {result}")

            except Exception as e:
                logger.error(f"Training failed for org {org_id}: {e}")

    async def _get_orgs_for_retraining(self) -> List[Dict[str, Any]]:
        """Get organizations that need model retraining"""
        if self.db is None:
            return []

        try:
            from sentinel.saas.models.organization import Organization
            from sentinel.saas.models.ml_model import MLModel
            from sqlalchemy import func, or_

            # Get all active organizations
            orgs = self.db.query(Organization).filter(
                Organization.status == "active"
            ).all()

            orgs_for_training = []

            for org in orgs:
                # Check if org has a recent model
                latest_model = self.db.query(MLModel).filter(
                    MLModel.org_id == org.org_id,
                    MLModel.model_type == "isolation_forest",
                    MLModel.status == "active",
                ).first()

                should_train = False

                if not latest_model:
                    # No model exists - should train
                    should_train = True
                elif latest_model.created_at:
                    # Check if model is older than threshold
                    age = datetime.utcnow() - latest_model.created_at.replace(tzinfo=None)
                    if age > timedelta(hours=self.default_interval_hours):
                        should_train = True

                if should_train:
                    orgs_for_training.append({
                        "org_id": org.org_id,
                        "org_name": org.org_name,
                    })

            return orgs_for_training

        except Exception as e:
            logger.error(f"Error getting orgs for retraining: {e}")
            return []

    async def _collect_training_data(self, org_id) -> np.ndarray:
        """Collect feature data from audit logs for training"""
        if self.db is None:
            return np.array([])

        try:
            from sentinel.saas.models.user_baseline import UserBaseline

            # Collect feature vectors from user baselines
            baselines = self.db.query(UserBaseline).filter(
                UserBaseline.org_id == org_id,
                UserBaseline.sample_count >= 5,  # Only use baselines with enough samples
            ).all()

            if not baselines:
                return np.array([])

            # Convert feature vectors to numpy array
            feature_vectors = []
            feature_names = None

            for baseline in baselines:
                if baseline.feature_vector:
                    if feature_names is None:
                        feature_names = sorted(baseline.feature_vector.keys())

                    vector = [baseline.feature_vector.get(name, 0.0) for name in feature_names]
                    feature_vectors.append(vector)

            if not feature_vectors:
                return np.array([])

            return np.array(feature_vectors, dtype=np.float32)

        except Exception as e:
            logger.error(f"Error collecting training data: {e}")
            return np.array([])

    async def trigger_training(
        self,
        org_id: str,
        model_type: str = "isolation_forest",
    ) -> Dict[str, Any]:
        """Manually trigger training for an organization"""
        logger.info(f"Manual training triggered for org {org_id}")

        features = await self._collect_training_data(org_id)

        if len(features) < self.min_samples:
            return {
                "status": "skipped",
                "reason": f"Insufficient data ({len(features)} samples, need {self.min_samples})",
            }

        if model_type == "isolation_forest":
            result = await self.pipeline.train_isolation_forest(
                org_id=org_id,
                feature_data=features,
            )
        elif model_type == "autoencoder":
            result = await self.pipeline.train_autoencoder(
                org_id=org_id,
                feature_data=features,
            )
        else:
            return {"status": "error", "reason": f"Unknown model type: {model_type}"}

        return {"status": "completed", "result": result}

    async def check_data_drift(
        self,
        org_id: str,
        new_features: np.ndarray,
        threshold: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Check if there's significant data drift that warrants retraining.

        Uses a simple approach: compare mean/std of new data with training data.
        """
        model_data = await self.pipeline.load_model(org_id)

        if not model_data or "metrics" not in model_data:
            return {"drift_detected": False, "reason": "no baseline model"}

        metrics = model_data["metrics"]
        old_mean = metrics.get("mean_score", 0)
        old_std = metrics.get("std_score", 1)

        # Calculate new data statistics
        new_mean = float(new_features.mean())
        new_std = float(new_features.std())

        # Simple drift detection
        mean_drift = abs(new_mean - old_mean) / max(abs(old_mean), 1e-6)
        std_drift = abs(new_std - old_std) / max(abs(old_std), 1e-6)

        drift_detected = mean_drift > threshold or std_drift > threshold

        return {
            "drift_detected": drift_detected,
            "mean_drift": mean_drift,
            "std_drift": std_drift,
            "threshold": threshold,
            "recommendation": "retrain" if drift_detected else "stable",
        }
