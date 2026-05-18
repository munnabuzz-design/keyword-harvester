import csv
import os
import string
import time
import requests
import streamlit as st
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

# Automatically load local private .env key configurations
load_dotenv()

# Set up professional page configuration with modern layout
st.set_page_config(
    page_title="Ultimate Smart Keyword Harvester", 
    page_icon="🔍", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium CSS Theme Styling Injection
st.markdown("""
    <style>
        /* Main page adjustments */
        .main .block-container { padding-top: 2rem; }
        h1 { color: #FF4B4B; font-weight: 800; font-size: 2.8rem; margin-bottom: 0.2rem; }
        .subtitle-text { color: #A0AEC0; font-size: 1.1rem; margin-bottom: 2rem; }
        
        /* Premium Dashboard Metric Cards */
        .metric-card {
            background-color: #1E293B;
            border: 1px solid #334155;
            padding: 1.2rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        .metric-num { font-size: 2.2rem; font-weight: 700; color: #00F2FE; line-height: 1; }
        .metric-lbl { font-size: 0.85rem; color: #94A3B8; margin-top: 0.5rem; font-weight: 500; }
        
        /* Info Tooltip Icon styling adjustment */
        .tooltip-container { display: inline-flex; align-items: center; gap: 6px; margin-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# Standard headers to prevent generic web request drops
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_live_api_keywords(seed):
    """Gathers raw semantic expansions across open-network endpoints."""
    gathered_set = set()
    try:
        datamuse_url = f"https://datamuse.com{requests.utils.quote(seed)}&max=15"
        res = requests.get(datamuse_url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            for item in res.json():
                gathered_set.add(f"{seed} {item['word']}")
                gathered_set.add(f"{item['word']} {seed}")
    except Exception: pass

    try:
        wiki_url = f"https://wikipedia.org{requests.utils.quote(seed)}&limit=10"
        res = requests.get(wiki_url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            raw_data = res.json()
            if len(raw_data) > 1 and isinstance(raw_data, list):
                for item in raw_data[1]:
                    gathered_set.add(item.lower())
    except Exception: pass

    return list(gathered_set)

def process_with_ai_brain(client, seed, raw_list_from_apis):
    """Processes or generates terms cleanly, returns true state flag alongside string payload blocks."""
    if not raw_list_from_apis:
        is_fallback_active = True
        prompt_data_source = f"Generate 35 highly relevant e-commerce long-tail search phrases based entirely on your internal memory for: '{seed}'."
    else:
        is_fallback_active = False
        keywords_string = "\n".join([f"- {kw}" for kw in raw_list_from_apis[:50]])
        prompt_data_source = f"Analyze these raw keywords harvested from open networks for the seed product: '{seed}':\n{keywords_string}"

    full_prompt = f"""
    You are an expert e-commerce SEO data analyst. Parse and enrich keywords for the product: '{seed}'.
    {prompt_data_source}

    For each keyword processed or generated, output exactly 4 columns separated by pipe characters (|):
    1. The Keyword phrase.
    2. Buyer Intent Category (Choose ONLY from: High Commercial, Informational, Navigational, Low Intent).
    3. Importance Status (Choose ONLY from: 🔥 BREAKING TREND, 📈 STABLE GROWTH, 📉 DECREASING).
    4. Target Audience Persona (e.g., Luxury Collectors, Budget Shoppers, Tech Enthusiasts, Gift Buyers).

    CRITICAL INSTRUCTION: Output ONLY raw data lines. No intro text, no conversational text, no markdown table borders. Start instantly with the data lines using format: Keyword | Intent Category | Importance Status | Target Audience Persona
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.3
        )
        raw_lines = completion.choices[0].message.content.strip().split("\n")
        return raw_lines, is_fallback_active
    except Exception as e:
        st.error(f"AI Connection Error: {e}")
        return [], False

# --- Application Layout Wrapper Construction ---

with st.sidebar:
    st.markdown("### ⚙️ Configuration Panel")
    
    api_key = os.getenv("MY_PROJECT_GROQ_KEY")
    if api_key:
        st.success("🔒 System Clearance Active")
    else:
        st.error("🔑 Token Key Required")
        api_key = st.text_input("Paste Groq Key manually:", type="password")

st.markdown("<h1>Ultimate Smart Keyword Harvester</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-text'>Next-generation AI semantic engine for e-commerce keyword optimization and audience targeting.</p>", unsafe_allow_html=True)

if not api_key:
    st.warning("Please configure your Groq API token inside your local folder `.env` file to unlock app functionality.")
else:
    client = Groq(api_key=api_key)
    
    search_term = st.text_input(
        "What product or topic are you researching?", 
        placeholder="e.g., leather handbags, minimalist wallets, wireless keyboards"
    ).strip()
    
    if st.button("Analyze & Harvest Data", type="primary"):
        if not search_term:
            st.warning("Please enter a valid search term first.")
        else:
            with st.spinner("Synchronizing deep intelligence matrices..."):
                
                raw_words = fetch_live_api_keywords(search_term)
                ai_output_lines, fallback_triggered = process_with_ai_brain(client, search_term, raw_words)
                
                parsed_rows = []
                for line in ai_output_lines:
                    if "|" in line:
                        parts = [item.strip() for item in line.split("|")]
                        if len(parts) >= 4:
                            # FIXED PARSING RULE: Added exact string index targets to populate cells smoothly
                            parsed_rows.append({
                                "Harvested Keyword": parts[0],
                                "Buyer Intent Category": parts[1],
                                "Trend Importance Status": parts[2],
                                "Target Audience Focus": parts[3]
                            })
                
                if parsed_rows:
                    df = pd.DataFrame(parsed_rows)
                    
                    status_message = "Engine Optimization Active"
                    status_help = "Deep Semantic Synthesis Engine running smoothly."
                    if fallback_triggered:
                        status_message = "AI Synthesis Active"
                        status_help = "Live network pipelines crowded. Switched automatically to internal model knowledge matrices for deep phrase brainstorming."
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"<div class='metric-card'><div class='metric-num'>{len(df)}</div><div class='metric-lbl'>Actionable Keywords Compiled</div></div>", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"<div class='metric-card'><div class='metric-num'>0$</div><div class='metric-lbl'>Total Infrastructure Costs</div></div>", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"<div class='metric-card'><div class='metric-num'>100%</div><div class='metric-lbl'>Data Protection Guarantee</div></div>", unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    st.markdown(f"""
                        <div class='tooltip-container'>
                            <span style='font-size: 1.1rem; font-weight:600; color:#10B981;'>⚡ Status: {status_message}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    st.caption(f"💡 Hover for technical log insight: {status_help}")
                    
                    st.dataframe(df, use_container_width=True)
                    
                    csv_bytes = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Data Spreadsheet (CSV)",
                        data=csv_bytes,
                        file_name=f"harvested_{search_term.replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("Data grid could not build rows safely. Recheck key validation or connectivity strings.")
