# GSC Analytics Dashboard 📊

A powerful Streamlit-based dashboard for Google Search Console data analysis with advanced comparison features.

## Features 🚀

### Core Functionality
- 🔐 Secure Google OAuth Authentication
- 📊 Comprehensive GSC Data Retrieval
- 📈 Advanced Period Comparisons
- 📋 URL List Management
- 📤 Data Export Capabilities

### Data Analysis
- Compare multiple time periods:
  - 30, 60, 90, 180, 360 days
  - Year-over-Year comparison
  - Multiple consecutive periods
- Metrics tracked:
  - Clicks (integer)
  - Impressions (integer)
  - Average Position (1 decimal)
  - CTR (percentage, 1 decimal)

### URL Management
- Upload URL lists (CSV/TXT)
- Direct URL input
- Save and manage multiple URL lists
- Export URL lists

### Optional Features
- 🗺️ Sitemap Analysis
- 🔍 URL Inspection
- 📊 Search Analytics Data

## Installation 🛠️

1. Clone the repository:
```bash
git clone https://github.com/yourusername/GSC-Analytics-Dashboard.git
cd GSC-Analytics-Dashboard
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up Google Search Console API:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable the Google Search Console API
   - Create OAuth 2.0 credentials
   - Download the client secrets file

4. Configure the application:
   - Rename the downloaded client secrets file to `client_secrets.json`
   - Place it in the project root directory

## Usage 💡

1. Start the application:
```bash
streamlit run app.py
```

2. Authenticate with Google:
   - Click the "Authenticate" button
   - Follow the OAuth flow
   - Grant necessary permissions

3. Select GSC Property:
   - Choose from available properties
   - Or use URL list management for specific URLs

4. Configure Analysis:
   - Select time period
   - Enable comparison if needed
   - Choose optional features
   - Set data filters

5. Export Data:
   - Download as CSV
   - View in-app visualizations
   - Save URL lists for future use

## Features in Detail 📝

### Period Comparison
- Compare data across multiple time periods
- Automatic date range calculation
- Excludes current day for accuracy
- YoY comparison for seasonal analysis

### URL Management
- Save multiple URL lists
- Name and organize lists
- Import from CSV/TXT
- Direct URL input
- Export functionality

### Data Formatting
- Clicks: Integer values
- Impressions: Integer values
- Average Position: 1 decimal place
- CTR: Percentage with 1 decimal place

### Optional Analysis
- Sitemap Analysis: Upload XML or provide URL
- URL Inspection: Detailed page information
- Search Analytics: Comprehensive query data

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- Google Search Console API
- Streamlit Framework
- Python Community

## Support 💬

For support, please open an issue in the GitHub repository or contact the maintainers.

## Disclaimer ⚠️

This is not an official Google product. This application is a third-party tool that uses Google Search Console's API.
