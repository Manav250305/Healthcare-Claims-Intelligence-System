import json
import boto3
import os
from datetime import datetime
from decimal import Decimal


dynamodb = boto3.resource('dynamodb')
secretsmanager = boto3.client('secretsmanager')


RESULTS_TABLE = os.environ['RESULTS_TABLE']
SECRET_NAME = os.environ.get('SECRET_NAME', 'healthcare-claim/openai-key')


CACHED_API_KEY = None


def get_openai_key():
    """Retrieve OpenAI key from Secrets Manager (cached)"""
    global CACHED_API_KEY
    
    if CACHED_API_KEY:
        return CACHED_API_KEY
    
    try:
        response = secretsmanager.get_secret_value(SecretId=SECRET_NAME)
        secret = json.loads(response['SecretString'])
        CACHED_API_KEY = secret['api_key']
        return CACHED_API_KEY
    except Exception as e:
        print(f"Failed to retrieve secret: {str(e)}")
        return None


def convert_floats_to_decimal(obj):
    """Recursively convert float to Decimal for DynamoDB"""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj


def lambda_handler(event, context):
    """Extract medical entities using OpenAI API or rule-based fallback"""
    
    try:
        claim_id = event['claim_id']
        extracted_text = event.get('extracted_text', '')
        key_value_pairs = event.get('key_value_pairs', {})
        
        print(f"Processing medical extraction for claim: {claim_id}")
        
        # Get OpenAI key from Secrets Manager
        openai_key = get_openai_key()
        
        if openai_key:
            medical_data = extract_with_openai(extracted_text, openai_key)
        else:
            print("OpenAI key not available, using rule-based extraction")
            medical_data = extract_with_rules(extracted_text, key_value_pairs)
        
        # Convert floats to Decimal for DynamoDB
        medical_data = convert_floats_to_decimal(medical_data)
        
        # Store in DynamoDB
        table = dynamodb.Table(RESULTS_TABLE)
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression="SET medical_entities = :entities, #status = :status, updated_at = :updated",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':entities': medical_data,
                ':status': 'MEDICAL_ANALYSIS_COMPLETE',
                ':updated': datetime.now().isoformat()
            }
        )
        
        print(f"✅ Medical entities extracted and saved")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'claim_id': claim_id,
                'medical_data': medical_data
            }, default=str)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def extract_with_openai(text, api_key):
    """Extract using OpenAI API"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        text_sample = text[:4000]
        
        prompt = f"""Extract medical information from this claim and return as JSON:


{text_sample}


Return ONLY valid JSON with this structure:
{{
  "patient": {{"name": "", "age": "", "gender": "", "id": ""}},
  "diagnosis_codes": ["ICD-10 codes"],
  "procedure_codes": ["CPT codes"],
  "medications": ["medication names"],
  "conditions": ["medical conditions"],
  "provider": {{"name": "", "npi": ""}},
  "claim_amount": ""
}}"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a medical claim data extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        medical_data_str = response.choices.message.content.strip()
        
        # Clean markdown code blocks
        if '```json' in medical_data_str:
            medical_data_str = medical_data_str.split('```json').split('```').strip()
        elif '```' in medical_data_str:
            medical_data_str = medical_data_str.split('```').split('```').strip()
        
        medical_data = json.loads(medical_data_str)
        medical_data['extraction_method'] = 'openai'
        medical_data['cost'] = {
            'input_tokens': response.usage.prompt_tokens,
            'output_tokens': response.usage.completion_tokens,
            'estimated_usd': round(response.usage.prompt_tokens * 0.0000005 + 
                                  response.usage.completion_tokens * 0.0000015, 6)
        }
        
        print(f"✅ OpenAI extraction successful, cost: ${medical_data['cost']['estimated_usd']}")
        
        return medical_data
        
    except Exception as e:
        print(f"OpenAI extraction failed: {str(e)}, falling back to rule-based")
        return extract_with_rules(text, {})


def extract_with_rules(text, key_value_pairs):
    """Rule-based extraction (FREE fallback)"""
    import re
    
    medical_data = {
        'patient': {},
        'diagnosis_codes': [],
        'procedure_codes': [],
        'medications': [],
        'conditions': [],
        'provider': {},
        'claim_amount': '',
        'extraction_method': 'rule_based'
    }
    
    if key_value_pairs:
        medical_data['patient'] = {
            'name': key_value_pairs.get('patient_name', ''),
            'id': key_value_pairs.get('patient_id', ''),
            'age': key_value_pairs.get('patient_age', ''),
            'gender': key_value_pairs.get('patient_gender', '')
        }
        medical_data['claim_amount'] = key_value_pairs.get('total_charge', '')
        medical_data['provider']['name'] = key_value_pairs.get('provider_name', '')
    
    # Extract ICD-10 codes
    icd_pattern = r'\b[A-Z]\d{2}\.?\d{0,4}\b'
    medical_data['diagnosis_codes'] = list(set(re.findall(icd_pattern, text)))
    
    # Extract CPT codes
    cpt_pattern = r'\bCPT[:\s]*(\d{5})\b|\b(\d{5})\b(?=.*procedure)'
    cpt_matches = re.findall(cpt_pattern, text, re.IGNORECASE)
    medical_data['procedure_codes'] = list(set([m or m for m in cpt_matches if m or m]))
    
    # Extract medications
    medication_pattern = r'\b([A-Z][a-z]+(?:in|ol|ide|mab|tinib))\b'
    medications = re.findall(medication_pattern, text)
    medical_data['medications'] = list(set(medications))[:10]
    
    return medical_data
