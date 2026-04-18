#!/bin/bash

source venv/bin/activate
uvicorn neron_llm.main:app --host 0.0.0.0 --port 8765
