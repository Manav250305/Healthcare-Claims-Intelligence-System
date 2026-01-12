import json
import boto3
import os
from decimal import Decimal
from urllib.parse import unquote

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'HealthcareClaims'))

# CORS headers to include in all responses
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,OPTIONS'
}

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    try:
        # Get claim_id from path parameters
        path_params = event.get('pathParameters', {})
        claim_id = path_params.get('proxy') or path_params.get('id') or path_params.get('claim_id')
        
        if claim_id:
            claim_id = unquote(claim_id)
        
        if not claim_id:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Missing claim_id'})
            }
        
        print(f"Fetching claim: {claim_id}")
        response = table.get_item(Key={'claim_id': claim_id})
        
        if 'Item' not in response:
            print(f"Claim not found: {claim_id}")
            return {
                'statusCode': 404,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Claim not found', 'claim_id': claim_id})
            }
        
        print(f"Claim found successfully")
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(response['Item'], cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(e)})
        }
