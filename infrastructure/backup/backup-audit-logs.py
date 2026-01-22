#!/usr/bin/env python3
"""
Daily backup of audit logs to S3 with lifecycle policies.

This script is designed to run as:
- AWS Lambda function (triggered by EventBridge)
- ECS scheduled task
- Kubernetes CronJob

Features:
- Exports audit logs from PostgreSQL to JSON
- Uploads to S3 with server-side encryption
- Supports date-based partitioning
- Includes error handling and logging
"""

import boto3
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
S3_BUCKET = os.environ.get('S3_BACKUP_BUCKET', 'sentinel-backups-production')
DATABASE_URL = os.environ.get('DATABASE_URL')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')


def get_db_connection():
    """Create database connection using SQLAlchemy."""
    from sqlalchemy import create_engine

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required")

    engine = create_engine(DATABASE_URL)
    return engine


def fetch_audit_logs(date: str) -> List[Dict[str, Any]]:
    """
    Fetch audit logs for a specific date.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        List of audit log records as dictionaries
    """
    from sqlalchemy import text

    engine = get_db_connection()

    query = text("""
        SELECT
            id,
            session_id,
            user_input,
            is_threat,
            threat_details,
            created_at,
            organization_id,
            workspace_id,
            api_key_id
        FROM audit_logs
        WHERE DATE(created_at) = :date
        ORDER BY created_at
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'date': date})
        logs = []

        for row in result:
            log_dict = dict(row._mapping)
            # Convert datetime objects to ISO format strings
            if log_dict.get('created_at'):
                log_dict['created_at'] = log_dict['created_at'].isoformat()
            logs.append(log_dict)

    return logs


def upload_to_s3(data: List[Dict], date: str) -> Dict[str, Any]:
    """
    Upload backup data to S3.

    Args:
        data: List of audit log records
        date: Date string for the backup

    Returns:
        S3 upload response metadata
    """
    s3 = boto3.client('s3', region_name=AWS_REGION)

    # Create JSON content
    json_data = json.dumps(data, default=str, indent=2, ensure_ascii=False)

    # S3 key with date-based partitioning
    key = f"audit-logs/year={date[:4]}/month={date[5:7]}/day={date[8:10]}/audit-logs.json"

    # Upload with server-side encryption
    response = s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json_data.encode('utf-8'),
        ContentType='application/json',
        ServerSideEncryption='AES256',
        Metadata={
            'backup-date': date,
            'record-count': str(len(data)),
            'backup-timestamp': datetime.utcnow().isoformat()
        }
    )

    logger.info(f"Uploaded {len(data)} records to s3://{S3_BUCKET}/{key}")

    return {
        'bucket': S3_BUCKET,
        'key': key,
        'record_count': len(data),
        'etag': response.get('ETag'),
        'version_id': response.get('VersionId')
    }


def backup_audit_logs(date: str = None) -> Dict[str, Any]:
    """
    Main backup function.

    Args:
        date: Optional date to backup (defaults to yesterday)

    Returns:
        Backup result metadata
    """
    # Default to yesterday's logs
    if date is None:
        yesterday = datetime.now() - timedelta(days=1)
        date = yesterday.strftime('%Y-%m-%d')

    logger.info(f"Starting backup for date: {date}")

    try:
        # Fetch logs from database
        logs = fetch_audit_logs(date)

        if not logs:
            logger.warning(f"No audit logs found for {date}")
            return {
                'status': 'success',
                'message': 'No logs to backup',
                'date': date,
                'record_count': 0
            }

        # Upload to S3
        upload_result = upload_to_s3(logs, date)

        logger.info(f"Backup completed successfully: {upload_result}")

        return {
            'status': 'success',
            'date': date,
            **upload_result
        }

    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return {
            'status': 'error',
            'date': date,
            'error': str(e)
        }


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    AWS Lambda entry point.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Lambda response
    """
    # Get date from event or use yesterday
    date = event.get('date')

    result = backup_audit_logs(date)

    return {
        'statusCode': 200 if result['status'] == 'success' else 500,
        'body': json.dumps(result)
    }


def main():
    """Command-line entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Backup audit logs to S3')
    parser.add_argument(
        '--date',
        help='Date to backup (YYYY-MM-DD format, defaults to yesterday)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Number of days to backup (starting from --date or yesterday)'
    )

    args = parser.parse_args()

    start_date = args.date
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Backup multiple days if requested
    for i in range(args.days):
        backup_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
        result = backup_audit_logs(backup_date)
        print(json.dumps(result, indent=2))

        if result['status'] == 'error':
            sys.exit(1)


if __name__ == '__main__':
    main()
