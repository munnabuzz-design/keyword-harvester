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
    page_title="Command Center Enterprise SEO Suite", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PREMIUM SAAS SECURITY CLEARANCE GATEWAY ---
def check_user_credentials():
    """Renders a secure storefront credential barrier gate layout screen."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown("<h2 style='text-align: center; color: #FF4B4B;'>🔒 Enterprise SEO Suite Gateway</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("Login Form"):
                username = st.text_input("SaaS Username Profile Name:")
                password = st.text_input("Security Access Password Token:", type="password")
                submit = st.form_submit_button("Authenticate System Access", type="primary")
                
                # Hardcoded secure sandbox demo credential tokens
                if submit:
                    if username == "admin" and password == "saas123":
                        st.session_state["authenticated"] = True
                        st.success("Access Granted! Loading Command Modules...")
                        st.rerun()
                    else:
                        st.error("Invalid structural credentials or revoked access clearance.")
            st.stop() # Freeze compiler loop layout processing until validated

check_user_credentials()

# Initialize Database Structures
def init_local_db():
    conn = sqlite3.connect("keyword_cache.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            keyword TEXT, country TEXT, mode TEXT, response_data TEXT, timestamp REAL,
            PRIMARY KEY (keyword, country, mode)
        )
    """)
    conn.commit()
    conn.close()

init_local_db()

# Hook Cloud Databases
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
                cloud_data = res.data["response_data"]
                return cloud_data
        except Exception: pass
    return None

def set_cached_data(keyword, country, mode, data_list):
    try:
        conn = sqlite3.connect("keyword_cache.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO cache (keyword, country, mode, response_data, timestamp) VALUES (?, ?, ?, ?, ?)", (keyword.lower(), country, mode, json.dumps(data_list), time.time()))
        conn.commit()
        conn.close()
    except Exception: pass
    if supabase_client:
        try:
            supabase_client.from_("keyword_cache").upsert({"keyword": keyword.lower(), "country": country, "mode": mode, "response_data": data_list}).execute()
        except Exception: pass

HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_live_api_keywords(seed, country_suffix):
    gathered_set = set()
    localized_seed = f"{seed} {country_suffix}".strip()
    try:
        res = requests.get(f"https://datamuse.com{urllib.parse.quote(localized_seed)}&max=15", headers=HEADERS, timeout=4)
        if res.status_code == 200:
            for item in res.json(): gathered_set.add(f"{seed} {item['word']}")
    except Exception: pass
    return list(gathered_set)

def run_magnet_intelligence_matrix(client, seed, country):
    prompt = f"Act as a Magnet SEO engine. Generate 40 long-tail keywords for product concept derived from: '{seed}' in market context: '{country}'. Format: Keyword | Search Volume | Magnet IQ Score | Title Density | Match Type | Intent Profile. Return ONLY raw rows split by pipes."
    try:
        completion = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role": "user", "content": prompt}], temperature=0.1)
        return completion.choices[0].message.content.strip().split("\n")
    except Exception: return []

def run_harvester_intelligence_matrix(client, seed, country, raw_list_from_apis):
    prompt = f"Act as an SEO harvester. Filter strings and group into categories for product: '{seed}' in market: '{country}'. List: {str(raw_list_from_apis[:20])}. Format: Cluster Group | Keyword | Intent Category | Importance Status | Target Audience Persona. Return ONLY raw rows split by pipes. Strip all surrounding '**' bold symbols completely from names."
    try:
        completion = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role": "user", "content": prompt}], temperature=0.1)
        return completion.choices[0].message.content.strip().split("\n")
    except Exception: return []

# --- Command Center UI Routing Automation Node ---
# EXTENSION SYNC: Reads if extension triggered 'harvester' or 'magnet' parameter mode
url_mode_param = st.query_params.get("mode", "harvester")
default_index = 0 if url_mode_param == "harvester" else 1

with st.sidebar:
    st.markdown("### ⚙️ Command Center Control Panel")
    app_mode = st.radio("Select Active Tool Module:", ["🔍 Smart Keyword Harvester", "🧲 Magnet AI"], index=default_index)
    target_country = st.selectbox("Target Market Location:", ["🇺🇸 United States", "🇬🇧 United Kingdom", "🇦🇺 Australia", "🇮🇳 India"])
    country_suffix = {"🇺🇸 United States": "US", "🇬🇧 United Kingdom": "UK", "🇦🇺 Australia": "AU", "🇮🇳 India": "IN"}[target_country]
    
    st.markdown("---")
    if st.button("Log Out of System Platform Session"):
        st.session_state["authenticated"] = False
        st.rerun()

st.markdown(f"<h1>Command Center Enterprise SEO Suite</h1>", unsafe_allow_html=True)

api_key = os.getenv("MY_PROJECT_GROQ_KEY")
if not api_key:
    st.error("Missing valid internal AI tokens.")
else:
    client = Groq(api_key=api_key)
    url_text_param = st.query_params.get("search", "")

    if app_mode == "🔍 Smart Keyword Harvester":
        search_term = st.text_input("Enter Scraped Competitor Parameter Naming Elements:", value=url_text_param, placeholder="e.g., leather handbags, minimalist wallets").strip()
        if st.button("Harvest Clustered Keywords", type="primary"):
            if search_term:
                cached_data = get_cached_data(search_term, country_suffix, "harvester")
                if cached_data:
                    st.success("⚡ Data loaded instantly from Layered Cache System ($0 token usage)!")
                    st.dataframe(pd.DataFrame(cached_data), use_container_width=True)
                else:
                    with st.spinner("Processing deep keyword taxonomy matrices..."):
                        raw_words = fetch_live_api_keywords(search_term, country_suffix)
                        ai_lines = run_harvester_intelligence_matrix(client, search_term, target_country, raw_words)
                        parsed_rows = []
                        for line in ai_lines:
                            if "|" in line:
                                p = [item.strip().replace("**", "") for item in line.split("|")]
                                if len(p) >= 5: parsed_rows.append({"Cluster Group": p[0], "Harvested Keyword": p[1], "Buyer Intent Category": p[2], "Trend Importance Status": p[3], "Target Audience Focus": p[4]})
                        if parsed_rows:
                            set_cached_data(search_term, country_suffix, "harvester", parsed_rows)
                            st.dataframe(pd.DataFrame(parsed_rows), use_container_width=True)

    elif app_mode == "🧲 Magnet AI":
        search_term = st.text_input("Enter Root Keyword to Pull Advanced Market Metrics:", value=url_text_param, placeholder="e.g., wallet, mechanical keyboard").strip()
        if st.button("Run Magnet Research", type="primary"):
            if search_term:
                cached_data = get_cached_data(search_term, country_suffix, "magnet")
                if cached_data:
                    st.success("⚡ Metrics retrieved from permanent cloud cache storage layers!")
                    st.dataframe(pd.DataFrame(cached_data), use_container_width=True)
                else:
                    with st.spinner("Extracting search volume velocity layers..."):
                        ai_lines = run_magnet_intelligence_matrix(client, search_term, target_country)
                        parsed_rows = []
                        for line in ai_lines:
                            if "|" in line:
                                p = [item.strip() for item in line.split("|")]
                                if len(p) >= 6:
                                    try: vol = int(p[1].replace(",", ""))
                                    except: vol = 0
                                    try: iq = int(p[2].replace(",", ""))
                                    except: iq = 0
                                    try: dens = int(p[3].replace(",", ""))
                                    except: dens = 0
                                    parsed_rows.append({
                                        "Keyword": p[0], 
                                        "Search Volume": vol, 
                                        "Magnet IQ Score": iq, 
                                        "Title Density": dens, 
                                        "Match Type": p[4], 
                                        "Intent Profile": p[5]
                                    })
                        if parsed_rows:
                            df = pd.DataFrame(parsed_rows)
                            set_cached_data(search_term, country_suffix, "magnet", parsed_rows)
                            
                            # Premium Dashboard Layout Metrics Presentation Summary
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Magnet Keywords Found", len(df))
                            col2.metric("Average Search Volume", int(df['Search Volume'].mean()))
                            col3.metric("Top Opportunity IQ Score", int(df['Magnet IQ Score'].max()))
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.dataframe(df.sort_values(by="Search Volume", ascending=False), use_container_width=True)
                            
                            # CSV Exporter Node Link Wrapper
                            csv_bytes = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download Magnet Report (CSV)", 
                                data=csv_bytes, 
                                file_name=f"magnet_{search_term.replace(' ', '_')}.csv", 
                                mime="text/csv"
                            )
                        else: 
                            st.error("Failed to build metrics data matrix grid.")
