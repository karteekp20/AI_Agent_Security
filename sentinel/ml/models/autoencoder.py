"""Autoencoder model for deep anomaly detection"""

from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Check for PyTorch availability
try:
    import torch
    import torch.nn as nn
    import torch.utils.data
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Autoencoder features disabled.")


def _create_module_class():
    """Create the Autoencoder class with proper inheritance"""
    if not TORCH_AVAILABLE:
        # Return a dummy class if PyTorch isn't available
        class DummyAutoencoder:
            def __init__(self, *args, **kwargs):
                raise ImportError(
                    "PyTorch is required for Autoencoder. "
                    "Install with: pip install torch"
                )
        return DummyAutoencoder

    class Autoencoder(nn.Module):
        """
        Deep autoencoder for anomaly detection.

        Architecture:
        - Encoder: input_dim -> hidden_dims -> encoding_dim
        - Decoder: encoding_dim -> hidden_dims (reversed) -> input_dim

        Anomaly detection works by measuring reconstruction error:
        - Normal inputs reconstruct well (low error)
        - Anomalous inputs reconstruct poorly (high error)
        """

        def __init__(
            self,
            input_dim: int = 17,
            encoding_dim: int = 8,
            hidden_dims: Tuple[int, ...] = (14, 10),
            dropout: float = 0.1,
        ):
            super().__init__()
            self.input_dim = input_dim
            self.encoding_dim = encoding_dim
            self.hidden_dims = hidden_dims

            # Build encoder
            encoder_layers: List[nn.Module] = []
            prev_dim = input_dim
            for hidden_dim in hidden_dims:
                encoder_layers.extend([
                    nn.Linear(prev_dim, hidden_dim),
                    nn.ReLU(),
                    nn.BatchNorm1d(hidden_dim),
                    nn.Dropout(dropout),
                ])
                prev_dim = hidden_dim
            encoder_layers.append(nn.Linear(prev_dim, encoding_dim))
            self.encoder = nn.Sequential(*encoder_layers)

            # Build decoder (mirror of encoder)
            decoder_layers: List[nn.Module] = []
            prev_dim = encoding_dim
            for hidden_dim in reversed(hidden_dims):
                decoder_layers.extend([
                    nn.Linear(prev_dim, hidden_dim),
                    nn.ReLU(),
                    nn.BatchNorm1d(hidden_dim),
                    nn.Dropout(dropout),
                ])
                prev_dim = hidden_dim
            decoder_layers.append(nn.Linear(prev_dim, input_dim))
            self.decoder = nn.Sequential(*decoder_layers)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """Forward pass through encoder and decoder"""
            encoded = self.encoder(x)
            decoded = self.decoder(encoded)
            return decoded

        def encode(self, x: torch.Tensor) -> torch.Tensor:
            """Get encoded representation"""
            return self.encoder(x)

        def get_reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
            """Calculate per-sample reconstruction error (anomaly score)"""
            reconstructed = self.forward(x)
            return torch.mean((x - reconstructed) ** 2, dim=1)

    return Autoencoder


# Create the Autoencoder class
Autoencoder = _create_module_class()


class AutoencoderWrapper:
    """
    Wrapper for autoencoder training and inference.

    Provides a scikit-learn-like interface (fit/predict/decision_function).
    """

    def __init__(
        self,
        model: Optional[Any] = None,
        threshold: float = 0.1,
        input_dim: int = 17,
        encoding_dim: int = 8,
        hidden_dims: Tuple[int, ...] = (14, 10),
    ):
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch is required for AutoencoderWrapper. "
                "Install with: pip install torch"
            )

        self.model = model
        self.threshold = threshold
        self.input_dim = input_dim
        self.encoding_dim = encoding_dim
        self.hidden_dims = hidden_dims
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._is_fitted = model is not None

    def fit(
        self,
        X: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        validation_split: float = 0.1,
        early_stopping_patience: int = 10,
    ) -> Dict[str, Any]:
        """
        Train the autoencoder.

        Args:
            X: Training data of shape (n_samples, n_features)
            epochs: Number of training epochs
            batch_size: Batch size for training
            learning_rate: Learning rate for optimizer
            validation_split: Fraction of data for validation
            early_stopping_patience: Epochs to wait for improvement

        Returns:
            Dictionary with training metrics
        """
        if self.model is None:
            self.model = Autoencoder(
                input_dim=X.shape[1],
                encoding_dim=self.encoding_dim,
                hidden_dims=self.hidden_dims,
            )

        self.model.to(self.device)
        self.model.train()

        # Split into train/val
        n_samples = len(X)
        n_val = int(n_samples * validation_split)
        indices = np.random.permutation(n_samples)

        X_train = X[indices[n_val:]]
        X_val = X[indices[:n_val]] if n_val > 0 else X_train[:batch_size]

        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train).to(self.device)
        X_val_tensor = torch.FloatTensor(X_val).to(self.device)

        # Create data loader
        train_dataset = torch.utils.data.TensorDataset(X_train_tensor, X_train_tensor)
        train_loader = torch.utils.data.DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
        )

        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()

        train_losses = []
        val_losses = []
        best_val_loss = float('inf')
        patience_counter = 0
        best_state = None

        for epoch in range(epochs):
            # Training
            self.model.train()
            epoch_loss = 0.0
            for batch_x, _ in train_loader:
                optimizer.zero_grad()
                output = self.model(batch_x)
                loss = criterion(output, batch_x)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            train_loss = epoch_loss / len(train_loader)
            train_losses.append(train_loss)

            # Validation
            self.model.eval()
            with torch.no_grad():
                val_output = self.model(X_val_tensor)
                val_loss = criterion(val_output, X_val_tensor).item()
                val_losses.append(val_loss)

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = self.model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break

            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"Epoch {epoch + 1}/{epochs}: "
                    f"train_loss={train_loss:.6f}, val_loss={val_loss:.6f}"
                )

        # Restore best model
        if best_state:
            self.model.load_state_dict(best_state)

        # Calculate threshold based on training data
        self.model.eval()
        with torch.no_grad():
            errors = self.model.get_reconstruction_error(X_train_tensor)
            errors_np = errors.cpu().numpy()
            # Set threshold at mean + 2*std
            self.threshold = float(errors_np.mean() + 2 * errors_np.std())

        self._is_fitted = True

        return {
            "final_train_loss": train_losses[-1],
            "final_val_loss": val_losses[-1],
            "best_val_loss": best_val_loss,
            "threshold": self.threshold,
            "epochs_trained": len(train_losses),
            "train_samples": len(X_train),
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict anomalies.

        Args:
            X: Data to predict

        Returns:
            Array of predictions: -1 for anomaly, 1 for normal
        """
        scores = self.decision_function(X)
        return np.where(scores < -self.threshold, -1, 1)

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """
        Get anomaly scores.

        Args:
            X: Data to score

        Returns:
            Array of scores (more negative = more anomalous)
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        self.model.eval()
        X_tensor = torch.FloatTensor(X).to(self.device)

        with torch.no_grad():
            errors = self.model.get_reconstruction_error(X_tensor)

        # Return negative errors (to match sklearn convention)
        return -errors.cpu().numpy()

    def get_reconstruction(self, X: np.ndarray) -> np.ndarray:
        """
        Get reconstructed output.

        Args:
            X: Input data

        Returns:
            Reconstructed data
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before reconstruction")

        self.model.eval()
        X_tensor = torch.FloatTensor(X).to(self.device)

        with torch.no_grad():
            reconstructed = self.model(X_tensor)

        return reconstructed.cpu().numpy()

    def get_encoding(self, X: np.ndarray) -> np.ndarray:
        """
        Get encoded representation.

        Args:
            X: Input data

        Returns:
            Encoded representation
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before encoding")

        self.model.eval()
        X_tensor = torch.FloatTensor(X).to(self.device)

        with torch.no_grad():
            encoded = self.model.encode(X_tensor)

        return encoded.cpu().numpy()
