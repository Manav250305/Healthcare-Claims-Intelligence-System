import json
import boto3
import os
from decimal import Decimal
from urllib.parse import unquote

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'HealthcareClaims'))

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    try:
        # Get claim_id from path parameters (supports proxy+, id, and claim_id)
        path_params = event.get('pathParameters', {})
        claim_id = path_params.get('proxy') or path_params.get('id') or path_params.get('claim_id')
        
        if claim_id:
            # URL decode the claim_id (handles slashes and special characters)
            claim_id = unquote(claim_id)
        
        if not claim_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Missing claim_id'})
            }
        
        print(f"Fetching claim: {claim_id}")
        response = table.get_item(Key={'claim_id': claim_id})
        
        if 'Item' not in response:
            print(f"Claim not found: {claim_id}")
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Claim not found', 'claim_id': claim_id})
            }
        
        print(f"Claim found successfully")
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response['Item'], cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(e)})
        }
