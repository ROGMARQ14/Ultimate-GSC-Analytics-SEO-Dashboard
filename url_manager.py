import pandas as pd
from typing import List, Optional
import streamlit as st
import io
import csv

class URLManager:
    """Manage URL lists with persistence using Streamlit's session state"""
    
    @staticmethod
    def parse_urls_from_text(text: str) -> List[str]:
        """Parse URLs from text input"""
        urls = [url.strip() for url in text.split('\n') if url.strip()]
        return [url for url in urls if url.startswith(('http://', 'https://'))]

    @staticmethod
    def parse_urls_from_file(file) -> List[str]:
        """Parse URLs from uploaded file (CSV or TXT)"""
        content = file.read()
        
        # Try to decode as text
        try:
            if isinstance(content, bytes):
                content = content.decode('utf-8')
        except UnicodeDecodeError:
            st.error("Failed to decode file. Please ensure it's a valid text file.")
            return []

        # Handle CSV files
        if file.name.endswith('.csv'):
            try:
                # Try reading as CSV
                df = pd.read_csv(io.StringIO(content))
                # Assume first column contains URLs
                urls = df.iloc[:, 0].tolist()
            except Exception:
                # If CSV parsing fails, try reading line by line
                urls = content.split('\n')
        else:
            # Handle as plain text file
            urls = content.split('\n')

        # Clean and validate URLs
        urls = [url.strip() for url in urls if url.strip()]
        return [url for url in urls if url.startswith(('http://', 'https://'))]

    @staticmethod
    def save_url_list(name: str, urls: List[str]) -> bool:
        """Save a URL list to session state"""
        if not name:
            st.error("Please provide a name for the URL list")
            return False
            
        if not urls:
            st.error("No valid URLs provided")
            return False

        # Initialize URL lists in session state if not exists
        if 'saved_url_lists' not in st.session_state:
            st.session_state.saved_url_lists = {}

        # Save the list
        st.session_state.saved_url_lists[name] = urls
        return True

    @staticmethod
    def get_url_list(name: str) -> Optional[List[str]]:
        """Retrieve a saved URL list by name"""
        if 'saved_url_lists' not in st.session_state:
            return None
        return st.session_state.saved_url_lists.get(name)

    @staticmethod
    def delete_url_list(name: str) -> bool:
        """Delete a saved URL list"""
        if 'saved_url_lists' not in st.session_state:
            return False
            
        if name in st.session_state.saved_url_lists:
            del st.session_state.saved_url_lists[name]
            return True
        return False

    @staticmethod
    def get_all_list_names() -> List[str]:
        """Get names of all saved URL lists"""
        if 'saved_url_lists' not in st.session_state:
            return []
        return list(st.session_state.saved_url_lists.keys())

    @staticmethod
    def export_url_list(name: str) -> Optional[str]:
        """Export a URL list as CSV"""
        urls = URLManager.get_url_list(name)
        if not urls:
            return None
            
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['URL'])
        writer.writerows([[url] for url in urls])
        return output.getvalue()

    @staticmethod
    def validate_url_list(urls: List[str]) -> List[str]:
        """Validate and clean URL list"""
        valid_urls = []
        for url in urls:
            url = url.strip()
            if url and url.startswith(('http://', 'https://')):
                valid_urls.append(url)
        return valid_urls
