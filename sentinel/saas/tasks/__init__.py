"""
Celery Tasks
Background job processing for report generation, emails, etc.
"""

from .report_tasks import generate_report_task

__all__ = ["generate_report_task"]
