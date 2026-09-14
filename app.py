import csv
import os
import string
import time
import sqlite3
import urllib.parse
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from postgrest import SyncPostgrestClient

load_dotenv()

st.set_page_config(
    page_title="Command Center Enterprise SEO Suite", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main .block-container { padding-top: 2rem; }
.metric-card {
    background-color: #1E293B;
    border: 1px solid #334155;
    padding: 1.2rem;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.15);
}
.metric-num {
    font-size: 2.2rem;
    font-weight: 700;
    color: #00F2FE;
    line-height: 1;
}
.metric-lbl {
    font-size: 0.85rem;
    color: #94A3B8;
    margin-top: 0.5rem;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# --- SECURITY GATEWAY ---
def check_user_credentials():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown("<h2 style='text-align: center; color: #FF4B4B;'>🔒 Enterprise SEO Suite Gateway</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("Login Form"):
                username = st.text_input("SaaS Username:")
                password = st.text_input("Access Password:", type="password")
                submit = st.form_submit_button("Authenticate Access", type="primary")
                
                if submit:
                    if username == "admin" and password == "saas123":
                        st.session_state["authenticated"] = True
                        st.success("Access Granted!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
            st.stop()

check_user_credentials()

# --- DATABASE SETUP ---
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

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        supabase_client = SyncPostgrestClient(f"{SUPABASE_URL}/rest/v1", headers=headers)
    except Exception:
        pass

def get_cached_data(keyword, country, mode):
    try:
        conn = sqlite3.connect("keyword_cache.db")
        cursor = conn.cursor()
        cursor.execute("SELECT response_data FROM cache WHERE keyword=? AND country=? AND mode=?", (keyword.lower(), country, mode))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]: 
            return json.loads(row[0])
    except Exception:
        pass

    if supabase_client:
        try:
            res = supabase_client.from_("keyword_cache").select("response_data").eq("keyword", keyword.lower()).eq("country", country).eq("mode", mode).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]["response_data"]
        except Exception:
            pass
    return None

def set_cached_data(keyword, country, mode, data_list):
    try:
        conn = sqlite3.connect("keyword_cache.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cache (keyword, country, mode, response_data, timestamp) VALUES (?, ?, ?, ?, ?)", 
            (keyword.lower(), country, mode, json.dumps(data_list), time.time())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    if supabase_client:
        try:
            supabase_client.from_("keyword_cache").upsert({
                "keyword": keyword.lower(), "country": country, "mode": mode, "response_data": data_list
            }).execute()
        except Exception:
            pass

# --- FAST MULTI-THREADED REAL SCRAPERS ---
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

AMAZON_MARKETPLACE_IDS = {
    "US": "ATVPDKIKX0DER",
    "UK": "A1F83G8C2ARO7P",
    "AU": "A39IBJ37TRP1C6",
    "IN": "A21TJRUUN4KGV"
}

def fetch_amazon_suggestions(query, country_suffix):
    mid = AMAZON_MARKETPLACE_IDS.get(country_suffix, "ATVPDKIKX0DER")
    url = f"https://completion.amazon.com/api/2/search?limit=11&prefix={urllib.parse.quote(query)}&mid={mid}&alias=aps"
    try:
        r = requests.get(url, headers=HEADERS, timeout=3)
        if r.status_code == 200:
            data = r.json()
            return [item["value"] for item in data.get("suggestions", []) if "value" in item]
    except Exception:
        pass
    return []

def fetch_google_suggestions(query, country_suffix):
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(query)}&gl={country_suffix.lower()}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if len(data) > 1 and isinstance(data[1], list):
                return data[1]
    except Exception:
        pass
    return []

def scrape_query_pair(query, country_suffix):
    """Worker task that checks both Google and Amazon concurrently for a given query."""
    amz = fetch_amazon_suggestions(query, country_suffix)
    goog = fetch_google_suggestions(query, country_suffix)
    return amz, goog

def harvest_real_keywords_parallel(seed, country_suffix, deep_scan=False):
    """Runs concurrent scraping for high speed, avoiding timeouts and IP throttling."""
    gathered_sources = {}
    
    # Generate query list (base + A-Z or base + top 8 letters)
    queries = [seed]
    letters = list(string.ascii_lowercase) if deep_scan else list(string.ascii_lowercase[:8])
    for l in letters:
        queries.append(f"{seed} {l}")

    # Fire all queries in parallel threads (5 to 8 workers is safe and fast)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(scrape_query_pair, q, country_suffix) for q in queries]
        for f in as_completed(futures):
            amz_res, goog_res = f.result()
            for kw in amz_res:
                kw_clean = kw.lower().strip()
                if kw_clean and kw_clean != seed.lower():
                    entry = gathered_sources.setdefault(kw_clean, {"amz": 0, "goog": 0})
                    entry["amz"] += 1
            for kw in goog_res:
                kw_clean = kw.lower().strip()
                if kw_clean and kw_clean != seed.lower():
                    entry = gathered_sources.setdefault(kw_clean, {"amz": 0, "goog": 0})
                    entry["goog"] += 1

    return gathered_sources

# --- AI ENRICHMENT ---
def analyze_and_cluster_keywords(client, seed, country, raw_keywords):
    sample_keywords = raw_keywords[:50]
    prompt = f"""
You are an expert E-commerce SEO Analyst.
Analyze these REAL user search queries for root keyword: '{seed}' in market: '{country}'.

Keyword List:
{json.dumps(sample_keywords)}

Categorize each keyword. Output ONLY pipe-separated values in this exact structure:
Keyword | Cluster Group | Search Intent (High Commercial / Informational / Navigational) | Priority (High / Medium / Low) | Target Persona

Rules: No headers, no markdown bolding, no dashes, raw rows only.
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content.strip().split("\n")
    except Exception:
        return []

# --- UI & NAVIGATION ---
url_mode_param = st.query_params.get("mode", "harvester")
default_index = 0 if url_mode_param == "harvester" else 1

with st.sidebar:
    st.markdown("### ⚙️ Control Panel")
    app_mode = st.radio("Select Tool Module:", ["🔍 Smart Keyword Harvester", "🧲 Real Demand Magnet"], index=default_index)
    target_country = st.selectbox("Target Market Location:", ["🇺🇸 United States", "🇬🇧 United Kingdom", "🇦🇺 Australia", "🇮🇳 India"])
    country_suffix = {"🇺🇸 United States": "US", "🇬🇧 United Kingdom": "UK", "🇦🇺 Australia": "AU", "🇮🇳 India": "IN"}[target_country]
    
    deep_harvest = st.checkbox("Enable Deep Alphabet Scan (A-Z)", value=False, help="Scrapes all 26 letters concurrently. Captures 60 to 100+ real search terms.")
    force_refresh = st.checkbox("Bypass Cache (Force Fresh Live Scrape)", value=False)

    st.markdown("---")
    if st.button("Log Out"):
        st.session_state["authenticated"] = False
        st.rerun()

st.markdown("<h1>Command Center Enterprise SEO Suite</h1>", unsafe_allow_html=True)

api_key = os.getenv("MY_PROJECT_GROQ_KEY")
if not api_key:
    st.error("Missing valid Groq API Key in `.env` file (`MY_PROJECT_GROQ_KEY`).")
else:
    client = Groq(api_key=api_key)
    url_text_param = st.query_params.get("search", "")

    # MODULE 1: SMART KEYWORD HARVESTER
    if app_mode == "🔍 Smart Keyword Harvester":
        search_term = st.text_input("Enter Product Keyword / Niche:", value=url_text_param, placeholder="e.g., leather wallet, mechanical keyboard").strip()
        
        if st.button("Harvest & Cluster Real Keywords", type="primary"):
            if search_term:
                cache_mode_key = f"harvester_deep" if deep_harvest else "harvester_fast"
                cached_data = None if force_refresh else get_cached_data(search_term, country_suffix, cache_mode_key)
                
                if cached_data:
                    st.success("⚡ Loaded instantly from Cache ($0 token cost)!")
                    st.dataframe(pd.DataFrame(cached_data), use_container_width=True)
                else:
                    with st.spinner("Scraping live Amazon & Google suggest engines in parallel..."):
                        keyword_dict = harvest_real_keywords_parallel(search_term, country_suffix, deep_scan=deep_harvest)
                        real_raw_kws = list(keyword_dict.keys())

                    if not real_raw_kws:
                        st.error("No suggestions returned from live search engines. Try a broader search phrase.")
                    else:
                        with st.spinner("Analyzing intent and clustering taxonomies..."):
                            ai_lines = analyze_and_cluster_keywords(client, search_term, target_country, real_raw_kws)
                            
                            # --- START OF ANTI-HALLUCINATION PARSING ---
                            verified_scraped_set = set(k.lower().strip() for k in real_raw_kws)
                            parsed_rows = []
                            
                            for line in ai_lines:
                                if "|" in line and "---" not in line:
                                    p = [item.strip().replace("**", "") for item in line.split("|")]
                                    if len(p) >= 5 and p[0].lower() != "keyword":
                                        returned_kw = p[0].lower()
                                        
                                        # Programmatic Guard: only accept if scraped from Amazon/Google
                                        if returned_kw in verified_scraped_set:
                                            parsed_rows.append({
                                                "Keyword": p[0],
                                                "Cluster Group": p[1],
                                                "Search Intent": p[2],
                                                "Priority": p[3],
                                                "Target Persona": p[4],
                                                "Data Origin": "Verified Live Autocomplete"
                                            })
                            # --- END OF ANTI-HALLUCINATION PARSING ---

                            # Fallback if AI formatting fails: display raw scraped keywords instead of a blank screen
                            if not parsed_rows:
                                parsed_rows = [{"Keyword": kw, "Cluster Group": "General", "Search Intent": "Commercial", "Priority": "Medium", "Target Persona": "Shopper"} for kw in real_raw_kws]

                            set_cached_data(search_term, country_suffix, cache_mode_key, parsed_rows)
                            df = pd.DataFrame(parsed_rows)

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(f'<div class="metric-card"><div class="metric-num">{len(df)}</div><div class="metric-lbl">Keywords Harvested</div></div>', unsafe_allow_html=True)
                            with col2:
                                st.markdown(f'<div class="metric-card"><div class="metric-num">{len(df["Cluster Group"].unique())}</div><div class="metric-lbl">Taxonomy Clusters</div></div>', unsafe_allow_html=True)
                            with col3:
                                st.markdown('<div class="metric-card"><div class="metric-num">100%</div><div class="metric-lbl">Verified Live Suggestion Data</div></div>', unsafe_allow_html=True)

                            st.markdown("<br>", unsafe_allow_html=True)
                            st.dataframe(df, use_container_width=True)
                            
                            csv_bytes = df.to_csv(index=False).encode('utf-8')
                            st.download_button("📥 Export Keywords (CSV)", csv_bytes, f"harvest_{search_term}.csv", "text/csv")

    # MODULE 2: REAL DEMAND MAGNET
    elif app_mode == "🧲 Real Demand Magnet":
        search_term = st.text_input("Enter Root Keyword for Market Demand Analysis:", value=url_text_param, placeholder="e.g., minimalist wallet, standing desk").strip()
        
        if st.button("Extract Real Search Demand", type="primary"):
            if search_term:
                cache_mode_key = f"magnet_deep" if deep_harvest else "magnet_fast"
                cached_data = None if force_refresh else get_cached_data(search_term, country_suffix, cache_mode_key)
                
                if cached_data:
                    st.success("⚡ Loaded from Cache!")
                    st.dataframe(pd.DataFrame(cached_data), use_container_width=True)
                else:
                    with st.spinner("Extracting multi-engine search velocity & demand matrix..."):
                        keyword_dict = harvest_real_keywords_parallel(search_term, country_suffix, deep_scan=deep_harvest)
                        
                        if not keyword_dict:
                            st.error("No real autocomplete metrics found for this query.")
                        else:
                            # Sort keywords: queries appearing in both engines and multiple variations rank highest
                            sorted_items = sorted(
                                keyword_dict.items(), 
                                key=lambda x: (x[1]["amz"] + x[1]["goog"], x[1]["amz"]), 
                                reverse=True
                            )

                            parsed_rows = []
                            for rank, (kw, counts) in enumerate(sorted_items, start=1):
                                amz_present = "✅ Yes" if counts["amz"] > 0 else "❌ No"
                                goog_present = "✅ Yes" if counts["goog"] > 0 else "❌ No"
                                
                                # Score from 100 down based on rank and presence
                                relative_score = max(15, 100 - (rank * 2))
                                
                                parsed_rows.append({
                                    "Search Keyword": kw,
                                    "Demand Rank": f"#{rank}",
                                    "Demand Score (1-100)": relative_score,
                                    "Amazon Buyer Presence": amz_present,
                                    "Google Search Presence": goog_present,
                                    "Word Count": len(kw.split())
                                })

                            df = pd.DataFrame(parsed_rows)
                            set_cached_data(search_term, country_suffix, cache_mode_key, parsed_rows)

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(f'<div class="metric-card"><div class="metric-num">{len(df)}</div><div class="metric-lbl">Total Real Queries Found</div></div>', unsafe_allow_html=True)
                            with col2:
                                st.markdown(f'<div class="metric-card"><div class="metric-num">{df["Demand Score (1-100)"].max()}</div><div class="metric-lbl">Peak Demand Velocity</div></div>', unsafe_allow_html=True)
                            with col3:
                                scan_type = "Deep Scan (A-Z)" if deep_harvest else "Standard Scan"
                                st.markdown(f'<div class="metric-card"><div class="metric-num">{scan_type}</div><div class="metric-lbl">Scan Depth</div></div>', unsafe_allow_html=True)

                            st.markdown("<br>", unsafe_allow_html=True)
                            st.dataframe(df, use_container_width=True)

                            csv_bytes = df.to_csv(index=False).encode('utf-8')
                            st.download_button("📥 Download Magnet Report (CSV)", csv_bytes, f"magnet_{search_term}.csv", "text/csv")
