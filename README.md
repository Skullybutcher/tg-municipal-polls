# Tandur Election Tracker

A real-time, mobile-first dashboard built with **Streamlit** to monitor municipal election results for **Tandur Municipality** (Vikarabad District).

This application scrapes live data from the Telangana State Election Commission (TSEC) website, presenting it in a clean, modern interface optimized for mobile devices.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-ff4b4b)
![Status](https://img.shields.io/badge/Status-Active-success)

## Live Demo

Check out the deployed application here:
👉 **[Tandur Election Tracker Live](https://telangana-municipal-results-tandur-by-ashtikar.streamlit.app/)**

## Features

* **Real-Time Data:** Fetches live election status and vote counts directly from TSEC servers.
* **Mobile-First Design:** Optimized grid layout (3 cards per row) and navigation for easy viewing on phones.
* **Robust Networking:** Includes auto-retry logic, connection pooling, and error handling to manage server load and timeouts.
* **Live Dashboard:** Instant overview of Declared vs. Pending results and System Health.
* **Ward Details:** Click on any ward to see a detailed table of candidates, vote shares, and winners.
* **System Status:** Visual indicators for network health (Healthy vs. Retrying).

## Installation

### Prerequisites
* Python 3.8 or higher

### Steps

1.  **Clone the repository:**
    
```bash
    git clone [https://github.com/your-username/tandur-election-tracker.git](https://github.com/your-username/tandur-election-tracker.git)
    cd tandur-election-tracker
    
```

2.  **Install dependencies:**
    
```
bash
    pip install streamlit requests beautifulsoup4 pandas urllib3
    
```

3.  **Run the application:**
    
```
bash
    streamlit run dashboard.py
    
```

## Configuration

The application is currently hardcoded for **Tandur (ID: 1)** in **Vikarabad District (ID: 24)** for the **2026 Election Cycle**.

You can modify these constants in `dashboard.py` to track other municipalities:

```
python
# --- CONFIGURATION ---
DISTRICT_ID = "24"  # Vikarabad
ULB_ID = "1"        # Tandur
YEAR = "2026"
ELECTION_ID = "190"
TOTAL_WARDS = 36
```

## Tech Stack

- **Frontend:** Streamlit
- **Scraping:** BeautifulSoup4 & Requests
- **Data Processing:** Pandas
- **Concurrency:** concurrent.futures (ThreadPoolExecutor)

## Disclaimer

This tool is for educational and monitoring purposes only. It scrapes data from the public TSEC portal.

- This is not an official government application.
- Data availability depends on the TSEC server status.
- Please be responsible with refresh rates to avoid overloading government servers.

## License

This project is open-source and available under the MIT License.
