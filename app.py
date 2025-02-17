import streamlit as st
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import json
from pathlib import Path
import base64
import io

# Configuration and Constants
SEARCH_TYPES = ["web", "image", "video", "news", "discover", "googleNews"]
PERIOD_OPTIONS = {
    "30 Days": 30,
    "60 Days": 60,
    "90 Days": 90,
    "180 Days": 180,
    "360 Days": 360,
    "Year over Year": "YoY"
}
MAX_ROWS = 1_000_000
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Initialize session state
def init_session_state():
    """Initialize Streamlit session state variables"""
    if 'saved_url_lists' not in st.session_state:
        st.session_state.saved_url_lists = {}
    if 'credentials' not in st.session_state:
        st.session_state.credentials = None
    if 'selected_property' not in st.session_state:
        st.session_state.selected_property = None
    if 'comparison_enabled' not in st.session_state:
        st.session_state.comparison_enabled = False
    if 'sitemap_enabled' not in st.session_state:
        st.session_state.sitemap_enabled = False
    if 'url_inspection_enabled' not in st.session_state:
        st.session_state.url_inspection_enabled = False

def setup_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="Ultimate GSC & GA4 SEO Dashboard",
        page_icon="📊",
        layout="wide"
    )
    st.title("📊 Ultimate GSC & GA4 SEO Dashboard")
    st.markdown("---")

def load_google_credentials():
    """Load and validate Google API credentials"""
    try:
        client_config = {
            "installed": {
                "client_id": st.secrets["installed"]["client_id"],
                "client_secret": st.secrets["installed"]["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token",
                "redirect_uris": [st.secrets["installed"]["redirect_uri"]],
            }
        }
        return client_config
    except Exception as e:
        st.error(f"Error loading credentials: {str(e)}")
        return None

def calculate_date_ranges(period, num_periods=1):
    """
    Calculate date ranges for comparison, excluding today
    
    Args:
        period (str): Period option key from PERIOD_OPTIONS
        num_periods (int): Number of consecutive periods to analyze
    
    Returns:
        list: List of tuples containing (start_date, end_date) for each period
    """
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    if period == "Year over Year":
        # For YoY, always compare with same period last year
        current_end = yesterday
        current_start = current_end - datetime.timedelta(days=29)  # 30 days including end date
        last_year_end = current_end - datetime.timedelta(days=365)
        last_year_start = current_start - datetime.timedelta(days=365)
        return [(last_year_start, last_year_end), (current_start, current_end)]
    
    # For other periods
    days = PERIOD_OPTIONS[period]
    ranges = []
    end_date = yesterday
    
    for i in range(num_periods):
        start_date = end_date - datetime.timedelta(days=days-1)
        ranges.append((start_date, end_date))
        end_date = start_date - datetime.timedelta(days=1)
    
    return ranges

def format_metrics(df):
    """Format metrics according to specifications"""
    df['clicks'] = df['clicks'].astype(int)
    df['impressions'] = df['impressions'].astype(int)
    df['position'] = df['position'].round(1)
    df['ctr'] = (df['ctr'] * 100).round(1).astype(str) + '%'
    return df

class URLListManager:
    """Manage saved URL lists"""
    
    @staticmethod
    def save_list(name, urls):
        """Save a URL list with given name"""
        if not name:
            st.error("Please provide a name for the URL list")
            return False
        
        st.session_state.saved_url_lists[name] = urls
        return True
    
    @staticmethod
    def get_list(name):
        """Retrieve a saved URL list by name"""
        return st.session_state.saved_url_lists.get(name, [])
    
    @staticmethod
    def delete_list(name):
        """Delete a saved URL list"""
        if name in st.session_state.saved_url_lists:
            del st.session_state.saved_url_lists[name]
            return True
        return False
    
    @staticmethod
    def get_all_list_names():
        """Get names of all saved URL lists"""
        return list(st.session_state.saved_url_lists.keys())

def main():
    """Main application function"""
    setup_page()
    init_session_state()
    
    # Sidebar for authentication and settings
    with st.sidebar:
        st.header("Settings")
        
        # Google Authentication
        if st.session_state.credentials is None:
            client_config = load_google_credentials()
            if client_config:
                st.info("Please authenticate with Google")
                if st.button("Authenticate"):
                    # Authentication logic here
                    pass
        else:
            st.success("✓ Authenticated with Google")
            if st.button("Logout"):
                st.session_state.credentials = None
                st.experimental_rerun()
        
        # Optional Features
        st.subheader("Optional Features")
        st.session_state.comparison_enabled = st.checkbox("Enable Comparison", value=st.session_state.comparison_enabled)
        st.session_state.sitemap_enabled = st.checkbox("Enable Sitemap Analysis", value=st.session_state.sitemap_enabled)
        st.session_state.url_inspection_enabled = st.checkbox("Enable URL Inspection", value=st.session_state.url_inspection_enabled)
    
    # Main content
    if st.session_state.credentials is None:
        st.warning("Please authenticate with Google to continue")
        return
    
    # URL Management
    st.header("URL Management")
    url_management_tab, data_analysis_tab = st.tabs(["URL Lists", "Data Analysis"])
    
    with url_management_tab:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Add URLs")
            upload_method = st.radio("Choose input method:", ["Upload File", "Paste URLs"])
            
            if upload_method == "Upload File":
                uploaded_file = st.file_uploader("Upload URL list (CSV/TXT)", type=['csv', 'txt'])
                if uploaded_file:
                    # File processing logic here
                    pass
            else:
                urls_input = st.text_area("Paste URLs (one per line)")
                if urls_input:
                    # URL processing logic here
                    pass
        
        with col2:
            st.subheader("Saved Lists")
            saved_lists = URLListManager.get_all_list_names()
            if saved_lists:
                selected_list = st.selectbox("Select saved list", saved_lists)
                if selected_list:
                    urls = URLListManager.get_list(selected_list)
                    st.write(f"URLs in list: {len(urls)}")
                    if st.button("Delete List"):
                        URLListManager.delete_list(selected_list)
                        st.experimental_rerun()
            else:
                st.info("No saved lists found")
    
    with data_analysis_tab:
        if not st.session_state.selected_property:
            st.warning("Please select a GSC property first")
            return
        
        # Date Range Selection
        st.subheader("Date Range Selection")
        period = st.selectbox("Select Period", list(PERIOD_OPTIONS.keys()))
        
        if period != "Year over Year" and st.session_state.comparison_enabled:
            num_periods = st.number_input("Number of periods to compare", min_value=2, max_value=6, value=2)
        else:
            num_periods = 1
        
        # Calculate date ranges
        date_ranges = calculate_date_ranges(period, num_periods)
        
        # Display date ranges
        st.write("Selected Date Ranges:")
        for start, end in date_ranges:
            st.write(f"- {start} to {end}")
        
        if st.button("Fetch Data"):
            # Data fetching logic here
            pass

if __name__ == "__main__":
    main()
