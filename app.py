import streamlit as st
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# Initialize Presidio PII Engines (Runs locally)
@st.cache_resource
def load_presidio():
    return AnalyzerEngine(), AnonymizerEngine()

analyzer, anonymizer = load_presidio()

def sanitize_input(text):
    results = analyzer.analyze(
        text=text, 
        entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "IP_ADDRESS", "LOCATION"], 
        language='en'
    )
    anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results)
    return anonymized_result.text

# Page Config
st.set_page_config(page_title="Safe Shield AI", page_icon="🛡️", layout="wide")

# --- ADD CUSTOM CSS HERE ---
st.markdown("""
    <style>
    /* Main application background */
    .stApp {
        background-color: #f8f9fa;
    }
    /* Custom styling for headers */
    h1 {
        color: #1e3a8a;
        font-family: 'Helvetica Neue', sans-serif;
    }
    /* Clean border styling for feedback boxes */
    .stAlert {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)
# ---------------------------

st.title("🛡️ Safe Shield AI: Domestic Abuse Triage & Support Engine")

# Sidebar for API Key
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Enter Anthropic API Key (sk-ant-...)", type="password")

if not api_key:
    st.info("👈 Please enter your Anthropic API Key in the sidebar to start.")
else:
    llm = ChatAnthropic(
        model="claude-sonnet-4-6", 
        api_key=api_key, 
        temperature=0
    )
    
    tab1, tab2 = st.tabs(["Layer 1: 24/7 Client Triage (Off-Hours)", "Layer 2: Worker Shift Debrief"])

    # --- TAB 1: TRIAGE & DASH EVALUATION ---
    with tab1:
        st.subheader("Simulate Incoming Off-Hours Client Message")
        raw_input = st.text_area(
            "Client Message / Form Submission:",
            value="My name is Sarah Smith, living at 14 High Street, Wallasey. My ex-partner John showed up at my house unannounced last night and threatened me.",
            height=120
        )
        
        if st.button("Run Safe Triage & Scrub PII"):
            with st.spinner("Processing safely..."):
                # 1. Scrub PII locally
                clean_text = sanitize_input(raw_input)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.error("**1. Local Raw Input (Never Leaves Computer)**")
                    st.write(raw_input)
                with col2:
                    st.success("**2. Anonymized Payload (Sent to Claude)**")
                    st.write(clean_text)

                # 2. Call Claude API for DASH Triage
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
                
                st.markdown("---")
                st.subheader("3. Auto-Generated Morning Briefing for Staff")
                st.info(response.content)

    # --- TAB 2: WORKER DEBRIEF ---
    with tab2:
        st.subheader("Caseworker End-of-Shift Debrief & Reset")
        debrief_input = st.text_area(
            "How are you feeling after today's shift?",
            value="Handled 3 complex social services calls and a high-risk advocacy case today. Feeling physically drained and frustrated with the delays.",
            height=120
        )
        
        if st.button("Complete Shift Debrief"):
            with st.spinner("Analyzing debrief..."):
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are a vicarious trauma debrief copilot for frontline domestic abuse caseworkers.
                    Provide a warm, supportive, 3-sentence response that:
                    1. Validates their hard work and emotional weight.
                    2. Offers a 1-minute mental boundary transition exercise before they head home.
                    3. Gently flags a self-care reminder if fatigue or burnout markers are present."""),
                    ("human", "{text}")
                ])
                chain = prompt | llm
                response = chain.invoke({"text": debrief_input})
                st.success(response.content)
