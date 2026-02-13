import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import urllib3

# Tell Python to ignore SSL certificate warnings, which are common on gov sites
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://tsec.gov.in"
ACTION_URL = "https://tsec.gov.in/knowPRUrban.se"

def get_election_data(ulb_id, ward_id):
    print(f"\n[i] Connecting to TSEC server... please wait.")

    # Use a session to keep cookies across requests
    session = requests.Session()
    # Fake user agent so we look like a browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    try:
        # 1. GET Request: Load the initial page to get the security token
        print("[i] Fetching security token...")
        initial_response = session.get(ACTION_URL, verify=False, timeout=15)
        initial_soup = BeautifulSoup(initial_response.content, 'html.parser')

        # Find the hidden Struts token field
        token_input = initial_soup.find('input', attrs={'name': 'org.apache.struts.taglib.html.TOKEN'})
        if not token_input:
            print("[!] Error: Could not find security token on page.")
            return
        token = token_input['value']

        # 2. Prepare payload based on your previous HTML inputs
        # Note: We are hardcoding District 24 (Vikarabad), Year 2026, and Election 190 
        # based on the default selections in the HTML you provided previously.
        payload = {
            'org.apache.struts.taglib.html.TOKEN': token,
            'mode': 'getULBWMDetails',
            'property(knowYour)': 'WM',
            'property(year)': '2026',       # Hardcoded based on your provided HTML
            'property(electionFor)': '190', # Hardcoded based on your provided HTML
            'property(district_id)': '24',  # Hardcoded Vikarabad based on HTML
            'property(ulb_id)': str(ulb_id),   # USER INPUT
            'property(ward_id)': str(ward_id), # USER INPUT
            'property(typeOfReport)': 'A'   # 'A' for All candidates
        }

        # 3. POST Request: Send the data
        print(f"[i] Fetching data for ULB: {ulb_id}, Ward: {ward_id}...")
        post_response = session.post(ACTION_URL, data=payload, verify=False, timeout=30)
        
        # 4. Parse the results
        parse_and_display_results(post_response.content)

    except requests.exceptions.RequestException as e:
        print(f"\n[!] Connection Error: {e}")

def parse_and_display_results(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the specific results table by its ID
    table = soup.find('table', id='GridView1')

    if not table:
        print("\n[!] Could not find results table. Check your ULB/Ward IDs.")
        # Sometimes errors are shown in alert boxes in the HTML, complex to parse.
        return

    # --- Extract Table Headers ---
    headers = []
    header_row = table.find('tr')
    if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all('th')]

    # --- Extract Table Data ---
    data = []
    # Skip the first row (headers)
    rows = table.find_all('tr')[1:]

    summary_text = ""

    for row in rows:
        # The table sometimes has a summary row spanning all columns right after headers
        # Example: "WARD Name : 33 , Reserved for : UR(G)..."
        if row.find('td', attrs={'colspan': True}):
            summary_text = row.get_text(strip=True)
            continue
            
        cells = row.find_all('td')
        if not cells:
            continue
            
        row_data = [cell.get_text(strip=True) for cell in cells]
        data.append(row_data)

    # --- Terminal Output ---
    if summary_text:
        print(f"\n{'='*60}")
        # Wrap text nicely for terminal width
        import textwrap
        print(textwrap.fill(summary_text, width=80))
        print(f"{'='*60}\n")

    if data and headers:
        # Use tabulate for pretty terminal printing
        print(tabulate(data, headers=headers, tablefmt="fancy_grid"))
    else:
        print("[!] No candidate data found for this selection.")


# --- Main Terminal Loop ---
if __name__ == "__main__":
    print("--- TSEC Urban Election Results Terminal App ---")
    print("Note: Currently hardcoded for District: Vikarabad (ID 24), Year: 2026")
    print("Type 'exit' to quit.\n")
    
    while True:
        try:
            ulb_input = input("Enter ULB ID (e.g., 1 for Tandur): ").strip()
            if ulb_input.lower() == 'exit': break
            
            ward_input = input("Enter Ward Number ID (e.g., 33): ").strip()
            if ward_input.lower() == 'exit': break

            if not ulb_input or not ward_input:
                print("Both IDs are required.")
                continue
                
            get_election_data(ulb_input, ward_input)
            print("\n" + "-"*30 + "\n")
            
        except KeyboardInterrupt:
            print("\nExiting.")
            break