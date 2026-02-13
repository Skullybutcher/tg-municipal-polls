import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib3
import concurrent.futures
import pandas as pd
import time
import random

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- HARDCODED CONFIGURATION FOR TANDUR ---
DISTRICT_ID = "24"  # Vikarabad
ULB_ID = "1"        # Tandur
YEAR = "2026"
ELECTION_ID = "190"
TOTAL_WARDS = 36    # Tandur has 36 wards
BASE_URL = "https://tsec.gov.in/knowPRUrban.se"

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Tandur Election Tracker",
    page_icon=".//icons//ballot.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- SESSION STATE SETUP ---
if 'view' not in st.session_state:
    st.session_state.view = 'dashboard'
if 'selected_ward' not in st.session_state:
    st.session_state.selected_ward = None

# --- ROBUST NETWORK FUNCTION ---

def get_session():
    """Creates a robust session with browser headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': 'https://tsec.gov.in/'
    })
    return session

def fetch_ward_data_with_retry(ward_num, retries=3):
    """
    Tries to fetch data. If it fails, waits and retries automatically.
    """
    session = get_session()
    
    for attempt in range(retries):
        try:
            # 1. Get Security Token
            time.sleep(random.uniform(0.1, 0.5)) 
            
            resp = session.get(BASE_URL, verify=False, timeout=15)
            soup = BeautifulSoup(resp.content, 'html.parser')
            token_input = soup.find('input', attrs={'name': 'org.apache.struts.taglib.html.TOKEN'})
            
            if not token_input:
                raise ValueError("Token not found")
                
            token = token_input['value']

            # 2. Prepare Payload
            payload = {
                'org.apache.struts.taglib.html.TOKEN': token,
                'mode': 'getULBWMDetails',
                'property(knowYour)': 'WM',
                'property(year)': YEAR,
                'property(electionFor)': ELECTION_ID,
                'property(district_id)': DISTRICT_ID,
                'property(ulb_id)': ULB_ID,
                'property(ward_id)': str(ward_num),
                'property(typeOfReport)': 'A' 
            }

            # 3. Post Data
            post_resp = session.post(BASE_URL, data=payload, verify=False, timeout=20)
            
            # 4. Check Validity
            if post_resp.status_code != 200:
                raise ValueError(f"Status Code: {post_resp.status_code}")

            post_soup = BeautifulSoup(post_resp.content, 'html.parser')
            table = post_soup.find('table', id='GridView1')
            
            if not table:
                return {"ward": ward_num, "status": "Pending", "summary": {}, "candidates": []}

            # 5. Parse Data
            rows = post_soup.find('table', id='GridView1').find_all('tr')
            
            summary_data = {}
            candidate_rows = []

            for row in rows[1:]:
                if row.find('td', attrs={'colspan': True}):
                    text = row.get_text(strip=True)
                    parts = text.split(',')
                    for part in parts:
                        if ':' in part:
                            key, val = part.split(':', 1)
                            summary_data[key.strip()] = val.strip()
                    continue
                
                cells = row.find_all('td')
                if len(cells) >= 4:
                    c_status = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                    candidate_rows.append({
                        "Sl No": cells[0].get_text(strip=True),
                        "Candidate Name": cells[1].get_text(strip=True),
                        "Party": cells[2].get_text(strip=True),
                        "Votes": int(cells[3].get_text(strip=True)) if cells[3].get_text(strip=True).isdigit() else 0,
                        "Status": c_status
                    })

            winner_data = None
            status = "Pending"
            for cand in candidate_rows:
                if "elected" in cand['Status'].lower() or "won" in cand['Status'].lower():
                    status = "Declared"
                    winner_data = cand
                    break

            return {
                "ward": ward_num,
                "status": status,
                "winner": winner_data,
                "summary": summary_data,
                "candidates": candidate_rows
            }

        except Exception as e:
            if attempt == retries - 1:
                return {"ward": ward_num, "status": "Connection Error", "candidates": []}
            else:
                time.sleep(2 ** attempt) 

@st.cache_data(ttl=60, show_spinner=False)
def fetch_all_data():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_ward = {executor.submit(fetch_ward_data_with_retry, i): i for i in range(1, TOTAL_WARDS + 1)}
        
        bar = st.progress(0)
        completed = 0
        
        for future in concurrent.futures.as_completed(future_to_ward):
            results.append(future.result())
            completed += 1
            bar.progress(completed / TOTAL_WARDS)
            
        bar.empty()
        
    results.sort(key=lambda x: x['ward'])
    return results

# --- UI LOGIC ---

# Main Dashboard View
if st.session_state.view == 'dashboard':
    
    # 1. Mobile Friendly Header
    head_col1, head_col2 = st.columns([3, 1])
    
    with head_col1:
        st.title("Tandur Election")
        st.caption("Vikarabad District | Municipal Results 2026")
        
    with head_col2:
        st.write("") 
        if st.button("Refresh", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # 2. Data Fetching
    if 'data' not in st.session_state:
        with st.spinner("Connecting to TSEC Secure Server..."):
            data = fetch_all_data()
            st.session_state.data = data
    else:
        data = st.session_state.data

    # 3. Summary Metrics with System Status
    declared = sum(1 for d in data if d['status'] == 'Declared')
    pending = sum(1 for d in data if d['status'] == 'Pending')
    errors = sum(1 for d in data if d['status'] == 'Connection Error')
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Declared", declared)
        col2.metric("Pending", pending)
        
        if errors > 0:
            col3.metric("Network Retrying", errors, delta_color="inverse")
        else:
            col3.metric("System Status", "Healthy")

    # 4. PARTY PERFORMANCE SECTION
    st.markdown("### Party Wise Performance")

    # Calculate Party Counts
    party_counts = {}
    for item in data:
        if item['status'] == 'Declared' and item['winner']:
            party = item['winner']['Party']
            if party.upper() == 'IND':
                party = 'Independent'
            party_counts[party] = party_counts.get(party, 0) + 1
    
    if party_counts:
        # Create a clean DataFrame
        df_party = pd.DataFrame(list(party_counts.items()), columns=['Party', 'Wards Won'])
        df_party = df_party.sort_values(by='Wards Won', ascending=False).reset_index(drop=True)
        
        col_table, col_chart = st.columns([1, 2])
        
        with col_table:
            st.dataframe(
                df_party, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Party": st.column_config.TextColumn("Party Name"),
                    "Wards Won": st.column_config.NumberColumn("Seats Won", format="%d")
                }
            )
            
        with col_chart:
            # Custom Color Chart using Vega-Lite (No extra imports needed)
            st.vega_lite_chart(df_party, {
                "mark": {"type": "bar", "tooltip": True},
                "encoding": {
                    "x": {"field": "Party", "type": "nominal", "sort": "-y", "axis": {"title": "", "labelAngle": 0}},
                    "y": {"field": "Wards Won", "type": "quantitative", "axis": {"title": ""}},
                    "color": {
                        "field": "Party",
                        "type": "nominal",
                        "scale": {
                            "domain": ["BJP",     "BRS",     "INC",     "Independent", "AIMIM",     "CPI"],
                            "range":  ["#FF9933", "#FF3399", "#1F77B4", "#D62728",     "#008000", "#FF0000"] 
                        },
                        "legend": None
                    }
                }
            }, use_container_width=True)
            
    else:
        st.info("Waiting for results to be declared to generate party summary.")

    st.markdown("---")

    # 5. WARDS OVERVIEW SECTION
    st.markdown("### Wards Overview")

    # Grid Display - 3 Columns for bigger cards
    cols_per_row = 3
    rows = [data[i:i + cols_per_row] for i in range(0, len(data), cols_per_row)]

    for row_items in rows:
        cols = st.columns(cols_per_row)
        for idx, item in enumerate(row_items):
            with cols[idx]:
                with st.container(border=True):
                    c_head1, c_head2 = st.columns([3,1])
                    c_head1.subheader(f"Ward {item['ward']}")
                    
                    if item['status'] == 'Declared':
                        st.success("WON")
                        if item['winner']:
                            st.markdown(f"**{item['winner']['Candidate Name']}**")
                            st.caption(f"{item['winner']['Party']}")
                    elif item['status'] == 'Connection Error':
                        st.error("Error")
                    else:
                        st.warning("Pending")
                        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                    
                    if st.button("Details", key=f"btn_{item['ward']}", use_container_width=True):
                        st.session_state.selected_ward = item
                        st.session_state.view = 'detail'
                        st.rerun()

# Detail View
elif st.session_state.view == 'detail':
    ward = st.session_state.selected_ward
    
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("Back", use_container_width=True):
            st.session_state.view = 'dashboard'
            st.rerun()
    with col_title:
        st.subheader(f"Ward {ward['ward']} Report")
    
    summary = ward.get('summary', {})
    
    st.markdown("---")
    
    m1, m2 = st.columns(2)
    m1.metric("Total Voters", summary.get('Total Voters in Municipality Ward', '-'))
    m2.metric("Valid Votes", summary.get('Total Vaild Votes', '-'))
    
    m3, m4 = st.columns(2)
    m3.metric("Reserved For", summary.get('Reserved for', '-'))
    m4.metric("Rejected/NOTA", f"{summary.get('Rejected Votes', '0')} / {summary.get('NOTA Votes', '0')}")

    st.markdown("### Candidate Table")
    
    if ward['candidates']:
        df = pd.DataFrame(ward['candidates'])
        
        def style_rows(row):
            styles = [''] * len(row)
            if "Elected" in str(row['Status']):
                styles = ['background-color: #d1e7dd; color: #0f5132; font-weight: bold'] * len(row)
            return styles

        st.dataframe(
            df.style.apply(style_rows, axis=1), 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sl No": st.column_config.TextColumn("No.", width="small"),
                "Candidate Name": st.column_config.TextColumn("Candidate Name", width="medium"),
                "Party": st.column_config.TextColumn("Party", width="small"),
                "Votes": st.column_config.NumberColumn("Votes", format="%d"),
            }
        )
    else:
        st.info("No detailed candidate data available yet.")