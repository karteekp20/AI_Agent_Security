"""ML Model Training Pipeline"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import pickle
from pathlib import Path
import logging
from uuid import UUID

import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """
    Orchestrates ML model training for anomaly detection.

    Supports:
    - Isolation Forest for general anomaly detection
    - Autoencoder for deep learning-based detection (optional)
    - User baseline generation
    """

    def __init__(self, db_adapter, model_storage_path: str = "./models"):
        self.db = db_adapter
        self.storage_path = Path(model_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def train_isolation_forest(
        self,
        org_id: str,
        feature_data: np.ndarray,
        contamination: float = 0.1,
        n_estimators: int = 100,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Train Isolation Forest model for anomaly detection.

        Args:
            org_id: Organization ID
            feature_data: Training data (n_samples, n_features)
            contamination: Expected proportion of anomalies
            n_estimators: Number of trees in the forest
            feature_names: Optional list of feature names

        Returns:
            Dictionary with training results
        """
        if len(feature_data) < 10:
            raise ValueError("Insufficient training data (need at least 10 samples)")

        logger.info(f"Training Isolation Forest for org {org_id} with {len(feature_data)} samples")

        model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=-1,
            max_samples='auto'
        )
        model.fit(feature_data)

        # Calculate training metrics
        scores = model.decision_function(feature_data)
        predictions = model.predict(feature_data)

        metrics = {
            "training_samples": len(feature_data),
            "feature_count": feature_data.shape[1],
            "anomaly_count": int((predictions == -1).sum()),
            "anomaly_rate": float((predictions == -1).mean()),
            "mean_score": float(scores.mean()),
            "std_score": float(scores.std()),
            "min_score": float(scores.min()),
            "max_score": float(scores.max()),
            "trained_at": datetime.utcnow().isoformat(),
        }

        # Get next version number
        model_version = await self._get_next_version(org_id, "isolation_forest")

        # Save model to file
        model_filename = f"{org_id}_isolation_forest_v{model_version}.pkl"
        model_path = self.storage_path / model_filename

        with open(model_path, "wb") as f:
            pickle.dump({
                "model": model,
                "feature_names": feature_names,
                "metrics": metrics,
                "version": model_version,
            }, f)

        # Record in database
        await self._save_model_metadata(
            org_id=org_id,
            model_type="isolation_forest",
            version=model_version,
            path=str(model_path),
            metrics=metrics,
            feature_names=feature_names,
        )

        logger.info(f"Saved Isolation Forest v{model_version} for org {org_id}")

        return {
            "version": model_version,
            "metrics": metrics,
            "path": str(model_path),
            "model_type": "isolation_forest",
        }

    async def train_autoencoder(
        self,
        org_id: str,
        feature_data: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Train Autoencoder model for deep anomaly detection.

        Args:
            org_id: Organization ID
            feature_data: Training data (n_samples, n_features)
            epochs: Number of training epochs
            batch_size: Batch size for training
            feature_names: Optional list of feature names

        Returns:
            Dictionary with training results
        """
        try:
            from ..models.autoencoder import AutoencoderWrapper
        except ImportError:
            raise ImportError("PyTorch required for autoencoder training")

        if len(feature_data) < 50:
            raise ValueError("Insufficient training data for autoencoder (need at least 50 samples)")

        logger.info(f"Training Autoencoder for org {org_id} with {len(feature_data)} samples")

        wrapper = AutoencoderWrapper()
        training_results = wrapper.fit(
            feature_data,
            epochs=epochs,
            batch_size=batch_size,
        )

        metrics = {
            "training_samples": len(feature_data),
            "feature_count": feature_data.shape[1],
            "final_loss": training_results["final_train_loss"],
            "threshold": training_results["threshold"],
            "epochs": epochs,
            "trained_at": datetime.utcnow().isoformat(),
        }

        model_version = await self._get_next_version(org_id, "autoencoder")
        model_filename = f"{org_id}_autoencoder_v{model_version}.pkl"
        model_path = self.storage_path / model_filename

        with open(model_path, "wb") as f:
            pickle.dump({
                "wrapper": wrapper,
                "feature_names": feature_names,
                "metrics": metrics,
                "version": model_version,
            }, f)

        await self._save_model_metadata(
            org_id=org_id,
            model_type="autoencoder",
            version=model_version,
            path=str(model_path),
            metrics=metrics,
            feature_names=feature_names,
        )

        logger.info(f"Saved Autoencoder v{model_version} for org {org_id}")

        return {
            "version": model_version,
            "metrics": metrics,
            "path": str(model_path),
            "model_type": "autoencoder",
        }

    async def update_user_baseline(
        self,
        org_id: str,
        user_id: str,
        features: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Update or create user behavioral baseline.

        Args:
            org_id: Organization ID
            user_id: User ID
            features: Feature vector for the user

        Returns:
            Updated baseline info
        """
        if self.db is None:
            logger.warning("No database adapter - cannot update baseline")
            return {"status": "skipped", "reason": "no database"}

        try:
            from sentinel.saas.models.user_baseline import UserBaseline

            # Try to find existing baseline
            baseline = self.db.query(UserBaseline).filter(
                UserBaseline.org_id == org_id,
                UserBaseline.user_id == user_id,
            ).first()

            if baseline:
                # Update existing baseline with exponential moving average
                alpha = 0.1  # Weight for new data
                existing = baseline.feature_vector or {}
                updated = {}
                for key in set(existing.keys()) | set(features.keys()):
                    old_val = existing.get(key, features.get(key, 0))
                    new_val = features.get(key, old_val)
                    updated[key] = alpha * new_val + (1 - alpha) * old_val

                baseline.feature_vector = updated
                baseline.sample_count = (baseline.sample_count or 0) + 1
                self.db.commit()

                return {
                    "status": "updated",
                    "sample_count": baseline.sample_count,
                    "user_id": user_id,
                }
            else:
                # Create new baseline
                new_baseline = UserBaseline(
                    org_id=UUID(org_id) if isinstance(org_id, str) else org_id,
                    user_id=user_id,
                    feature_vector=features,
                    sample_count=1,
                )
                self.db.add(new_baseline)
                self.db.commit()

                return {
                    "status": "created",
                    "sample_count": 1,
                    "user_id": user_id,
                }
        except Exception as e:
            logger.error(f"Error updating baseline for user {user_id}: {e}")
            self.db.rollback()
            return {"status": "error", "error": str(e)}

    async def _get_next_version(self, org_id: str, model_type: str) -> int:
        """Get the next version number for a model"""
        if self.db is None:
            return 1

        try:
            from sentinel.saas.models.ml_model import MLModel
            from sqlalchemy import func

            result = self.db.query(func.max(MLModel.model_version)).filter(
                MLModel.org_id == org_id,
                MLModel.model_type == model_type,
            ).scalar()

            return (result or 0) + 1
        except Exception as e:
            logger.error(f"Error getting next version: {e}")
            return 1

    async def _save_model_metadata(
        self,
        org_id: str,
        model_type: str,
        version: int,
        path: str,
        metrics: Dict[str, Any],
        feature_names: Optional[List[str]] = None,
    ):
        """Save model metadata to database"""
        if self.db is None:
            logger.warning("No database adapter - cannot save model metadata")
            return

        try:
            from sentinel.saas.models.ml_model import MLModel

            model_record = MLModel(
                org_id=UUID(org_id) if isinstance(org_id, str) else org_id,
                model_type=model_type,
                model_version=version,
                model_path=path,
                metrics=metrics,
                feature_names=feature_names,
                status="active",
            )

            # Archive previous versions
            self.db.query(MLModel).filter(
                MLModel.org_id == org_id,
                MLModel.model_type == model_type,
                MLModel.status == "active",
            ).update({"status": "archived"})

            self.db.add(model_record)
            self.db.commit()
            logger.info(f"Saved model metadata: {model_type} v{version} for org {org_id}")
        except Exception as e:
            logger.error(f"Error saving model metadata: {e}")
            self.db.rollback()

    async def load_model(
        self,
        org_id: str,
        model_type: str = "isolation_forest",
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Load a trained model from storage.

        Args:
            org_id: Organization ID
            model_type: Type of model to load
            version: Specific version (latest if None)

        Returns:
            Loaded model data or None
        """
        if self.db is None:
            # Try to load from default path
            model_files = list(self.storage_path.glob(f"{org_id}_{model_type}_v*.pkl"))
            if not model_files:
                return None
            model_path = max(model_files, key=lambda p: int(p.stem.split('_v')[-1]))
        else:
            try:
                from sentinel.saas.models.ml_model import MLModel

                query = self.db.query(MLModel).filter(
                    MLModel.org_id == org_id,
                    MLModel.model_type == model_type,
                )

                if version:
                    query = query.filter(MLModel.model_version == version)
                else:
                    query = query.filter(MLModel.status == "active")

                model_record = query.first()
                if not model_record:
                    return None

                model_path = Path(model_record.model_path)
            except Exception as e:
                logger.error(f"Error loading model metadata: {e}")
                return None

        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return None

        try:
            with open(model_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
