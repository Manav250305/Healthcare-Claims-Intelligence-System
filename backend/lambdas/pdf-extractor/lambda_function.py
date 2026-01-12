import json
import boto3
import os
from datetime import datetime

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

RESULTS_TABLE = os.environ['RESULTS_TABLE']

def lambda_handler(event, context):
    """Download PDF and trigger orchestrator - text extraction moved to orchestrator"""
    
    try:
        # Get S3 object details
        if 'Records' in event:
            record = event['Records'][0]  # Fixed: added [0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
        else:
            bucket = event['bucket']
            key = event['key']
        
        print(f"Processing PDF: s3://{bucket}/{key}")
        
        # Get PDF metadata
        obj_metadata = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = obj_metadata['ContentLength']
        
        # Store initial record in DynamoDB
        claim_id = key
        user_id = key.split('/')[0] if '/' in key else 'unknown'  # Fixed: added [0]
        
        table = dynamodb.Table(RESULTS_TABLE)
        table.put_item(
            Item={
                'claim_id': claim_id,
                'user_id': user_id,
                'timestamp': int(datetime.now().timestamp()),
                'status': 'UPLOADED',
                's3_bucket': bucket,
                's3_key': key,
                'file_size': file_size,
                'created_at': datetime.now().isoformat(),
                'processing_complete': False  # Added this
            }
        )
        
        print(f"✅ Recorded upload: {file_size} bytes")
        
        # Trigger orchestrator for processing
        print("🚀 Triggering orchestrator...")
        lambda_client.invoke(
            FunctionName='ClaimOrchestrator',
            InvocationType='Event',
            Payload=json.dumps({'claim_id': claim_id})
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'PDF processing initiated',
                'claim_id': claim_id
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
