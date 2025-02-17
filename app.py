import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import plotly.express as px
from pathlib import Path
import base64
import io
from gsc_api import GSCApi
from url_manager import URLManager
from data_viz import DataVisualizer
from site_analyzer import SiteAnalyzer

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
    if 'date_range' not in st.session_state:
        st.session_state.date_range = '30'
    if 'comparison_periods' not in st.session_state:
        st.session_state.comparison_periods = 1

def setup_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="Ultimate GSC & Analytics SEO Dashboard",
        page_icon="📊",
        layout="wide"
    )
    st.title("📊 Ultimate GSC & Analytics SEO Dashboard")
    st.markdown("---")

def load_google_credentials():
    """Load and validate Google API credentials from Streamlit secrets"""
    try:
        # Check if credentials exist in Streamlit secrets
        if 'gsc_credentials' not in st.secrets:
            st.error("GSC credentials not found in secrets. Please configure them in your Streamlit secrets.")
            st.info("""
            To configure credentials:
            1. Local development: Add them to .streamlit/secrets.toml
            2. Streamlit Cloud: Add them in the app settings under "Secrets"
            """)
            return None
            
        credentials = st.secrets['gsc_credentials']
        
        # Validate required fields
        required_fields = ['client_id', 'client_secret', 'redirect_uri']
        missing_fields = [field for field in required_fields if field not in credentials]
        
        if missing_fields:
            st.error(f"Missing required credentials: {', '.join(missing_fields)}")
            return None
            
        # Build the client config dictionary
        client_config = {
            "installed": {
                "client_id": credentials['client_id'],
                "client_secret": credentials['client_secret'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token",
                "redirect_uris": [credentials['redirect_uri']],
            }
        }
        
        return client_config
        
    except Exception as e:
        st.error(f"Error loading credentials: {str(e)}")
        return None

def get_date_ranges(days: int, periods: int = 1) -> list:
    """Generate date ranges for comparison"""
    today = datetime.datetime.now().date()
    ranges = []
    
    for i in range(periods):
        end_date = today - datetime.timedelta(days=1) - datetime.timedelta(days=(days * i))
        start_date = end_date - datetime.timedelta(days=days-1)
        ranges.append((start_date, end_date))
    
    return ranges

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
    setup_page()
    init_session_state()
    
    # Sidebar for authentication and settings
    with st.sidebar:
        st.header("Settings")
        
        # Google Authentication
        if st.session_state.credentials is None:
            st.info("Please log in with your Google account to access Search Console data.")
            
            if st.button("🔐 Login with Google"):
                client_config = load_google_credentials()
                if client_config:
                    try:
                        flow = Flow.from_client_config(
                            client_config,
                            scopes=SCOPES,
                            redirect_uri=client_config["installed"]["redirect_uris"][0]
                        )
                        auth_url, _ = flow.authorization_url(prompt="consent")
                        st.session_state.flow = flow
                        st.markdown(f'[Click here to login with Google]({auth_url})')
                    except Exception as e:
                        st.error(f"Authentication error: {str(e)}")
        else:
            st.success("✓ Successfully logged in")
            if st.button("Logout"):
                st.session_state.credentials = None
                st.experimental_rerun()

            # Optional Features
            st.subheader("Analysis Options")
            st.session_state.comparison_enabled = st.checkbox(
                "Enable Comparison",
                value=st.session_state.comparison_enabled,
                help="Compare metrics across multiple time periods"
            )
            
            if st.session_state.comparison_enabled:
                st.session_state.comparison_periods = st.number_input(
                    "Number of periods to compare",
                    min_value=1,
                    max_value=4,
                    value=st.session_state.comparison_periods,
                    help="Compare up to 4 consecutive periods"
                )
            
            st.session_state.sitemap_enabled = st.checkbox(
                "Enable Sitemap Analysis",
                value=st.session_state.sitemap_enabled,
                help="Analyze sitemap data"
            )
            
            st.session_state.url_inspection_enabled = st.checkbox(
                "Enable URL Inspection",
                value=st.session_state.url_inspection_enabled,
                help="Inspect individual URLs"
            )
    
    # Main content
    if st.session_state.credentials is None:
        st.warning("Please log in to access the dashboard")
        return
        
    # Initialize GSC API
    gsc_api = GSCApi(st.session_state.credentials)
    
    # Property Selection
    try:
        properties = gsc_api.list_properties()
        if not properties:
            st.warning("No properties found in your Google Search Console")
            return
            
        selected_property = st.selectbox(
            "Select Property",
            options=properties,
            index=0 if st.session_state.selected_property is None else properties.index(st.session_state.selected_property)
        )
        st.session_state.selected_property = selected_property
        
    except Exception as e:
        st.error(f"Error loading properties: {str(e)}")
        return
    
    # URL Management
    st.subheader("URL Management")
    url_manager_col1, url_manager_col2 = st.columns([2, 1])
    
    with url_manager_col1:
        url_input_method = st.radio(
            "URL Input Method",
            options=["Upload File", "Paste URLs", "Saved Lists"],
            horizontal=True
        )
        
        if url_input_method == "Upload File":
            uploaded_file = st.file_uploader("Upload URL list (CSV or TXT)", type=['csv', 'txt'])
            if uploaded_file:
                urls = URLManager.parse_urls_from_file(uploaded_file)
                if urls:
                    st.success(f"Loaded {len(urls)} URLs")
                    st.session_state.current_urls = urls
                else:
                    st.error("No valid URLs found in file")
                    
        elif url_input_method == "Paste URLs":
            url_text = st.text_area("Paste URLs (one per line)")
            if url_text:
                urls = URLManager.parse_urls_from_text(url_text)
                if urls:
                    st.success(f"Loaded {len(urls)} URLs")
                    st.session_state.current_urls = urls
                else:
                    st.error("No valid URLs found")
                    
        elif url_input_method == "Saved Lists":
            saved_lists = URLManager.get_all_list_names()
            if not saved_lists:
                st.info("No saved URL lists found")
            else:
                selected_list = st.selectbox("Select Saved List", options=saved_lists)
                if selected_list:
                    urls = URLManager.get_url_list(selected_list)
                    if urls:
                        st.success(f"Loaded {len(urls)} URLs")
                        st.session_state.current_urls = urls
    
    with url_manager_col2:
        if 'current_urls' in st.session_state and st.session_state.current_urls:
            st.info(f"Current URL List ({len(st.session_state.current_urls)} URLs)")
            if st.button("Save Current List"):
                list_name = st.text_input("List Name")
                if list_name:
                    if URLManager.save_url_list(list_name, st.session_state.current_urls):
                        st.success(f"Saved list: {list_name}")
    
    # Date Range Selection
    st.subheader("Date Range")
    date_col1, date_col2 = st.columns([1, 2])
    
    with date_col1:
        st.session_state.date_range = st.selectbox(
            "Select Period",
            options=['30', '60', '90', '180', '360', 'YoY'],
            format_func=lambda x: f"{x} days" if x != 'YoY' else "Year over Year",
            help="Select the time period for analysis"
        )
    
    with date_col2:
        if st.session_state.date_range == 'YoY':
            date_ranges = [
                (datetime.date.today() - relativedelta(years=1, days=1),
                 datetime.date.today() - datetime.timedelta(days=1)),
                (datetime.date.today() - relativedelta(years=2, days=1),
                 datetime.date.today() - relativedelta(years=1, days=1))
            ]
        else:
            date_ranges = get_date_ranges(
                int(st.session_state.date_range),
                st.session_state.comparison_periods if st.session_state.comparison_enabled else 1
            )
        
        # Display selected date ranges
        for i, (start_date, end_date) in enumerate(date_ranges):
            st.info(f"Period {i+1}: {start_date} to {end_date}")
            
    # Data Analysis Section
    if 'current_urls' in st.session_state and st.session_state.current_urls:
        st.header("Data Analysis")
        
        with st.spinner("Fetching data from Google Search Console..."):
            try:
                # Fetch data for each URL and period
                all_data = []
                
                for url in st.session_state.current_urls:
                    for i, (start_date, end_date) in enumerate(date_ranges):
                        period_label = f"Period_{i+1}"
                        
                        df = gsc_api.fetch_search_analytics(
                            site_url=st.session_state.selected_property,
                            start_date=start_date,
                            end_date=end_date,
                            dimensions=['page'],
                            url_filter=url
                        )
                        
                        if not df.empty:
                            # Rename columns to include period
                            df.columns = [f"{col}_{period_label}" if col != 'page' else col 
                                        for col in df.columns]
                            all_data.append(df)
                
                if not all_data:
                    st.warning("No data found for the selected URLs and time periods")
                    return
                    
                # Combine all data
                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df = combined_df.groupby('page').first().reset_index()
                
                # Format metrics
                combined_df = DataVisualizer.format_metrics(combined_df)
                
                # Create period labels for visualization
                period_labels = [f"Period_{i+1}" for i in range(len(date_ranges))]
                
                # Calculate summary statistics
                summary = DataVisualizer.create_metric_summary(combined_df, period_labels)
                
                # Display metric summaries
                st.subheader("Metrics Overview")
                metric_tabs = st.tabs(["Clicks", "Impressions", "CTR", "Position"])
                
                for metric_tab, metric in zip(metric_tabs, ['clicks', 'impressions', 'ctr', 'position']):
                    with metric_tab:
                        # Display metric cards
                        DataVisualizer.display_metric_cards(summary, metric)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Comparison chart
                            fig = DataVisualizer.create_comparison_chart(
                                combined_df,
                                metric,
                                period_labels
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                        with col2:
                            # Trend chart
                            fig = DataVisualizer.create_trend_chart(
                                combined_df,
                                metric,
                                period_labels
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Heatmap for changes
                        if len(period_labels) > 1:
                            fig = DataVisualizer.create_heatmap(
                                combined_df,
                                metric,
                                period_labels
                            )
                            st.plotly_chart(fig, use_container_width=True)
                
                # Data Export
                st.subheader("Export Data")
                export_data = DataVisualizer.prepare_export_data(
                    combined_df,
                    summary,
                    period_labels
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Export URL metrics
                    csv_metrics = export_data['url_metrics'].to_csv(index=False)
                    st.download_button(
                        "Download URL Metrics (CSV)",
                        csv_metrics,
                        "gsc_url_metrics.csv",
                        "text/csv",
                        key='download_metrics'
                    )
                    
                with col2:
                    # Export summary
                    csv_summary = export_data['summary'].to_csv(index=False)
                    st.download_button(
                        "Download Summary (CSV)",
                        csv_summary,
                        "gsc_summary.csv",
                        "text/csv",
                        key='download_summary'
                    )
                    
            except Exception as e:
                st.error(f"Error analyzing data: {str(e)}")
    else:
        st.info("Please load URLs to analyze data")

    # Sitemap Analysis
    if st.session_state.sitemap_enabled:
        st.header("🗺️ Sitemap Analysis")
        
        sitemap_col1, sitemap_col2 = st.columns([2, 1])
        
        with sitemap_col1:
            sitemap_input = st.text_input(
                "Enter Sitemap URL",
                placeholder="https://example.com/sitemap.xml",
                help="Enter the full URL of your sitemap"
            )
            
            if sitemap_input:
                with st.spinner("Analyzing sitemap..."):
                    try:
                        # Parse sitemap
                        sitemap_df = SiteAnalyzer.parse_sitemap(sitemap_input)
                        
                        if not sitemap_df.empty:
                            # Analyze sitemap data
                            insights = SiteAnalyzer.analyze_sitemap_data(sitemap_df)
                            
                            # Display insights
                            st.subheader("📊 Sitemap Insights")
                            
                            # Basic stats
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Total URLs", insights['total_urls'])
                            
                            with col2:
                                if insights['last_updated']:
                                    st.metric("Last Updated", insights['last_updated'].strftime('%Y-%m-%d'))
                            
                            with col3:
                                if insights['urls_by_domain']:
                                    domains = len(insights['urls_by_domain'])
                                    st.metric("Domains", domains)
                            
                            # URL Distribution
                            st.subheader("📁 URL Distribution by Directory")
                            if insights['urls_by_directory']:
                                dir_df = pd.DataFrame(
                                    list(insights['urls_by_directory'].items()),
                                    columns=['Directory', 'Count']
                                )
                                fig = px.bar(
                                    dir_df,
                                    x='Directory',
                                    y='Count',
                                    title='Top Directories'
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # Update Frequency
                            if insights['update_frequency']:
                                st.subheader("🔄 Update Frequency")
                                freq_df = pd.DataFrame(
                                    list(insights['update_frequency'].items()),
                                    columns=['Frequency', 'Count']
                                )
                                fig = px.pie(
                                    freq_df,
                                    values='Count',
                                    names='Frequency',
                                    title='Content Update Frequency'
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # Priority Distribution
                            if insights['priority_distribution']:
                                st.subheader("⭐ Priority Distribution")
                                priority_df = pd.DataFrame(
                                    list(insights['priority_distribution'].items()),
                                    columns=['Priority', 'Count']
                                )
                                fig = px.bar(
                                    priority_df,
                                    x='Priority',
                                    y='Count',
                                    title='URL Priorities'
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # Export option
                            st.download_button(
                                "Download Sitemap Data (CSV)",
                                sitemap_df.to_csv(index=False),
                                "sitemap_data.csv",
                                "text/csv",
                                key='download_sitemap'
                            )
                            
                    except Exception as e:
                        st.error(f"Error analyzing sitemap: {str(e)}")
        
        with sitemap_col2:
            st.info("""
            ### About Sitemap Analysis
            
            The sitemap analyzer provides insights about your website's structure and content organization:
            
            - **Total URLs**: Number of URLs in the sitemap
            - **Last Updated**: Most recent content update
            - **Update Frequency**: How often content changes
            - **Priority Distribution**: URL importance levels
            - **Directory Structure**: Content organization
            
            Use these insights to:
            - Identify content gaps
            - Optimize crawl budget
            - Improve site structure
            """)
    
    # URL Inspection
    if st.session_state.url_inspection_enabled and 'current_urls' in st.session_state:
        st.header("🔍 URL Inspection")
        
        inspection_col1, inspection_col2 = st.columns([2, 1])
        
        with inspection_col1:
            if st.button("Inspect Current URLs"):
                with st.spinner("Inspecting URLs..."):
                    try:
                        # Batch inspect URLs
                        results = SiteAnalyzer.batch_inspect_urls(
                            gsc_api,
                            st.session_state.selected_property,
                            st.session_state.current_urls
                        )
                        
                        # Display results
                        SiteAnalyzer.display_inspection_results(results)
                        
                        # Prepare results for export
                        inspection_data = []
                        for url, data in results.items():
                            if 'error' not in data:
                                row = {
                                    'URL': url,
                                    'Coverage Verdict': data['Coverage'].get('Verdict'),
                                    'Mobile Verdict': data['Mobile Usability'].get('Verdict'),
                                    'Rich Results Verdict': data['Rich Results'].get('Verdict'),
                                    'Last Crawl': data['Coverage'].get('Last Crawl'),
                                    'Coverage State': data['Coverage'].get('Coverage State'),
                                    'Indexing Allowed': data['Coverage'].get('Indexing Allowed?'),
                                    'Robots.txt': data['Coverage'].get('Crawl Allowed?')
                                }
                                inspection_data.append(row)
                        
                        if inspection_data:
                            inspection_df = pd.DataFrame(inspection_data)
                            st.download_button(
                                "Download Inspection Results (CSV)",
                                inspection_df.to_csv(index=False),
                                "inspection_results.csv",
                                "text/csv",
                                key='download_inspection'
                            )
                            
                    except Exception as e:
                        st.error(f"Error inspecting URLs: {str(e)}")
        
        with inspection_col2:
            st.info("""
            ### About URL Inspection
            
            The URL inspector checks various aspects of your URLs:
            
            - **Coverage**: Indexing status and issues
            - **Mobile Usability**: Mobile-friendly assessment
            - **Rich Results**: Structured data validation
            - **Performance**: Page performance metrics
            
            Use these insights to:
            - Fix indexing issues
            - Improve mobile experience
            - Optimize rich results
            - Enhance page performance
            """)

if __name__ == "__main__":
    main()
