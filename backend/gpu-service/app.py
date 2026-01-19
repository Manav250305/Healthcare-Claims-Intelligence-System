from flask import Flask, request, jsonify
import torch
from transformers import AutoTokenizer, AutoModel, pipeline
import os
import logging
from datetime import datetime
import boto3
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize CloudWatch client for custom metrics
cloudwatch = boto3.client('cloudwatch', region_name=os.getenv('AWS_REGION', 'us-east-1'))

# Model configuration
MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"
device = "cpu"

# Global model variables
tokenizer = None
model = None
qa_pipeline = None

def initialize_model():
    """Initialize Bio_ClinicalBERT model for CPU inference"""
    global tokenizer, model, qa_pipeline
    
    try:
        logger.info(f"Loading {MODEL_NAME} on CPU...")
        
        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModel.from_pretrained(MODEL_NAME)
        
        # Set model to evaluation mode and optimize for CPU
        model.eval()
        model.to(device)
        
        # Create question-answering pipeline
        qa_pipeline = pipeline(
            "question-answering",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            device=-1  # CPU inference
        )
        
        logger.info("Model loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return False

# Initialize model on startup
initialize_model()

def send_cloudwatch_metric(metric_name, value, unit='Count'):
    """Send custom metrics to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace='HealthcareClaims/ProService',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit,
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error sending CloudWatch metric: {str(e)}")

def analyze_medical_document(text, query):
    """Analyze medical document using Bio_ClinicalBERT"""
    try:
        # Use question-answering pipeline
        result = qa_pipeline(question=query, context=text)
        
        # Get embeddings for detailed analysis
        inputs = tokenizer(text, return_tensors="pt", 
                          truncation=True, max_length=512, padding=True)
        
        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state
        
        # Extract key medical entities and insights
        analysis = {
            "answer": result['answer'],
            "confidence": result['score'],
            "embedding_shape": list(embeddings.shape),
            "document_length": len(text),
            "tokens_processed": inputs['input_ids'].shape[1]
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error in document analysis: {str(e)}")
        raise

def extract_medical_insights(text):
    """Extract comprehensive medical insights from document"""
    insights = {}
    
    # Define key questions for medical document analysis
    questions = [
        "What is the primary diagnosis?",
        "What treatments are recommended?",
        "What medications are prescribed?",
        "What are the test results?",
        "What is the patient's condition?"
    ]
    
    for question in questions:
        try:
            result = qa_pipeline(question=question, context=text[:2000])
            if result['score'] > 0.1:  # Confidence threshold
                insights[question] = {
                    "answer": result['answer'],
                    "confidence": round(result['score'], 3)
                }
        except:
            continue
    
    return insights

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for ALB"""
    if model is not None and tokenizer is not None:
        return jsonify({
            "status": "healthy",
            "model": MODEL_NAME,
            "device": device,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    else:
        return jsonify({
            "status": "unhealthy",
            "error": "Model not loaded"
        }), 503

@app.route('/analyze', methods=['POST'])
def analyze_document():
    """Main endpoint for Pro version document analysis"""
    start_time = datetime.utcnow()
    
    try:
        # Validate request
        if not request.json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        document_text = request.json.get('document_text', '')
        query = request.json.get('query', 'Summarize the medical document')
        user_id = request.json.get('user_id', 'unknown')
        
        if not document_text:
            return jsonify({"error": "document_text is required"}), 400
        
        logger.info(f"Processing request for user: {user_id}")
        
        # Perform analysis
        analysis_result = analyze_medical_document(document_text, query)
        
        # Extract comprehensive insights
        insights = extract_medical_insights(document_text)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Send metrics to CloudWatch
        send_cloudwatch_metric('RequestsProcessed', 1)
        send_cloudwatch_metric('ProcessingTime', processing_time * 1000, 'Milliseconds')
        
        response = {
            "status": "success",
            "model": MODEL_NAME,
            "service_tier": "pro",
            "analysis": analysis_result,
            "insights": insights,
            "processing_time_seconds": round(processing_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Request completed in {processing_time:.2f}s")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        send_cloudwatch_metric('RequestErrors', 1)
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/batch-analyze', methods=['POST'])
def batch_analyze():
    """Batch processing endpoint for multiple documents"""
    try:
        if not request.json or 'documents' not in request.json:
            return jsonify({"error": "documents array is required"}), 400
        
        documents = request.json['documents']
        results = []
        
        for idx, doc in enumerate(documents):
            try:
                text = doc.get('text', '')
                query = doc.get('query', 'Summarize the medical document')
                
                analysis = analyze_medical_document(text, query)
                results.append({
                    "document_index": idx,
                    "status": "success",
                    "analysis": analysis
                })
            except Exception as e:
                results.append({
                    "document_index": idx,
                    "status": "error",
                    "error": str(e)
                })
        
        send_cloudwatch_metric('BatchRequestsProcessed', len(documents))
        
        return jsonify({
            "status": "success",
            "total_documents": len(documents),
            "results": results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/model-info', methods=['GET'])
def model_info():
    """Return information about the loaded model"""
    return jsonify({
        "model_name": MODEL_NAME,
        "device": device,
        "model_loaded": model is not None,
        "service_tier": "pro",
        "features": [
            "Detailed medical document analysis",
            "Clinical entity extraction",
            "Medical question answering",
            "Batch processing support"
        ]
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
