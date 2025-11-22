#!/bin/bash
# Start the FastAPI server

echo "Starting Company Intelligence API server..."
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
