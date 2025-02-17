from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import pandas as pd
from typing import List, Tuple, Dict, Any
import datetime

class GSCApi:
    """Google Search Console API wrapper"""
    
    def __init__(self, credentials):
        """Initialize the API with credentials"""
        self.credentials = credentials
        self.service = build('searchconsole', 'v1', credentials=credentials)

    def list_properties(self) -> List[str]:
        """Get list of GSC properties"""
        try:
            sites = self.service.sites().list().execute()
            return [site['siteUrl'] for site in sites.get('siteEntry', [])]
        except Exception as e:
            raise Exception(f"Failed to fetch properties: {str(e)}")

    def get_sitemap_data(self, site_url: str) -> Dict[str, Any]:
        """Get sitemap data for a specific site"""
        try:
            sitemaps = self.service.sitemaps().list(siteUrl=site_url).execute()
            return sitemaps
        except Exception as e:
            raise Exception(f"Failed to fetch sitemap data: {str(e)}")

    def inspect_url(self, site_url: str, url: str) -> Dict[str, Any]:
        """Inspect a specific URL"""
        try:
            body = {
                'inspectionUrl': url,
                'siteUrl': site_url
            }
            response = self.service.urlInspection().index().inspect(body=body).execute()
            return response
        except Exception as e:
            raise Exception(f"Failed to inspect URL: {str(e)}")

    def fetch_search_analytics(
        self,
        site_url: str,
        start_date: datetime.date,
        end_date: datetime.date,
        dimensions: List[str] = None,
        row_limit: int = 25000,
        url_filter: str = None
    ) -> pd.DataFrame:
        """
        Fetch search analytics data
        
        Args:
            site_url: GSC property URL
            start_date: Start date for data
            end_date: End date for data
            dimensions: List of dimensions to fetch
            row_limit: Maximum number of rows to fetch
            url_filter: Optional URL to filter results
        
        Returns:
            DataFrame with search analytics data
        """
        if dimensions is None:
            dimensions = ['page', 'query']

        request = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': dimensions,
            'rowLimit': row_limit,
            'dataState': 'all'  # Include fresh data
        }

        # Add URL filter if specified
        if url_filter:
            request['dimensionFilterGroups'] = [{
                'filters': [{
                    'dimension': 'page',
                    'operator': 'equals',
                    'expression': url_filter
                }]
            }]

        try:
            response = self.service.searchanalytics().query(
                siteUrl=site_url,
                body=request
            ).execute()

            if not response.get('rows'):
                return pd.DataFrame()

            # Process response into DataFrame
            data = []
            for row in response['rows']:
                item = {
                    dimensions[i]: value 
                    for i, value in enumerate(row['keys'])
                }
                item.update({
                    'clicks': row['clicks'],
                    'impressions': row['impressions'],
                    'ctr': row['ctr'],
                    'position': row['position']
                })
                data.append(item)

            df = pd.DataFrame(data)
            
            # Format metrics
            df['clicks'] = df['clicks'].astype(int)
            df['impressions'] = df['impressions'].astype(int)
            df['position'] = df['position'].round(1)
            df['ctr'] = (df['ctr'] * 100).round(1)

            return df

        except Exception as e:
            raise Exception(f"Failed to fetch search analytics: {str(e)}")

    def batch_fetch_urls(
        self,
        site_url: str,
        urls: List[str],
        start_date: datetime.date,
        end_date: datetime.date
    ) -> pd.DataFrame:
        """
        Fetch data for multiple URLs in batch
        
        Args:
            site_url: GSC property URL
            urls: List of URLs to fetch data for
            start_date: Start date for data
            end_date: End date for data
        
        Returns:
            DataFrame with combined data for all URLs
        """
        all_data = []
        
        for url in urls:
            try:
                df = self.fetch_search_analytics(
                    site_url=site_url,
                    start_date=start_date,
                    end_date=end_date,
                    dimensions=['page'],
                    url_filter=url
                )
                
                if not df.empty:
                    all_data.append(df)
                    
            except Exception as e:
                print(f"Error fetching data for {url}: {str(e)}")
                continue
        
        if not all_data:
            return pd.DataFrame()
            
        return pd.concat(all_data, ignore_index=True)

    def compare_periods(
        self,
        site_url: str,
        date_ranges: List[Tuple[datetime.date, datetime.date]],
        urls: List[str] = None
    ) -> pd.DataFrame:
        """
        Compare data across multiple periods
        
        Args:
            site_url: GSC property URL
            date_ranges: List of (start_date, end_date) tuples
            urls: Optional list of URLs to filter by
        
        Returns:
            DataFrame with comparison data
        """
        all_data = []
        
        for start_date, end_date in date_ranges:
            period_label = f"{start_date} to {end_date}"
            
            try:
                df = self.fetch_search_analytics(
                    site_url=site_url,
                    start_date=start_date,
                    end_date=end_date,
                    dimensions=['page'],
                    url_filter=urls[0] if urls else None
                )
                
                if not df.empty:
                    df['period'] = period_label
                    all_data.append(df)
                    
                if urls and len(urls) > 1:
                    # Fetch remaining URLs in batch
                    for url in urls[1:]:
                        url_df = self.fetch_search_analytics(
                            site_url=site_url,
                            start_date=start_date,
                            end_date=end_date,
                            dimensions=['page'],
                            url_filter=url
                        )
                        
                        if not url_df.empty:
                            url_df['period'] = period_label
                            all_data.append(url_df)
                            
            except Exception as e:
                print(f"Error fetching data for period {period_label}: {str(e)}")
                continue
        
        if not all_data:
            return pd.DataFrame()
            
        result = pd.concat(all_data, ignore_index=True)
        
        # Pivot the data for comparison
        pivot_df = result.pivot(
            index='page',
            columns='period',
            values=['clicks', 'impressions', 'ctr', 'position']
        )
        
        # Flatten column names
        pivot_df.columns = [f"{col[0]}_{col[1]}" for col in pivot_df.columns]
        
        return pivot_df.reset_index()
