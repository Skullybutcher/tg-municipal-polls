import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib3
import concurrent.futures
import pandas as pd
import re

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration for Tandur ---
DISTRICT_ID = "24"  # Vikarabad
ULB_ID = "1"        # Tandur
YEAR = "2026"
ELECTION_ID = "190"
TOTAL_WARDS = 36
BASE_URL = "https://tsec.gov.in/knowPRUrban.se"

# --- Backend Logic ---

def parse_summary_text(text):
    """
    Extracts key-value pairs from the summary string like:
    'WARD Name : 33 , Reserved for : UR(G), Total Voters... : 1879'
    """
    data = {}
    # Regex to find patterns like "Key : Value"
    # We look for text followed by a colon and then value until a comma or end of string
    parts = text.split(',')
    for part in parts:
        if ':' in part:
            key, val = part.split(':', 1)
            data[key.strip()] = val.strip()
    return data

def fetch_ward_full_data(ward_num):
    """
    Fetches EVERYTHING: Summary header, Winner status, and the full Candidate Table.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    try:
        # 1. Get Token
        resp = session.get(BASE_URL, verify=False, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        token_input = soup.find('input', attrs={'name': 'org.apache.struts.taglib.html.TOKEN'})
        
        if not token_input:
            return {"ward": ward_num, "status": "Error", "msg": "Token Error"}
            
        token = token_input['value']

        # 2. Post Data
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

        post_resp = session.post(BASE_URL, data=payload, verify=False, timeout=15)
        post_soup = BeautifulSoup(post_resp.content, 'html.parser')
        
        # 3. Parse Table
        table = post_soup.find('table', id='GridView1')
        if not table:
             return {"ward": ward_num, "status": "Pending", "summary": {}, "candidates": []}

        rows = table.find_all('tr')
        
        # A. Parse Summary Row (usually the row after header, colspan=5)
        summary_data = {}
        candidate_rows = []
        
        # Skip header row (index 0)
        for row in rows[1:]:
            # Check for Summary Row (it has colspan)
            if row.find('td', attrs={'colspan': True}):
                raw_text = row.get_text(strip=True)
                summary_data = parse_summary_text(raw_text)
                continue
            
            # Check for Candidate Rows
            cells = row.find_all('td')
            if len(cells) >= 4:
                # Extract data
                c_sl = cells[0].get_text(strip=True)
                c_name = cells[1].get_text(strip=True)
                c_party = cells[2].get_text(strip=True)
                c_votes = cells[3].get_text(strip=True)
                c_status = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                
                candidate_rows.append({
                    "Sl No": c_sl,
                    "Candidate Name": c_name,
                    "Party": c_party,
                    "Votes": int(c_votes) if c_votes.isdigit() else 0,
                    "Status": c_status
                })

        # B. Determine Winner
        winner_data = None
        status = "Pending"
        for cand in candidate_rows:
            if "Elected" in cand['Status'] or "won" in cand['Status'].lower():
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
        return {"ward": ward_num, "status": "Error", "msg": str(e), "candidates": []}

@st.cache_data(ttl=60)
def get_all_wards_data():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ward = {executor.submit(fetch_ward_full_data, i): i for i in range(1, TOTAL_WARDS + 1)}
        for future in concurrent.futures.as_completed(future_to_ward):
            results.append(future.result())
    results.sort(key=lambda x: x['ward'])
    return results

# --- UI LOGIC ---

# 1. Page Config
st.set_page_config(page_title="Tandur Election Dashboard", layout="wide")

# 2. Session State Management
if 'view' not in st.session_state:
    st.session_state.view = 'dashboard'
if 'selected_ward' not in st.session_state:
    st.session_state.selected_ward = None

def go_to_detail(ward_data):
    st.session_state.selected_ward = ward_data
    st.session_state.view = 'detail'

def go_to_dashboard():
    st.session_state.view = 'dashboard'
    st.session_state.selected_ward = None

# 3. Main Header
st.title("🗳️ Tandur Municipal Results Live")

# 4. Data Loading
if st.session_state.view == 'dashboard':
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Always fetch data (cached) so we have it available
data = get_all_wards_data()

# --- VIEW 1: DASHBOARD (Grid) ---
if st.session_state.view == 'dashboard':
    
    # Metrics
    declared_count = sum(1 for d in data if d['status'] == 'Declared')
    pending_count = TOTAL_WARDS - declared_count
    col1, col2 = st.columns(2)
    col1.metric("Results Declared", declared_count)
    col2.metric("Results Pending", pending_count)
    
    st.markdown("---")
    
    # Grid Logic
    cols_per_row = 4
    rows = [data[i:i + cols_per_row] for i in range(0, len(data), cols_per_row)]

    for row_items in rows:
        cols = st.columns(cols_per_row)
        for idx, item in enumerate(row_items):
            with cols[idx]:
                with st.container(border=True):
                    st.subheader(f"Ward {item['ward']}")
                    
                    if item['status'] == 'Declared':
                        st.success("✅ DECLARED")
                        if item['winner']:
                            st.write(f"**{item['winner']['Candidate Name']}**")
                            st.caption(f"{item['winner']['Party']}")
                    elif item['status'] == 'Error':
                        st.error("⚠️ Error")
                    else:
                        st.warning("⏳ Pending")
                        st.caption("Counting in progress...")
                        
                    # The "Details" Button
                    if st.button(f"View Details ➝", key=f"btn_{item['ward']}"):
                        go_to_detail(item)

# --- VIEW 2: DETAILS PAGE (Single Ward) ---
elif st.session_state.view == 'detail':
    ward = st.session_state.selected_ward
    
    # Back Button
    if st.button("← Back to Dashboard"):
        go_to_dashboard()
        st.rerun()

    # Header Section
    st.markdown(f"## 📍 Ward No. {ward['ward']} Details")
    
    # 1. Summary Metrics Card
    summary = ward.get('summary', {})
    
    # Clean up keys for display
    # Example keys: 'Total Voters in Municipality Ward', 'Total Vaild Votes', 'Reserved for'
    reserved_for = summary.get('Reserved for', 'N/A')
    total_voters = summary.get('Total Voters in Municipality Ward', '0')
    valid_votes = summary.get('Total Vaild Votes', '0')
    rejected = summary.get('Rejected Votes', '0')
    nota = summary.get('NOTA Votes', '0')

    with st.container(border=True):
        st.markdown("### 📊 Ward Statistics")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Reserved For", reserved_for)
        m2.metric("Total Voters", total_voters)
        m3.metric("Valid Votes", valid_votes)
        m4.metric("Rejected", rejected)
        m5.metric("NOTA", nota)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Candidates Table
    st.markdown("### 🏃 Candidate Performance")
    
    if ward['candidates']:
        df = pd.DataFrame(ward['candidates'])
        
        # Highlight the Winner Row Logic
        def highlight_winner(row):
            if "Elected" in str(row['Status']):
                return ['background-color: #d4edda; color: #155724']*len(row) # Light Green
            return ['']*len(row)

        # Apply styling
        styled_df = df.style.apply(highlight_winner, axis=1)

        # Show interactive dataframe
        st.dataframe(
            styled_df,
            column_config={
                "Sl No": st.column_config.NumberColumn("S.No", width="small"),
                "Candidate Name": st.column_config.TextColumn("Candidate Name", width="large"),
                "Party": st.column_config.TextColumn("Party", width="medium"),
                "Votes": st.column_config.ProgressColumn(
                    "Votes Secured", 
                    format="%d", 
                    min_value=0, 
                    max_value=int(total_voters) if total_voters.isdigit() and int(total_voters) > 0 else 1000
                ),
                "Status": st.column_config.TextColumn("Status", width="medium")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No candidate data available yet.")