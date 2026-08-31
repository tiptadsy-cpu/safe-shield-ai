from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
import os

app = FastAPI(title="Safe Shield AI API")

# Initialize Presidio PII Engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

def sanitize_input(text: str) -> str:
    results = analyzer.analyze(
        text=text, 
        entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "IP_ADDRESS", "LOCATION"], 
        language='en'
    )
    return anonymizer.anonymize(text=text, analyzer_results=results).text

class TriageRequest(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"status": "Safe Shield API Active"}

@app.post("/api/v1/triage")
def run_triage(data: TriageRequest, x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API Key missing")
        
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    llm = ChatAnthropic(model="claude-sonnet-4-6", api_key=anthropic_key, temperature=0)
    
    clean_text = sanitize_input(data.message)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a domestic abuse triage engine aligning responses with the UK DASH framework. 
        Analyze the anonymized payload and respond ONLY with structured text containing:
        - ASSESSED RISK LEVEL: (Low, Medium, High, or Critical)
        - KEY DASH RISK INDICATORS FLAGGED: (List key factors)
        - SAFEST OUTREACH RECOMMENDATION: (Recommended contact timing/channel)
        - MORNING BRIEFING SUMMARY FOR CASEWORKER: (2-sentence summary)"""),
        ("human", "{text}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"text": clean_text})
    
    return {
        "status": "success",
        "anonymized_payload": clean_text,
        "briefing": response.content
    }
