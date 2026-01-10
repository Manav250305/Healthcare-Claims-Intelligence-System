import json
import boto3
import os
from datetime import datetime
from urllib.parse import unquote_plus

s3_client = boto3.client('s3')
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET', '')

def lambda_handler(event, context):
    """Generate pre-signed URL for secure S3 upload"""
    
    try:
        # Extract user info from Cognito authorizer
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        user_id = claims.get('sub', 'anonymous')
        
        # Get filename from query parameters
        params = event.get('queryStringParameters', {})
        if not params or 'filename' not in params:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Missing filename parameter'})
            }
        
        original_filename = unquote_plus(params['filename'])
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_extension = original_filename.split('.')[-1].lower()
        s3_key = f"{user_id}/{timestamp}_{original_filename}"
        
        # Validate file type
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
        if file_extension not in allowed_extensions:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
                })
            }
        
        # Determine content type
        content_type = 'application/pdf' if file_extension == 'pdf' else 'image/jpeg'
        
        # Generate pre-signed URL (valid for 5 minutes)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': UPLOAD_BUCKET,
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=300  # 5 minutes
        )
        
        print(f"✅ Generated pre-signed URL for user: {user_id}, file: {s3_key}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'uploadUrl': presigned_url,
                'fileKey': s3_key,
                'expiresIn': 300
            })
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }
