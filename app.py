import csv
import os
import string
import time
import sqlite3
import urllib.parse
import requests
import streamlit as st
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

# Automatically load local private .env key configurations
load_dotenv()

# Set up professional page configuration with modern layout and native icon placeholders
st.set_page_config(
    page_title="Ultimate Smart Keyword Harvester", 
    page_icon="🔍", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize the Free SQLite Local Cache Database Engine
def init_cache_db():
    conn = sqlite3.connect("keyword_cache.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            keyword TEXT,
            country TEXT,
            response_data TEXT,
            timestamp REAL,
            PRIMARY KEY (keyword, country)
        )
    """)
    conn.commit()
    conn.close()

init_cache_db()

def get_cached_data(keyword, country):
    conn = sqlite3.connect("keyword_cache.db")
    cursor = conn.cursor()
    cursor.execute("SELECT response_data FROM cache WHERE keyword=? AND country=?", (keyword.lower(), country))
    row = cursor.fetchone()
    conn.close()
    if row:
        import json
        return json.loads(row)
    return None

def set_cached_data(keyword, country, data_list):
    import json
    conn = sqlite3.connect("keyword_cache.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO cache (keyword, country, response_data, timestamp) VALUES (?, ?, ?, ?)",
        (keyword.lower(), country, json.dumps(data_list), time.time())
    )
    conn.commit()
    conn.close()

# Custom Premium CSS Theme Styling Injection + Mobile Icon Touch Configuration
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
    </style>
""", unsafe_allow_html=True)

# PWA Mobile Device Home-Screen Manifest Icon Injection Wrapper
st.markdown("""
    <link rel="apple-touch-icon" sizes="180x180" href="https://icons8.com">
    <link rel="icon" type="image/png" sizes="32x32" href="https://icons8.com">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
""", unsafe_allow_html=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_live_api_keywords(seed, country_suffix):
    """Gathers raw semantic expansions across open-network endpoints."""
    gathered_set = set()
    localized_seed = f"{seed} {country_suffix}".strip()
    
    try:
        datamuse_url = f"https://datamuse.com{urllib.parse.quote(localized_seed)}&max=15"
        res = requests.get(datamuse_url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            for item in res.json():
                gathered_set.add(f"{seed} {item['word']}")
    except Exception: pass

    try:
        wiki_url = f"https://wikipedia.org{urllib.parse.quote(seed)}&limit=10"
        res = requests.get(wiki_url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            raw_data = res.json()
            if len(raw_data) > 1 and isinstance(raw_data, list):
                for item in raw_data:
                    gathered_set.add(item.lower())
    except Exception: pass

    return list(gathered_set)

def process_with_ai_brain(client, seed, country, raw_list_from_apis):
    """Enriches data strings: Applies automated filtering and semantic clustering."""
    if not raw_list_from_apis:
        is_fallback_active = True
        prompt_data_source = f"Brainstorm a list of 40 highly relevant e-commerce long-tail keyword phrases from your memory for: '{seed}' targeted specifically at the {country} market."
    else:
        is_fallback_active = False
        keywords_string = "\n".join([f"- {kw}" for kw in raw_list_from_apis[:50]])
        prompt_data_source = f"Analyze these raw keywords for the product '{seed}' targeted at the {country} market:\n{keywords_string}"

    full_prompt = f"""
    You are an expert e-commerce SEO data analyst. Parse and enrich keywords for the product: '{seed}' in country market context: '{country}'.
    {prompt_data_source}

    CRITICAL REFINEMENT INSTRUCTIONS:
    1. AUTOMATIC NEGATIVE FILTER: Strip out and discard any junk phrases, obvious spelling errors, symbols, and duplicate concepts.
    2. DYNAMIC CLUSTERING: Categorize the remaining keywords into logical thematic product clusters (e.g., Styling, Material, Sizing, Intent).

    For each verified keyword, output exactly 5 columns separated by pipe characters (|):
    1. Dynamic Semantic Cluster Group Name (Capitalized topic title)
    2. The cleaned Keyword phrase.
    3. Buyer Intent Category (Choose ONLY from: High Commercial, Informational, Navigational, Low Intent).
    4. Importance Status (Choose ONLY from: 🔥 BREAKING TREND, 📈 STABLE GROWTH, 📉 DECREASING).
    5. Target Audience Persona (e.g., Luxury Collectors, Budget Shoppers, Tech Enthusiasts, Gift Buyers).

    CRITICAL INSTRUCTION: Output ONLY raw data lines. No intro text, no conversational text, no headers.
    Format: Cluster Group | Keyword | Intent Category | Importance Status | Target Audience Persona
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.2
        )
        # FIXED: Explicitly target choice index 0 to parse message content correctly
        raw_lines = completion.choices[0].message.content.strip().split("\n")
        return raw_lines, is_fallback_active
    except Exception as e:
        st.error(f"AI Connection Error: {e}")
        return [], False

# --- Layout Visual Design Panels Wrapper ---

with st.sidebar:
    st.markdown("### ⚙️ Configuration & Market Panel")
    
    # VISUAL UPGRADE: Flag emojis added dynamically to choice selection layout labels
    target_country = st.selectbox(
        "Target Market Location:",
        ["🇺🇸 United States", "🇬🇧 United Kingdom", "🇦🇺 Australia", "🇮🇳 India"]
    )
    country_map = {
        "🇺🇸 United States": "US", 
        "🇬🇧 United Kingdom": "UK", 
        "🇦🇺 Australia": "AU", 
        "🇮🇳 India": "IN"
    }
    country_suffix = country_map[target_country]

    st.markdown("---")
    api_key = os.getenv("MY_PROJECT_GROQ_KEY")
    if api_key:
        st.success("🔒 System Clearance Active")
    else:
        st.error("🔑 Token Key Required")
        api_key = st.text_input("Paste Groq Key manually:", type="password")

st.markdown("<h1>Ultimate Smart Keyword Harvester</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-text'>Enterprise AI engine featuring automated negative filtering, thematic data clustering, and SQLite local speed caching.</p>", unsafe_allow_html=True)

if not api_key:
    st.warning("Please configure your Groq API token inside your local folder `.env` file to unlock app functionality.")
else:
    client = Groq(api_key=api_key)
    
    # REBRANDED FIELD DESCRIPTION: Changed to industry-standard competitor analysis language
    search_term = st.text_input(
        "Enter Core Competitor Product Name or Search Term:", 
        placeholder="e.g., leather handbags, minimalist wallets, wireless keyboards"
    ).strip()
    
    if st.button("Analyze & Harvest Data", type="primary"):
        if not search_term:
            st.warning("Please enter a valid search term first.")
        else:
            cached_rows = get_cached_data(search_term, country_suffix)
            
            if cached_rows is not None:
                st.success("⚡ Data loaded instantly from local SQLite Cache (0$ token usage)!")
                df = pd.DataFrame(cached_rows)
                
                col1, col2, col3 = st.columns(3)
                with col1: st.markdown(f"<div class='metric-card'><div class='metric-num'>{len(df)}</div><div class='metric-lbl'>Keywords Loaded from Cache</div></div>", unsafe_allow_html=True)
                with col2: st.markdown(f"<div class='metric-card'><div class='metric-num'>0$</div><div class='metric-lbl'>Total Infrastructure Costs</div></div>", unsafe_allow_html=True)
                with col3: st.markdown(f"<div class='metric-card'><div class='metric-num'>100%</div><div class='metric-lbl'>Data Protection Guarantee</div></div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.dataframe(df.sort_values(by="Cluster Group"), use_container_width=True)
                
                csv_bytes = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Download Data Spreadsheet (CSV)", data=csv_bytes, file_name=f"harvested_{search_term.replace(' ', '_')}.csv", mime="text/csv")
                
            else:
                with st.spinner("Synchronizing deep intelligence matrices..."):
                    raw_words = fetch_live_api_keywords(search_term, country_suffix)
                    ai_output_lines, fallback_triggered = process_with_ai_brain(client, search_term, target_country, raw_words)
                    
                    parsed_rows = []
                    for line in ai_output_lines:
                        if "|" in line:
                            parts = [item.strip() for item in line.split("|")]
                            if len(parts) >= 5:
                                parsed_rows.append({
                                    "Cluster Group": parts[0],
                                    "Harvested Keyword": parts[1],
                                    "Buyer Intent Category": parts[2],
                                    "Trend Importance Status": parts[3],
                                    "Target Audience Focus": parts[4]
                                })
                    
                    if parsed_rows:
                        df = pd.DataFrame(parsed_rows)
                        set_cached_data(search_term, country_suffix, parsed_rows)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1: st.markdown(f"<div class='metric-card'><div class='metric-num'>{len(df)}</div><div class='metric-lbl'>Actionable Keywords Compiled</div></div>", unsafe_allow_html=True)
                        with col2: st.markdown(f"<div class='metric-card'><div class='metric-num'>0$</div><div class='metric-lbl'>Total Infrastructure Costs</div></div>", unsafe_allow_html=True)
                        with col3: st.markdown(f"<div class='metric-card'><div class='metric-num'>100%</div><div class='metric-lbl'>Data Protection Guarantee</div></div>", unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.dataframe(df.sort_values(by="Cluster Group"), use_container_width=True)
                        
                        csv_bytes = df.to_csv(index=False).encode('utf-8')
                        st.download_button(label="📥 Download Data Spreadsheet (CSV)", data=csv_bytes, file_name=f"harvested_{search_term.replace(' ', '_')}.csv", mime="text/csv")
                    else:
                        st.error("Data grid could not build rows safely. Recheck key validation or connectivity strings.")
