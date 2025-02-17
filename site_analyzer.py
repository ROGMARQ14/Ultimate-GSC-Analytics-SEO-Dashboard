import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
import concurrent.futures

class SiteAnalyzer:
    """Handle sitemap analysis and URL inspection"""
    
    @staticmethod
    def parse_sitemap(sitemap_url: str) -> pd.DataFrame:
        """Parse sitemap XML and return URLs with metadata"""
        try:
            response = requests.get(sitemap_url, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            # Handle sitemap index files
            if 'sitemapindex' in root.tag:
                # Fetch and combine all sitemaps
                urls_data = []
                for sitemap in root.findall('.//{*}sitemap'):
                    loc = sitemap.find('{*}loc')
                    if loc is not None:
                        sub_sitemap_url = loc.text
                        sub_urls = SiteAnalyzer.parse_sitemap(sub_sitemap_url)
                        urls_data.extend(sub_urls)
                return pd.DataFrame(urls_data)
            
            # Process regular sitemap
            urls_data = []
            for url in root.findall('.//{*}url'):
                url_data = {
                    'url': url.find('{*}loc').text if url.find('{*}loc') is not None else None,
                    'lastmod': url.find('{*}lastmod').text if url.find('{*}lastmod') is not None else None,
                    'changefreq': url.find('{*}changefreq').text if url.find('{*}changefreq') is not None else None,
                    'priority': url.find('{*}priority').text if url.find('{*}priority') is not None else None
                }
                urls_data.append(url_data)
            
            df = pd.DataFrame(urls_data)
            
            # Convert lastmod to datetime
            if 'lastmod' in df.columns:
                df['lastmod'] = pd.to_datetime(df['lastmod'])
            
            # Convert priority to float
            if 'priority' in df.columns:
                df['priority'] = pd.to_numeric(df['priority'], errors='coerce')
            
            return df
            
        except Exception as e:
            st.error(f"Error parsing sitemap: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    def analyze_sitemap_data(df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze sitemap data and return insights"""
        if df.empty:
            return {}
            
        insights = {
            'total_urls': len(df),
            'last_updated': df['lastmod'].max() if 'lastmod' in df.columns else None,
            'update_frequency': {},
            'priority_distribution': {},
            'urls_by_directory': {},
            'urls_by_domain': {}
        }
        
        # Analyze change frequency
        if 'changefreq' in df.columns:
            insights['update_frequency'] = df['changefreq'].value_counts().to_dict()
        
        # Analyze priority distribution
        if 'priority' in df.columns:
            insights['priority_distribution'] = df['priority'].value_counts().to_dict()
        
        # Analyze URL structure
        df['parsed_url'] = df['url'].apply(urlparse)
        df['directory'] = df['parsed_url'].apply(lambda x: x.path.rsplit('/', 1)[0])
        df['domain'] = df['parsed_url'].apply(lambda x: x.netloc)
        
        insights['urls_by_directory'] = df['directory'].value_counts().head(10).to_dict()
        insights['urls_by_domain'] = df['domain'].value_counts().to_dict()
        
        return insights

    @staticmethod
    def format_inspection_results(results: Dict[str, Any]) -> Dict[str, Any]:
        """Format URL inspection results for display"""
        formatted = {
            'Coverage': {},
            'Mobile Usability': {},
            'Rich Results': {},
            'Performance': {}
        }
        
        if not results:
            return formatted
            
        inspection_result = results.get('inspectionResult', {})
        
        # Coverage data
        coverage = inspection_result.get('indexStatusResult', {})
        formatted['Coverage'] = {
            'Verdict': coverage.get('verdict'),
            'Coverage State': coverage.get('coverageState'),
            'Crawl Allowed?': coverage.get('robotsTxtState'),
            'Page Fetch': coverage.get('pageFetchState'),
            'Indexing Allowed?': coverage.get('indexingState'),
            'Last Crawl': coverage.get('lastCrawlTime')
        }
        
        # Mobile Usability
        mobile = inspection_result.get('mobileUsabilityResult', {})
        formatted['Mobile Usability'] = {
            'Verdict': mobile.get('verdict'),
            'Issues': mobile.get('issues', [])
        }
        
        # Rich Results
        rich_results = inspection_result.get('richResultsResult', {})
        formatted['Rich Results'] = {
            'Verdict': rich_results.get('verdict'),
            'Detected Items': rich_results.get('detectedItems', [])
        }
        
        # Performance metrics (if available)
        performance = inspection_result.get('performanceResult', {})
        if performance:
            formatted['Performance'] = performance
            
        return formatted

    @staticmethod
    def batch_inspect_urls(
        gsc_api: Any,
        site_url: str,
        urls: List[str],
        max_workers: int = 5
    ) -> Dict[str, Dict[str, Any]]:
        """Inspect multiple URLs in parallel"""
        results = {}
        
        def inspect_url(url: str) -> Tuple[str, Dict[str, Any]]:
            try:
                result = gsc_api.inspect_url(site_url, url)
                return url, SiteAnalyzer.format_inspection_results(result)
            except Exception as e:
                return url, {'error': str(e)}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(inspect_url, url): url 
                for url in urls
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    url, result = future.result()
                    results[url] = result
                except Exception as e:
                    results[url] = {'error': str(e)}
        
        return results

    @staticmethod
    def display_inspection_results(results: Dict[str, Dict[str, Any]]):
        """Display URL inspection results in Streamlit"""
        for url, data in results.items():
            with st.expander(f"📄 {url}"):
                if 'error' in data:
                    st.error(f"Error inspecting URL: {data['error']}")
                    continue
                
                for section, details in data.items():
                    if details:  # Only show non-empty sections
                        st.subheader(section)
                        
                        if isinstance(details, dict):
                            for key, value in details.items():
                                if value:  # Only show non-empty values
                                    st.write(f"**{key}:** {value}")
                        elif isinstance(details, list):
                            for item in details:
                                st.write(f"- {item}")
                        else:
                            st.write(details)
