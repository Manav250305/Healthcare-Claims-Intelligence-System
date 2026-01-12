# Healthcare Claims Intelligence System

A comprehensive system for intelligent processing and analysis of healthcare insurance claims using AI/ML and AWS cloud services.

## Overview

This system leverages natural language processing, machine learning, and AWS Lambda for automated claim analysis and processing. It includes:

- **GPU-accelerated NLP Service**: FastAPI-based service using Bio-ClinicalBERT for medical entity recognition
- **Serverless Claim Processing**: AWS Lambda functions for orchestration, PDF extraction, and risk scoring
- **Web Frontend**: React-based UI for claim submission and result visualization
- **Cloud Infrastructure**: Terraform and CloudFormation templates for AWS deployment

## Project Structure

```
healthcare-claim-intelligence/
├── backend/
│   ├── gpu-service/              # FastAPI GPU service for NLP analysis
│   │   ├── app.py               # Main FastAPI application
│   │   ├── Dockerfile           # Docker configuration
│   │   └── requirements.txt      # Python dependencies
│   ├── lambdas/                 # AWS Lambda functions
│   │   ├── claim-orchestrator/  # Main claim processing orchestrator
│   │   ├── openai-medical-extractor/  # OpenAI-based claim extraction
│   │   ├── pdf-extractor/       # PDF text extraction
│   │   ├── risk-scorer/         # Risk analysis and scoring
│   │   ├── get-claim-results/   # Claim result retrieval
│   │   └── generate-presigned-url/  # S3 URL generation
│   ├── layers/                  # Lambda layers
│   │   └── pdf-processing/      # PDF processing utilities
│   └── utils/                   # Shared utilities
├── frontend/                    # React-based web interface
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/             # Page components
│   │   ├── services/          # API services
│   │   ├── hooks/             # Custom React hooks
│   │   └── App.jsx            # Main app component
│   ├── package.json           # Node dependencies
│   └── vite.config.js         # Vite configuration
├── infrastructure/            # IaC templates
│   ├── cloudformation/        # AWS CloudFormation templates
│   └── terraform/             # Terraform configurations
├── lambda-layer-openai/       # Pre-packaged OpenAI Python layer
├── lambda-layer-openai-clean/ # Optimized OpenAI layer
├── sample-data/               # Sample claim data
├── test-samples/              # Testing utilities
└── docs/                      # Documentation
```

## Features

### Backend Services

**GPU Service** (`backend/gpu-service/`)

- FastAPI REST API for claim analysis
- Bio-ClinicalBERT model for medical entity recognition
- Named Entity Recognition (NER) for:
  - Diagnoses
  - Procedures
  - Medications
  - Risk factors
- Detailed confidence scoring and recommendations
- CloudWatch metrics publishing

**Lambda Functions**

- **Claim Orchestrator**: Coordinates entire claim processing workflow
- **PDF Extractor**: Extracts text from PDF claim documents using PDFPlumber/PDFMiner
- **OpenAI Medical Extractor**: Structured extraction using OpenAI API
- **Risk Scorer**: Automated risk assessment and scoring
- **Get Claim Results**: Retrieves processing results
- **Generate Presigned URL**: Secure S3 file access

### Frontend

- React 18 with Vite build tool
- Cognito authentication integration
- Claim submission and tracking interface
- Results visualization
- Responsive Tailwind CSS styling

## Tech Stack

### Backend

- **Framework**: FastAPI, Python
- **ML/NLP**: Hugging Face Transformers, PyTorch, Bio-ClinicalBERT
- **Cloud**: AWS Lambda, S3, CloudWatch
- **APIs**: OpenAI GPT
- **PDF Processing**: PDFPlumber, PDFMiner, PyPDF2
- **Container**: Docker

### Frontend

- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS, PostCSS
- **HTTP Client**: Axios
- **Auth**: Amazon Cognito
- **Router**: React Router v6
- **Icons**: Lucide React

### Infrastructure

- **IaC**: Terraform, AWS CloudFormation
- **Cloud Provider**: AWS

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+
- AWS Account with appropriate IAM permissions
- Docker (for GPU service)

### Backend Setup

1. **GPU Service**

```bash
cd backend/gpu-service
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

2. **Lambda Functions**

- Deploy using AWS SAM, Serverless Framework, or AWS Console
- Ensure Lambda layers are attached:
  - `lambda-layer-openai/` for OpenAI dependencies
  - `backend/layers/pdf-processing/` for PDF utilities

### Frontend Setup

```bash
cd frontend
npm install
npm run dev        # Development server on http://localhost:5173
npm run build      # Production build
npm run preview    # Preview production build
```

### Infrastructure Deployment

**Terraform**

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

**CloudFormation**

```bash
aws cloudformation create-stack \
  --stack-name healthcare-claims \
  --template-body file://infrastructure/cloudformation/template.yaml
```

## API Documentation

### GPU Service Endpoints

**POST /analyze-claim**

- Analyzes claim text using NLP
- Request body:
  ```json
  {
    "claim_id": "CLM-001",
    "text": "Patient diagnosed with diabetes...",
    "analysis_tier": "pro"
  }
  ```
- Response includes entities, confidence scores, and recommendations

**GET /health**

- Health check endpoint

### Lambda Functions

See individual README files in `backend/lambdas/` for detailed API specifications.

## Configuration

Environment variables and secrets:

- AWS region, credentials
- OpenAI API key
- S3 bucket names
- Cognito pool configuration

See `.env.example` (if present) for complete configuration details.

## Testing

```bash
# Backend tests
cd backend
python -m pytest tests/

# Frontend tests
cd frontend
npm test

# Test data generation
python test-samples/generate_test_claims.py
python test-samples/create_test_pdfs.py
```

## Development

### Adding a New Lambda Function

1. Create directory in `backend/lambdas/`
2. Add `app.py` and `requirements.txt`
3. Update SAM/CloudFormation template
4. Deploy and test

### Updating Models

- GPU service model: Update `MODEL_NAME` in `backend/gpu-service/app.py`
- Rebuild Docker image for GPU service
- Re-deploy container/ECS task

## Deployment

Deployment varies by component:

- **GPU Service**: Docker container → ECS/EC2
- **Lambda Functions**: Deploy via AWS Console, SAM, or Terraform
- **Frontend**: S3 + CloudFront or similar CDN

See `infrastructure/` directory for detailed deployment configurations.

## Monitoring

- **GPU Service**: FastAPI docs at `/docs`, metrics published to CloudWatch
- **Lambda**: CloudWatch Logs, X-Ray tracing
- **Frontend**: Browser console, network tab in DevTools

## Contributing

1. Create a feature branch
2. Make changes and test locally
3. Submit pull request with description

## License

[Add license information]

## Support

For issues or questions, please [add contact information or support channels].
