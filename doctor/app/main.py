# app/main.py
# FastAPI 

from fastapi import FastAPI
from app.runner import run_full_diagnosis

app = FastAPI(title="Neron Doctor Agent")

@app.post("/diagnose")
def diagnose():
    result = run_full_diagnosis()
    return result
