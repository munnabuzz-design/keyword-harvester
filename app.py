import csv
import os
import string
import time
import sqlite3
import urllib.parse
import requests
import json
import streamlit as st
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from postgrest import SyncPostgrestClient

# Load local environment configurations
load_dotenv()

st.set_page_config(
    page_title="Ultimate Smart Keyword Harvester & Magnet AI", 
    page_icon="🧲", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize the Free SQLite Cache Database
def init_local_db():
    conn = sqlite3.connect("keyword_cache.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            keyword TEXT, country TEXT, mode TEXT, response_data TEXT, timestamp REAL,
            PRIMARY KEY (keyword, country, mode)
        )
    """)
    cursor.execute("PRAGMA table_info(cache)")
    columns = [col[1] for col in cursor.fetchall()]
    if "mode" not in columns:
        try:
            cursor.execute("ALTER TABLE cache ADD COLUMN mode TEXT DEFAULT 'harvester'")
        except Exception: pass
    conn.commit()
    conn.close()

init_local_db()

# Initialize Pure-Web Supabase Connection using the light driver setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        supabase_client = SyncPostgrestClient(f"{SUPABASE_URL}/rest/v1", headers=headers)
    except Exception: pass

def get_cached_data(keyword, country, mode):
    try:
        conn = sqlite3.connect("keyword_cache.db")
        cursor = conn.cursor()
        cursor.execute("SELECT response_data FROM cache WHERE keyword=? AND country=? AND mode=?", (keyword.lower(), country, mode))
        row = cursor.fetchone()
        conn.close()
        if row: return json.loads(row)
    except Exception: pass
    
    if supabase_client:
        try:
            res = supabase_client.from_("keyword_cache").select("response_data").eq("keyword", keyword.lower()).eq("country", country).eq("mode", mode).execute()
            if res.data:
                cloud_data = res.data[0]["response_data"]
                set_local_cache(keyword, country, mode, cloud_data)
                return cloud_data
        except Exception: pass
    return None

def set_local_cache(keyword, country, mode, data_list):
    try:
        conn = sqlite3.connect("keyword_cache.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cache (keyword, country, mode, response_data, timestamp) VALUES (?, ?, ?, ?, ?)",
            (keyword.lower(), country, mode, json.dumps(data_list), time.time())
        )
        conn.commit()
        conn.close()
    except Exception: pass

def set_cached_data(keyword, country, mode, data_list):
    set_local_cache(keyword, country, mode, data_list)
    if supabase_client:
        try:
            supabase_client.from_("keyword_cache").upsert({
                "keyword": keyword.lower(), "country": country, "mode": mode, "response_data": data_list
            }).execute()
        except Exception: pass

# Styling
st.markdown("""
    <style>
        .main .block-container { padding-top: 2rem; }
        h1 { color: #FF4B4B; font-weight: 800; font-size: 2.8rem; margin-bottom: 0.2rem; }
        .subtitle-text { color: #A0AEC0; font-size: 1.1rem; margin-bottom: 2rem; }
        .metric-card {
            background-color: #1E293B; border: 1px solid #334155; padding: 1.2rem; border-radius: 12px; text-align: center;
        }
        .metric-num { font-size: 2.2rem; font-weight: 700; color: #00F2FE; line-height: 1; }
        .metric-lbl { font-size: 0.85rem; color: #94A3B8; margin-top: 0.5rem; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_live_api_keywords(seed, country_suffix):
    gathered_set = set()
    localized_seed = f"{seed} {country_suffix}".strip()
    try:
        res = requests.get(f"https://datamuse.com{urllib.parse.quote(localized_seed)}&max=15", headers=HEADERS, timeout=4)
        if res.status_code == 200:
            for item in res.json(): gathered_set.add(f"{seed} {item['word']}")
    except Exception: pass
    try:
        res = requests.get(f"https://wikipedia.org{urllib.parse.quote(seed)}&limit=10", headers=HEADERS, timeout=4)
        if res.status_code == 200:
            raw_data = res.json()
            if len(raw_data) > 1 and isinstance(raw_data, list):
                for item in raw_data: gathered_set.add(item.lower())
    except Exception: pass
    return list(gathered_set)

def run_magnet_intelligence_matrix(client, seed, country):
    """Simulates an advanced Magnet algorithm to discover search metrics and density profiles."""
    prompt = f"""
    You are an expert Amazon and E-commerce SEO engineer simulating an advanced keyword discovery tool.
    Generate an advanced keyword research matrix based on the root phrase: '{seed}' for the market context: '{country}'.
    
    Examine your internal historical memory and provide between 30 and 50 highly converting, long-tail search terms related to this root phrase.
    For each keyword, you must calculate and output exactly 6 columns separated by pipe characters (|):
    1. Keyword phrase
    2. Estimated Monthly Search Volume (Realistic predicted integer number e.g. 4500, 120, 24100)
    3. Magnet IQ Score (Higher score means high volume but low competition - integer between 100 and 9000)
    4. Competitor Title Density (How many page-one products use this keyword in their title? Integer between 0 and 40)
    5. Match Type (Choose only from: Organic, Sponsored, Smart Complete)
    6. Primary Intent Profile (Choose only from: High Purchase, Research, Comparison)
    
    CRITICAL INSTRUCTION: Return ONLY raw rows. No intro remarks, no headers, no conversational text.
    Format: Keyword | Search Volume | Magnet IQ Score | Title Density | Match Type | Intent Profile
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.2
        )
        # FIXED: Explicitly target choices[0] array index layer
        raw_ai_text = completion.choices[0].message.content.strip()
        return raw_ai_text.split("\n")
    except Exception as e:
        st.error(f"Magnet AI System Failure: {e}")
        return []

def run_harvester_intelligence_matrix(client, seed, country, raw_list_from_apis):
    if not raw_list_from_apis:
        prompt_data_source = f"Brainstorm a list of 40 highly relevant e-commerce long-tail keyword phrases from your memory for: '{seed}' targeted specifically at the {country} market."
    else:
        keywords_string = "\n".join([f"- {kw}" for kw in raw_list_from_apis[:50]])
        prompt_data_source = f"Analyze these raw keywords for the product '{seed}' targeted at the {country} market:\n{keywords_string}"

    prompt = f"""
    You are an expert e-commerce SEO data analyst. Parse and enrich keywords for the product: '{seed}' in country market: '{country}'.
    {prompt_data_source}
    Strip out junk words and group into thematic clusters.
    
    Output exactly 5 columns separated by pipe characters (|):
    Cluster Group | Keyword | Intent Category | Importance Status | Target Audience Persona
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.2
        )
        # FIXED: Explicitly target choices[0] array index layer
        raw_ai_text = completion.choices[0].message.content.strip()
        return raw_ai_text.split("\n")
    except Exception as e:
        st.error(f"AI Harvester Connection Error: {e}")
        return []

# --- Graphical Dashboard Assembly Wrapper ---

with st.sidebar:
    st.markdown("### ⚙️ Command Center Control Panel")
    app_mode = st.radio("Select Active Tool Module:", ["🔍 Smart Keyword Harvester", "🧲 Magnet AI"])
    target_country = st.selectbox("Target Market Location:", ["🇺🇸 United States", "🇬🇧 United Kingdom", "🇦🇺 Australia", "🇮🇳 India"])
    country_map = {"🇺🇸 United States": "US", "🇬🇧 United Kingdom": "UK", "🇦🇺 Australia": "AU", "🇮🇳 India": "IN"}
    country_suffix = country_map[target_country]

    st.markdown("---")
    api_key = os.getenv("MY_PROJECT_GROQ_KEY")
    if api_key: st.success("🔒 System Clearance Active")
    else: api_key = st.text_input("Paste Groq Key manually:", type="password")

st.markdown(f"<h1>Ultimate Smart Keyword Harvester & Magnet AI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-text'>Next-generation e-commerce semantic matrix platform engineered with dual-layered caching infrastructure.</p>", unsafe_allow_html=True)

if not api_key:
    st.warning("Please configure your Groq token variable to unlock system access framework panels.")
else:
    client = Groq(api_key=api_key)
    
    if app_mode == "🔍 Smart Keyword Harvester":
        search_term = st.text_input("Enter Core Product Search Term or Competitor Keyword:", placeholder="e.g., leather handbags, minimalist wallets")
        if st.button("Harvest Clustered Keywords", type="primary"):
            if not search_term: st.warning("Please fill in a valid product input string first.")
            else:
                cached_data = get_cached_data(search_term, country_suffix, "harvester")
                if cached_data:
                    st.success("⚡ Data loaded instantly from Layered Cache System ($0 token usage)!")
                    df = pd.DataFrame(cached_data)
                    st.dataframe(df.sort_values(by="Cluster Group"), use_container_width=True)
                else:
                    with st.spinner("Compiling autocomplete matrices and running AI sorting nodes..."):
                        raw_words = fetch_live_api_keywords(search_term, country_suffix)
                        ai_lines = run_harvester_intelligence_matrix(client, search_term, target_country, raw_words)
                        parsed_rows = []
                        for line in ai_lines:
                            if "|" in line:
                                parts = [item.strip() for item in line.split("|")]
                                if len(parts) >= 5:
                                    parsed_rows.append({"Cluster Group": parts[0], "Harvested Keyword": parts[1], "Buyer Intent Category": parts[2], "Trend Importance Status": parts[3], "Target Audience Focus": parts[4]})
                        if parsed_rows:
                            df = pd.DataFrame(parsed_rows)
                            set_cached_data(search_term, country_suffix, "harvester", parsed_rows)
                            st.dataframe(df.sort_values(by="Cluster Group"), use_container_width=True)
                        else: st.error("Failed to extract data streams safely.")
                        
    elif app_mode == "🧲 Magnet AI":
        search_term = st.text_input("Enter Root Keyword to Pull Advanced Market Metrics:", placeholder="e.g., wallet, mechanical keyboard, backpack")
        if st.button("Run Magnet Research", type="primary"):
            if not search_term: st.warning("Please fill in a valid root phrase string first.")
            else:
                cached_data = get_cached_data(search_term, country_suffix, "magnet")
                if cached_data:
                    st.success("⚡ Metrics retrieved from permanent cloud cache database storage layers!")
                    df = pd.DataFrame(cached_data)
                    st.dataframe(df.sort_values(by="Search Volume", ascending=False), use_container_width=True)
                else:
                    with st.spinner("Extracting search volume tiers, IQ metrics, and competitor density metrics..."):
                        ai_lines = run_magnet_intelligence_matrix(client, search_term, target_country)
                        parsed_rows = []
                        for line in ai_lines:
                            if "|" in line:
                                parts = [item.strip() for item in line.split("|")]
                                if len(parts) >= 6:
                                    try: vol = int(parts[1].replace(",", ""))
                                    except: vol = 0
                                    try: iq = int(parts[2].replace(",", ""))
                                    except: iq = 0
                                    try: dens = int(parts[3].replace(",", ""))
                                    except: dens = 0
                                    parsed_rows.append({"Keyword": parts[0], "Search Volume": vol, "Magnet IQ Score": iq, "Title Density": dens, "Match Type": parts[4], "Intent Profile": parts[5]})
                        if parsed_rows:
                            df = pd.DataFrame(parsed_rows)
                            set_cached_data(search_term, country_suffix, "magnet", parsed_rows)
                            
                            col1, col2, col3 = st.columns(3)
                            with col1: st.markdown(f"<div class='metric-card'><div class='metric-num'>{len(df)}</div><div class='metric-lbl'>Magnet Keywords Found</div></div>", unsafe_allow_html=True)
                            with col2: st.markdown(f"<div class='metric-card'><div class='metric-num'>{int(df['Search Volume'].mean())}</div><div class='metric-lbl'>Average Search Volume</div></div>", unsafe_allow_html=True)
                            with col3: st.markdown(f"<div class='metric-card'><div class='metric-num'>{int(df['Magnet IQ Score'].max())}</div><div class='metric-lbl'>Top Opportunity IQ Score</div></div>", unsafe_allow_html=True)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.dataframe(df.sort_values(by="Search Volume", ascending=False), use_container_width=True)
                            
                            csv_bytes = df.to_csv(index=False).encode('utf-8')
                            st.download_button(label="📥 Download Magnet Report (CSV)", data=csv_bytes, file_name=f"magnet_{search_term.replace(' ', '_')}.csv", mime="text/csv")
                        else: st.error("Failed to build metrics data matrix grid.")
