#!/bin/bash
# Start Whisper and LLM services in parallel
python3 -m uvicorn whisper_service:app --host 0.0.0.0 --port 8001 &
python3 -m uvicorn llm_service:app --host 0.0.0.0 --port 8002 &
wait
