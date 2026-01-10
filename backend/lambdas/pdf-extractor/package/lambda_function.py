import json
import boto3
import os
from io import BytesIO
import PyPDF2
import pdfplumber
from datetime import datetime

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

RESULTS_TABLE = os.environ['RESULTS_TABLE']

def lambda_handler(event, context):
    """Extract text from PDF and trigger orchestrator"""
    
    try:
        # Get S3 object details
        if 'Records' in event:
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
        else:
            bucket = event['bucket']
            key = event['key']
        
        print(f"Processing PDF: s3://{bucket}/{key}")
        
        # Download PDF
        pdf_obj = s3_client.get_object(Bucket=bucket, Key=key)
        pdf_data = pdf_obj['Body'].read()
        pdf_file = BytesIO(pdf_data)
        
        # Extract text using PyPDF2
        extracted_text = ""
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            extracted_text += f"\n--- Page {page_num + 1} ---\n{text}"
        
        # Extract key-value pairs
        key_value_pairs = extract_key_value_pairs(extracted_text)
        
        # Store in DynamoDB
        claim_id = key
        user_id = key.split('/')[0] if '/' in key else 'unknown'
        
        table = dynamodb.Table(RESULTS_TABLE)
        table.put_item(
            Item={
                'claim_id': claim_id,
                'user_id': user_id,
                'timestamp': int(datetime.now().timestamp()),
                'status': 'TEXT_EXTRACTED',
                's3_bucket': bucket,
                's3_key': key,
                'extracted_text': extracted_text[:50000],
                'key_value_pairs': key_value_pairs,
                'page_count': len(pdf_reader.pages),
                'created_at': datetime.now().isoformat()
            }
        )
        
        print(f"✅ Extracted {len(extracted_text)} characters from {len(pdf_reader.pages)} pages")
        
        # Trigger orchestrator for further processing
        print("🚀 Triggering orchestrator...")
        lambda_client.invoke(
            FunctionName='ClaimOrchestrator',
            InvocationType='Event',  # Async
            Payload=json.dumps({'claim_id': claim_id})
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'PDF processing initiated',
                'claim_id': claim_id,
                'page_count': len(pdf_reader.pages)
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


def extract_key_value_pairs(text):
    """Extract key-value pairs from text"""
    import re
    
    key_value_pairs = {}
    
    patterns = {
        'patient_name': r'Patient Name[:\s]+([^\n]+)',
        'patient_id': r'Patient ID[:\s]+([^\n]+)',
        'patient_age': r'Age[:\s]+(\d+)',
        'patient_gender': r'Gender[:\s]+([^\n]+)',
        'date_of_service': r'Date of Service[:\s]+([^\n]+)',
        'diagnosis': r'Diagnosis[:\s]+([^\n]+)',
        'procedure': r'Procedure[:\s]+([^\n]+)',
        'total_charge': r'Total Charge[:\s]+\$?([\d,\.]+)',
        'provider_name': r'Provider Name[:\s]+([^\n]+)',
        'insurance_id': r'Insurance ID[:\s]+([^\n]+)',
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            key_value_pairs[field] = match.group(1).strip()
    
    return key_value_pairs
