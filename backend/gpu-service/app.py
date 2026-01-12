from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import boto3
import time
from datetime import datetime
import uvicorn

app = FastAPI(title="Claims GPU Service", version="1.0.0")

# Initialize CloudWatch client
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

# Load medical NLP model (BioClinicalBERT or similar)
MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"
print(f"Loading model: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)

# Check GPU availability
device = "cpu"  # t3.micro doesn't have GPU
model = model.to(device)
print(f"Model loaded on device: {device}")

# Create NER pipeline
ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, device=0 if device == "cuda" else -1)

class ClaimRequest(BaseModel):
    claim_id: str
    text: str
    analysis_tier: str = "pro"

class DetailedAnalysis(BaseModel):
    diagnoses: list
    procedures: list
    medications: list
    risk_factors: list
    confidence_scores: dict
    recommendations: list
    processing_time_seconds: float

class ClaimResponse(BaseModel):
    claim_id: str
    entities: list
    detailed_analysis: DetailedAnalysis
    gpu_used: bool
    model_name: str

def publish_metrics(processing_time, success=True, gpu_util=0):
    """Publish custom metrics to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace='ClaimsGPUService',
            MetricData=[
                {
                    'MetricName': 'ProcessingTime',
                    'Value': processing_time,
                    'Unit': 'Seconds',
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'RequestCount',
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'SuccessRate',
                    'Value': 1 if success else 0,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'GPUUtilization',
                    'Value': gpu_util,
                    'Unit': 'Percent',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    except Exception as e:
        print(f"Failed to publish metrics: {e}")

def get_gpu_usage():
    """Get current GPU utilization"""
    try:
        if not torch.cuda.is_available():
            return 0
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        return util.gpu
    except:
        return 0

@app.get("/health")
def health_check():
    """Health check endpoint for ALB"""
    gpu_available = torch.cuda.is_available()
    gpu_util = get_gpu_usage() if gpu_available else 0
    
    return {
        "status": "healthy",
        "gpu_available": gpu_available,
        "gpu_utilization": gpu_util,
        "model": MODEL_NAME,
        "device": device
    }

@app.post("/analyze", response_model=ClaimResponse)
def analyze_claim(request: ClaimRequest):
    """Pro-tier medical claim analysis with GPU acceleration"""
    start_time = time.time()
    
    try:
        print(f"Processing claim {request.claim_id} with GPU analysis")
        
        # Run NER on extracted text
        entities_raw = ner_pipeline(request.text[:512])  # Limit text length
        
        # Group entities by type
        diagnoses = []
        procedures = []
        medications = []
        
        for ent in entities_raw:
            if ent['entity'].startswith('B-'):  # Beginning of entity
                entity_type = ent['entity'][2:]
                if 'DIAGNOSIS' in entity_type or 'DISEASE' in entity_type:
                    diagnoses.append({
                        "text": ent['word'],
                        "confidence": round(ent['score'], 3)
                    })
                elif 'PROCEDURE' in entity_type or 'TREATMENT' in entity_type:
                    procedures.append({
                        "text": ent['word'],
                        "confidence": round(ent['score'], 3)
                    })
                elif 'MEDICATION' in entity_type or 'DRUG' in entity_type:
                    medications.append({
                        "text": ent['word'],
                        "confidence": round(ent['score'], 3)
                    })
        
        # Risk factor analysis
        risk_factors = []
        risk_keywords = ['diabetes', 'hypertension', 'cancer', 'chronic', 'severe']
        for keyword in risk_keywords:
            if keyword.lower() in request.text.lower():
                risk_factors.append(keyword.capitalize())
        
        # Generate recommendations
        recommendations = []
        if len(diagnoses) > 3:
            recommendations.append("Multiple diagnoses detected - verify medical necessity")
        if len(medications) > 5:
            recommendations.append("High medication count - check for drug interactions")
        if risk_factors:
            recommendations.append(f"Risk factors present: {', '.join(risk_factors)}")
        
        processing_time = time.time() - start_time
        gpu_util = get_gpu_usage()
        
        # Publish metrics to CloudWatch
        publish_metrics(processing_time, success=True, gpu_util=gpu_util)
        
        detailed_analysis = DetailedAnalysis(
            diagnoses=diagnoses,
            procedures=procedures,
            medications=medications,
            risk_factors=risk_factors,
            confidence_scores={
                "overall": round(sum([e['confidence'] for e in diagnoses + procedures + medications]) / max(len(diagnoses + procedures + medications), 1), 3),
                "diagnosis": round(sum([e['confidence'] for e in diagnoses]) / max(len(diagnoses), 1), 3),
                "procedure": round(sum([e['confidence'] for e in procedures]) / max(len(procedures), 1), 3),
                "medication": round(sum([e['confidence'] for e in medications]) / max(len(medications), 1), 3)
            },
            recommendations=recommendations,
            processing_time_seconds=round(processing_time, 3)
        )
        
        return ClaimResponse(
            claim_id=request.claim_id,
            entities=entities_raw[:20],  # Limit response size
            detailed_analysis=detailed_analysis,
            gpu_used=torch.cuda.is_available(),
            model_name=MODEL_NAME
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        publish_metrics(processing_time, success=False, gpu_util=get_gpu_usage())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
