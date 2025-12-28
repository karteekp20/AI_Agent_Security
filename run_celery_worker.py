#!/usr/bin/env python3
"""
Celery Worker Runner
Starts the Celery worker for report generation tasks
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only what's needed for Celery
from sentinel.saas.celery_app import celery_app

if __name__ == "__main__":
    # Start the worker
    celery_app.worker_main(argv=[
        'worker',
        '--loglevel=info',
        '--concurrency=2',
        '--pool=solo'  # Use solo pool to avoid fork issues
    ])
