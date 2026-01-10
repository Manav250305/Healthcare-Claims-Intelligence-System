import json
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
RESULTS_TABLE = os.environ['RESULTS_TABLE']

def lambda_handler(event, context):
    """
    Calculate risk score using rule-based logic
    100% FREE - No external API calls
    """
    
    try:
        claim_id = event['claim_id']
        
        # Get claim data from DynamoDB
        table = dynamodb.Table(RESULTS_TABLE)
        response = table.get_item(Key={'claim_id': claim_id})
        
        if 'Item' not in response:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Claim not found'})}
        
        claim_data = response['Item']
        medical_entities = claim_data.get('medical_entities', {})
        key_value_pairs = claim_data.get('key_value_pairs', {})
        
        # Initialize risk scoring
        risk_score = 0
        risk_breakdown = []
        flags = []
        
        # Rule 1: Missing Critical Information (max 15 points)
        required_fields = ['patient_name', 'date_of_service', 'diagnosis', 'procedure']
        missing_fields = []
        for field in required_fields:
            if not key_value_pairs.get(field) and not medical_entities.get('patient', {}).get('name'):
                missing_fields.append(field)
        
        if missing_fields:
            points = len(missing_fields) * 4
            risk_score += points
            risk_breakdown.append({
                'category': 'Missing Information',
                'points': points,
                'severity': 'MEDIUM',
                'details': f"Missing: {', '.join(missing_fields)}"
            })
            flags.append('INCOMPLETE_DATA')
        
        # Rule 2: High Claim Amount (max 25 points)
        claim_amount_str = key_value_pairs.get('total_charge', '') or medical_entities.get('claim_amount', '0')
        try:
            claim_amount = float(str(claim_amount_str).replace('$', '').replace(',', '') or '0')
        except:
            claim_amount = 0
        
        if claim_amount > 10000:
            risk_score += 25
            risk_breakdown.append({
                'category': 'High Claim Amount',
                'points': 25,
                'severity': 'HIGH',
                'details': f"${claim_amount:,.2f} exceeds $10,000 threshold"
            })
            flags.append('HIGH_AMOUNT')
        elif claim_amount > 5000:
            risk_score += 15
            risk_breakdown.append({
                'category': 'Elevated Claim Amount',
                'points': 15,
                'severity': 'MEDIUM',
                'details': f"${claim_amount:,.2f} exceeds $5,000 threshold"
            })
            flags.append('ELEVATED_AMOUNT')
        elif claim_amount > 2000:
            risk_score += 8
            risk_breakdown.append({
                'category': 'Above Average Amount',
                'points': 8,
                'severity': 'LOW',
                'details': f"${claim_amount:,.2f} above typical claim"
            })
        
        # Rule 3: Multiple Procedures (max 20 points)
        procedure_codes = medical_entities.get('procedure_codes', [])
        if len(procedure_codes) > 5:
            risk_score += 20
            risk_breakdown.append({
                'category': 'Multiple Procedures',
                'points': 20,
                'severity': 'HIGH',
                'details': f"{len(procedure_codes)} procedures performed"
            })
            flags.append('MULTIPLE_PROCEDURES')
        elif len(procedure_codes) > 3:
            risk_score += 10
            risk_breakdown.append({
                'category': 'Several Procedures',
                'points': 10,
                'severity': 'MEDIUM',
                'details': f"{len(procedure_codes)} procedures"
            })
        
        # Rule 4: Multiple Diagnoses (max 15 points)
        diagnosis_codes = medical_entities.get('diagnosis_codes', [])
        conditions = medical_entities.get('conditions', [])
        total_diagnoses = len(diagnosis_codes) + len(conditions)
        
        if total_diagnoses > 4:
            risk_score += 15
            risk_breakdown.append({
                'category': 'Multiple Diagnoses',
                'points': 15,
                'severity': 'MEDIUM',
                'details': f"{total_diagnoses} diagnoses/conditions listed"
            })
            flags.append('COMPLEX_CASE')
        elif total_diagnoses > 2:
            risk_score += 8
            risk_breakdown.append({
                'category': 'Several Diagnoses',
                'points': 8,
                'severity': 'LOW',
                'details': f"{total_diagnoses} diagnoses"
            })
        
        # Rule 5: Incomplete Patient Information (max 15 points)
        patient = medical_entities.get('patient', {})
        patient_fields = [patient.get('name'), patient.get('id'), patient.get('age'), patient.get('gender')]
        missing_patient_fields = sum(1 for f in patient_fields if not f)
        
        if missing_patient_fields > 2:
            risk_score += 15
            risk_breakdown.append({
                'category': 'Incomplete Patient Data',
                'points': 15,
                'severity': 'MEDIUM',
                'details': f"{missing_patient_fields} patient fields missing"
            })
            flags.append('INCOMPLETE_PATIENT_INFO')
        elif missing_patient_fields > 0:
            risk_score += 7
            risk_breakdown.append({
                'category': 'Some Patient Data Missing',
                'points': 7,
                'severity': 'LOW',
                'details': f"{missing_patient_fields} fields missing"
            })
        
        # Rule 6: No Diagnosis Codes (10 points)
        if not diagnosis_codes and not conditions:
            risk_score += 10
            risk_breakdown.append({
                'category': 'Missing Diagnosis',
                'points': 10,
                'severity': 'MEDIUM',
                'details': 'No diagnosis codes found'
            })
            flags.append('NO_DIAGNOSIS')
        
        # Rule 7: No Procedure Codes (10 points)
        if not procedure_codes:
            risk_score += 10
            risk_breakdown.append({
                'category': 'Missing Procedures',
                'points': 10,
                'severity': 'MEDIUM',
                'details': 'No procedure codes found'
            })
            flags.append('NO_PROCEDURES')
        
        # Determine risk level and action
        if risk_score <= 20:
            risk_level = 'LOW'
            action = 'AUTO_APPROVE'
            color = 'green'
        elif risk_score <= 50:
            risk_level = 'MEDIUM'
            action = 'MANUAL_REVIEW'
            color = 'yellow'
        else:
            risk_level = 'HIGH'
            action = 'DETAILED_INVESTIGATION'
            color = 'red'
        
        # Calculate confidence score
        total_possible_points = 100
        confidence = round((1 - (risk_score / total_possible_points)) * 100, 2)
        
        # Create comprehensive risk analysis
        risk_analysis = {
            'claim_id': claim_id,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'recommended_action': action,
            'confidence_score': confidence,
            'color_indicator': color,
            'flags': flags,
            'risk_breakdown': risk_breakdown,
            'statistics': {
                'total_diagnoses': total_diagnoses,
                'total_procedures': len(procedure_codes),
                'total_medications': len(medical_entities.get('medications', [])),
                'claim_amount': float(claim_amount) if claim_amount else 0
            },
            'timestamp': datetime.now().isoformat(),
            'processing_method': 'rule_based_scoring_v1'
        }
        
        # Store in DynamoDB
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression="SET risk_analysis = :analysis, #status = :status, final_score = :score",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':analysis': json.loads(json.dumps(risk_analysis), parse_float=Decimal),
                ':status': 'SCORING_COMPLETE',
                ':score': Decimal(str(risk_score))
            }
        )
        
        print(f"✅ Risk Analysis Complete: Score={risk_score}/100, Level={risk_level}, Action={action}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(risk_analysis, default=str)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
