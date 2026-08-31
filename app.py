from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from presidio_analyzer import AnalyzerEngine, NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
import os
import smtplib
from email.message import EmailMessage

app = FastAPI(title="Safe Shield AI API")

# Explicitly configure Presidio to use the SMALL spacy model to prevent memory crashes
configuration = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}
provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine = provider.create_engine()

analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
anonymizer = AnonymizerEngine()

def sanitize_input(text: str) -> str:
    results = analyzer.analyze(
        text=text, 
        entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "IP_ADDRESS", "LOCATION"], 
        language='en'
    )
    return anonymizer.anonymize(text=text, analyzer_results=results).text

def send_instant_notification(briefing_text: str):
    smtp_server = "smtp.gmail.com"
    smtp_port = 465
    sender_email = os.getenv("ALERT_SENDER_EMAIL")
    sender_password = os.getenv("ALERT_SENDER_PASSWORD")
    recipient_email = os.getenv("ALERT_RECIPIENT_EMAIL")

    if not sender_email or not sender_password or not recipient_email:
        return

    msg = EmailMessage()
    msg.set_content(f"New client triage submission received. Instant Briefing:\n\n{briefing_text}")
    msg["Subject"] = "🚨 URGENT: New Safe Shield Triage Briefing"
    msg["From"] = sender_email
    msg["To"] = recipient_email

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email alert: {e}")

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
    if not anthropic_key:
        raise HTTPException(status_code=500, detail="Anthropic API Key not configured on server")
        
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", api_key=anthropic_key, temperature=0)
    
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
    
    send_instant_notification(response.content)
    
    return {
        "status": "success",
        "anonymized_payload": clean_text,
        "briefing": response.content
    }
