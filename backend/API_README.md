# Company Intelligence API

A FastAPI-based backend service that generates company profiles, identifies competitors, and analyzes solutions using Google Search and Gemini AI.

## Features

- **Company Profile Generation**: Comprehensive analysis of a company including industry, business model, key clients, and market context
- **Competitor Analysis**: Automated identification and validation of direct and indirect competitors
- **Solutions Analysis**: Detailed breakdown of company offerings with features, benefits, use cases, and competitive intelligence
- **Web Search Grounding**: Uses Google Search via Gemini API for real-time market data
- **Token Tracking**: Monitors and logs Gemini API token usage
- **CORS Support**: Ready for cross-origin requests
- **Interactive API Documentation**: Auto-generated Swagger UI and ReDoc documentation

## Prerequisites

- Python 3.8+
- Gemini API key (set as `GEMINI_API_KEY` environment variable)
- Dependencies from `requirements.txt`

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

3. Make the run script executable:

```bash
chmod +x run_server.sh
```

## Running the Server

### Option 1: Using the shell script

```bash
./run_server.sh
```

### Option 2: Direct Python execution

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Manual start

```bash
python app.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Endpoints

### 1. Health Check

```
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "message": "API is running"
}
```

### 2. Generate Company Profile and Solutions

```
GET /profile_competitors_solution?domain=stripe.com&model=gemini-2.5-pro
```

**Parameters:**

- `domain` (required): Company domain (e.g., `stripe.com`, `https://example.com`)
- `model` (optional): Gemini model to use (default: `gemini-2.5-pro`)

**Response:**

```json
{
  "domain": "stripe.com",
  "company_profile": {
    "name": "Stripe",
    "core_business": {
      "industry": "Financial Technology",
      "sub_industries": ["Payment Processing", "API Platform"],
      "company_overview": "...",
      "company_size": "...",
      "business_model": "...",
      "current_stage": "..."
    },
    "key_clients": [
      {
        "client_name": "...",
        "client_domain": "...",
        "client_case_study": "...",
        "inferred_region": "...",
        "explanation": "..."
      }
    ],
    "competitors": [
      {
        "company_name": "...",
        "website": "...",
        "location": "...",
        "type": "direct"
      }
    ],
    "market_context": {
      "addressed_geography": [],
      "competitive_advantages": [],
      "industry_trends": [],
      "regulatory_environment": [],
      "current_challenges": []
    },
    "technical_foundation": {
      "technical_sophistication": "...",
      "integration_capabilities": [],
      "security_certifications": [],
      "compliance_requirements": []
    },
    "enhanced_confidence": {
      "core_business": 0.8,
      "key_clients": 0.75,
      "market_context": 0.85,
      "technical_foundation": 0.8
    },
    "research_summary": {
      "searches_conducted": 15,
      "fields_enhanced": [],
      "high_confidence_discoveries": [],
      "remaining_gaps": [],
      "source_quality_breakdown": {},
      "key_clients_discovered": 5,
      "verified_domains": 4,
      "case_studies_found": 3
    }
  },
  "solutions_profile": [
    {
      "Title": "Stripe Payments",
      "Description": "...",
      "Features": [],
      "Benefits": [],
      "Use_Cases": [],
      "Target_Industries": [],
      "Target_Roles": [],
      "Pricing_Model": "...",
      "Pricing_Value": "...",
      "customer_intelligence": {
        "positive_feedback": [],
        "negative_feedback": [],
        "review_themes": [],
        "satisfaction_indicators": [],
        "customer_success_stories": [],
        "typical_customer_profile": [],
        "customer_retention_signals": []
      },
      "competitive_intelligence": {
        "vs_competitors": [],
        "unique_differentiators": [],
        "competitive_weaknesses": [],
        "market_positioning": [],
        "switching_triggers": [],
        "competitive_pricing": []
      },
      "market_intelligence": {
        "adoption_patterns": [],
        "buying_triggers": [],
        "decision_criteria": [],
        "budget_considerations": [],
        "expansion_usage": [],
        "churn_indicators": [],
        "roi_evidence": [],
        "market_trends_impact": []
      },
      "pain_point_intelligence": {
        "primary_pains_addressed": [],
        "pain_indicators": [],
        "pain_triggers": [],
        "consequence_evidence": [],
        "pain_evolution": []
      },
      "external_validation": {
        "website_claims_verified": [],
        "website_gaps_filled": [],
        "contradictions_found": [],
        "additional_insights": [],
        "source_quality_breakdown": {},
        "research_confidence": 0.85,
        "information_completeness": 0.88
      }
    }
  ],
  "analysis_metadata": {
    "input_tokens": 12500,
    "output_tokens": 8300,
    "thinking_tokens": 2100,
    "model_used": "gemini-2.5-pro",
    "company_name": "Stripe",
    "solutions_count": 5,
    "industry": "Financial Technology"
  }
}
```

**Error Response:**

```json
{
  "error": "Request failed",
  "detail": "Invalid domain format: invalid-domain"
}
```

## Example Usage

### Using cURL

```bash
curl "http://localhost:8000/profile_competitors_solution?domain=stripe.com"
```

### Using Python Requests

```python
import requests
import json

response = requests.get(
    "http://localhost:8000/profile_competitors_solution",
    params={
        "domain": "stripe.com",
        "model": "gemini-2.5-pro"
    }
)

data = response.json()
print(f"Company: {data['company_profile']['name']}")
print(f"Solutions: {len(data['solutions_profile'])}")
print(f"Token Usage: {data['analysis_metadata']}")
```

### Using JavaScript/Fetch

```javascript
const response = await fetch(
  "http://localhost:8000/profile_competitors_solution?domain=stripe.com"
);
const data = await response.json();
console.log(`Company: ${data.company_profile.name}`);
console.log(`Solutions: ${data.solutions_profile.length}`);
console.log(`Tokens: ${data.analysis_metadata.output_tokens}`);
```

## API Behavior

### Request Processing

1. **Domain Validation**: Cleans and validates the input domain
2. **Company Profile Generation**: Uses Gemini 2.5 Pro with Google Search to analyze the company
3. **Solutions Analysis**: Analyzes solutions using the company profile as context
4. **Response Compilation**: Returns both profiles with metadata

### Performance Considerations

- **Thinking Budget**: 2000 tokens for company profile, 3000 for solutions
- **Temperature**: 0.7 for balanced creativity and accuracy
- **Model**: Uses `gemini-2.5-pro` by default for better results

### Error Handling

- Returns 400 for invalid domain formats
- Returns 500 for API or processing errors
- All errors include descriptive messages

## Logging

The API logs all activities to the console with the following format:

```
2024-11-22 10:30:45,123 - api_clients.gemini_adapter - INFO - Initialized Gemini API with model: gemini-2.5-pro
```

## Environment Variables

- `GEMINI_API_KEY` (required): Your Google Gemini API key
- `PYTHONUNBUFFERED` (optional): Set to `1` for real-time logging output

## Architecture

```
┌─────────────────────────────────────────┐
│   FastAPI Application (app.py)          │
├─────────────────────────────────────────┤
│  GET /profile_competitors_solution      │
│  ├─ Domain Validation                   │
│  ├─ Gemini API Initialization           │
│  ├─ Company Profile Generation          │
│  │  └─ Uses company_profile.md prompt   │
│  ├─ Solutions Analysis                  │
│  │  └─ Uses solutions_profile.md prompt │
│  └─ Response Compilation                │
└─────────────────────────────────────────┘
         │                │
         ▼                ▼
    ┌─────────────┬──────────────┐
    │  Gemini API │  Google      │
    │  (2.5 Pro)  │  Search      │
    └─────────────┴──────────────┘
```

## Troubleshooting

### Import errors for FastAPI

```
ImportError: No module named 'fastapi'
```

**Solution**: Install dependencies with `pip install -r requirements.txt`

### GEMINI_API_KEY not found

```
ValueError: GEMINI_API_KEY environment variable is not set
```

**Solution**: Set the environment variable: `export GEMINI_API_KEY="your-key"`

### Server won't start on port 8000

```
OSError: [Errno 48] Address already in use
```

**Solution**: Use a different port: `python -m uvicorn app:app --port 8001`

### Slow response times

- This is expected - the API is generating comprehensive analyses using multiple Google searches
- Typical analysis takes 60-120 seconds depending on company complexity
- Token usage can reach 10,000+ tokens per request

## Performance Metrics

Typical performance for a single domain analysis:

- **Company Profile**: 30-45 seconds
- **Solutions Analysis**: 45-75 seconds
- **Total Time**: 75-120 seconds
- **Input Tokens**: 8,000-15,000
- **Output Tokens**: 6,000-12,000
- **Thinking Tokens**: 2,000-3,000

## License

This project is part of the Competitive Intelligence Platform.
