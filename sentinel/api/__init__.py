"""
Sentinel API Server
Production-ready FastAPI server integrating all 4 phases
"""

from .server import app, create_app
from .config import APIConfig

__all__ = ['app', 'create_app', 'APIConfig']
