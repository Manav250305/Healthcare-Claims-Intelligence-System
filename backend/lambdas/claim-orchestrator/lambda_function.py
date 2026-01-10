import json
import boto3
import os
import time

lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

RESULTS_TABLE = os.environ['RESULTS_TABLE']

def lambda_handler(event, context):
    """
    Orchestrates the complete claim processing workflow
    Triggered after PDF extraction completes
    """
    
    try:
        claim_id = event.get('claim_id')
        
        if not claim_id:
            # Try to extract from DynamoDB stream event
            if 'Records' in event:
                record = event['Records'][0]
                if record['eventName'] == 'INSERT':
                    claim_id = record['dynamodb']['Keys']['claim_id']['S']
        
        if not claim_id:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Missing claim_id'})}
        
        print(f"🚀 Starting orchestration for claim: {claim_id}")
        
        # Get initial claim data
        table = dynamodb.Table(RESULTS_TABLE)
        response = table.get_item(Key={'claim_id': claim_id})
        
        if 'Item' not in response:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Claim not found'})}
        
        claim_data = response['Item']
        
        # Step 1: Medical Entity Extraction
        print("Step 1: Extracting medical entities...")
        medical_payload = {
            'claim_id': claim_id,
            'extracted_text': claim_data.get('extracted_text', ''),
            'key_value_pairs': claim_data.get('key_value_pairs', {})
        }
        
        medical_response = lambda_client.invoke(
            FunctionName='OpenAIMedicalExtractor',
            InvocationType='RequestResponse',
            Payload=json.dumps(medical_payload)
        )
        
        medical_result = json.loads(medical_response['Payload'].read())
        print(f"✅ Medical extraction: {medical_result.get('statusCode')}")
        
        # Small delay to ensure DynamoDB consistency
        time.sleep(2)
        
        # Step 2: Risk Scoring
        print("Step 2: Calculating risk score...")
        risk_payload = {
            'claim_id': claim_id
        }
        
        risk_response = lambda_client.invoke(
            FunctionName='RiskScorer',
            InvocationType='RequestResponse',
            Payload=json.dumps(risk_payload)
        )
        
        risk_result = json.loads(risk_response['Payload'].read())
        print(f"✅ Risk scoring: {risk_result.get('statusCode')}")
        
        # Update final status
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression="SET processing_complete = :complete, completed_at = :completed",
            ExpressionAttributeValues={
                ':complete': True,
                ':completed': int(time.time())
            }
        )
        
        print(f"🎉 Processing complete for claim: {claim_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'claim_id': claim_id,
                'message': 'Processing complete',
                'medical_extraction': medical_result.get('statusCode') == 200,
                'risk_scoring': risk_result.get('statusCode') == 200
            })
        }
        
    except Exception as e:
        print(f"❌ Orchestration error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
