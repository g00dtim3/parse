import streamlit as st
import pandas as pd
import re
from urllib.parse import urlparse
import json
import time
from datetime import datetime

# Check for required packages
try:
    import requests
    from bs4 import BeautifulSoup
    PACKAGES_AVAILABLE = True
except ImportError as e:
    PACKAGES_AVAILABLE = False
    MISSING_PACKAGES = str(e)

# Page configuration
st.set_page_config(
    page_title="Comment Extractor",
    page_icon="💬",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 10px 10px;
    }
    .comment-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: #f9f9f9;
    }
    .comment-author {
        font-weight: bold;
        color: #4a90e2;
    }
    .comment-date {
        color: #666;
        font-size: 0.9em;
    }
    .stats-container {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
    }
    .stat-box {
        text-align: center;
        padding: 1rem;
        background: #f0f2f6;
        border-radius: 10px;
        min-width: 100px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header"><h1>💬 Comment Extractor</h1><p>Extract comments and responses from various platforms</p></div>', unsafe_allow_html=True)

# Check if required packages are available
if not PACKAGES_AVAILABLE:
    st.error("⚠️ Missing Required Packages")
    st.markdown("""
    This app requires additional packages to be installed. Please run the following command in your terminal:
    
    ```bash
    pip install requests beautifulsoup4
    ```
    
    **Or install all requirements at once:**
    ```bash
    pip install streamlit requests beautifulsoup4 pandas lxml
    ```
    
    **If using conda:**
    ```bash
    conda install requests beautifulsoup4 pandas lxml
    ```
    
    After installation, restart the Streamlit app.
    """)
    
    st.info(f"**Error details:** {MISSING_PACKAGES}")
    st.stop()  # Stop execution here

class CommentExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def extract_reddit_comments(self, url):
        """Extract comments from Reddit posts"""
        try:
            # Convert to JSON API endpoint
            if not url.endswith('.json'):
                url = url.rstrip('/') + '.json'
            
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            comments = []
            
            # Handle Reddit JSON structure
            if isinstance(data, list) and len(data) > 1:
                comments_data = data[1]['data']['children']
                
                def parse_comment(comment_obj, depth=0):
                    if comment_obj['kind'] == 't1':  # Comment
                        comment_data = comment_obj['data']
                        comments.append({
                            'author': comment_data.get('author', '[deleted]'),
                            'text': comment_data.get('body', '[deleted]'),
                            'score': comment_data.get('score', 0),
                            'created_utc': datetime.fromtimestamp(comment_data.get('created_utc', 0)),
                            'depth': depth,
                            'id': comment_data.get('id', ''),
                            'permalink': f"https://reddit.com{comment_data.get('permalink', '')}"
                        })
                        
                        # Parse replies
                        if 'replies' in comment_data and comment_data['replies']:
                            if isinstance(comment_data['replies'], dict):
                                for reply in comment_data['replies']['data']['children']:
                                    parse_comment(reply, depth + 1)
                
                for comment in comments_data:
                    parse_comment(comment)
            
            return comments
            
        except Exception as e:
            st.error(f"Error extracting Reddit comments: {str(e)}")
            return []
    
    def extract_generic_comments(self, url):
        """Extract comments using generic HTML parsing"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            comments = []
            
            # Common comment selectors
            comment_selectors = [
                '.comment', '.comment-item', '.comment-content',
                '[class*="comment"]', '[id*="comment"]',
                '.reply', '.response', '.discussion-item'
            ]
            
            for selector in comment_selectors:
                comment_elements = soup.select(selector)
                if comment_elements:
                    for i, element in enumerate(comment_elements[:50]):  # Limit to 50
                        text = element.get_text(strip=True)
                        if len(text) > 10:  # Filter out very short texts
                            comments.append({
                                'author': 'Unknown',
                                'text': text[:500] + '...' if len(text) > 500 else text,
                                'score': None,
                                'created_utc': datetime.now(),
                                'depth': 0,
                                'id': f'generic_{i}',
                                'source': selector
                            })
                    if comments:
                        break
            
            return comments
            
        except Exception as e:
            st.error(f"Error extracting generic comments: {str(e)}")
            return []
    
    def extract_comments(self, url):
        """Main method to extract comments based on URL"""
        domain = urlparse(url).netloc.lower()
        
        if 'reddit.com' in domain:
            return self.extract_reddit_comments(url)
        else:
            return self.extract_generic_comments(url)

# Initialize extractor
@st.cache_resource
def get_extractor():
    return CommentExtractor()

extractor = get_extractor()

# Main interface
col1, col2 = st.columns([3, 1])

with col1:
    url_input = st.text_input(
        "Enter URL to extract comments from:",
        placeholder="https://www.reddit.com/r/example/comments/...",
        help="Supports Reddit URLs and attempts to extract from other platforms"
    )

with col2:
    st.write("")  # Spacing
    extract_button = st.button("🔍 Extract Comments", type="primary")

# Platform detection and info
if url_input:
    domain = urlparse(url_input).netloc.lower()
    if 'reddit.com' in domain:
        st.info("🎯 Reddit URL detected - will use Reddit API for better results")
    else:
        st.info("🌐 Generic URL - will attempt HTML parsing")

# Extract comments when button is pressed
if extract_button and url_input:
    with st.spinner("Extracting comments..."):
        comments = extractor.extract_comments(url_input)
    
    if comments:
        # Display statistics
        st.markdown("### 📊 Extraction Results")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Comments", len(comments))
        with col2:
            authors = set(c['author'] for c in comments if c['author'] != 'Unknown')
            st.metric("Unique Authors", len(authors))
        with col3:
            avg_length = sum(len(c['text']) for c in comments) / len(comments)
            st.metric("Avg Length", f"{avg_length:.0f} chars")
        with col4:
            scored_comments = [c for c in comments if c.get('score') is not None]
            if scored_comments:
                avg_score = sum(c['score'] for c in scored_comments) / len(scored_comments)
                st.metric("Avg Score", f"{avg_score:.1f}")
            else:
                st.metric("Avg Score", "N/A")
        
        # Display options
        st.markdown("### 📋 Display Options")
        col1, col2, col3 = st.columns(3)
        with col1:
            show_table = st.checkbox("Show as Table", value=True)
        with col2:
            show_cards = st.checkbox("Show as Cards", value=False)
        with col3:
            max_comments = st.slider("Max comments to display", 10, 100, 50)
        
        # Filter comments
        display_comments = comments[:max_comments]
        
        # Create DataFrame for table view
        if show_table:
            st.markdown("### 📄 Comments Table")
            
            df_data = []
            for comment in display_comments:
                df_data.append({
                    'Author': comment['author'],
                    'Comment': comment['text'][:100] + '...' if len(comment['text']) > 100 else comment['text'],
                    'Score': comment.get('score', 'N/A'),
                    'Date': comment['created_utc'].strftime('%Y-%m-%d %H:%M') if isinstance(comment['created_utc'], datetime) else 'N/A',
                    'Depth': comment.get('depth', 0)
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"comments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Card view
        if show_cards:
            st.markdown("### 💬 Comments Feed")
            
            for i, comment in enumerate(display_comments):
                with st.container():
                    # Indentation for nested comments
                    indent = "  " * comment.get('depth', 0)
                    
                    st.markdown(f"""
                    <div class="comment-card" style="margin-left: {comment.get('depth', 0) * 20}px;">
                        <div class="comment-author">{indent}👤 {comment['author']}</div>
                        <div class="comment-date">📅 {comment['created_utc'].strftime('%Y-%m-%d %H:%M') if isinstance(comment['created_utc'], datetime) else 'Unknown date'}</div>
                        <div style="margin-top: 0.5rem;">{comment['text']}</div>
                        {f'<div style="margin-top: 0.5rem; color: #666;">👍 Score: {comment["score"]}</div>' if comment.get('score') is not None else ''}
                    </div>
                    """, unsafe_allow_html=True)
        
        # JSON export option
        if st.checkbox("🔧 Show raw JSON data"):
            st.json(comments[:5])  # Show first 5 for preview
            
            json_data = json.dumps(comments, default=str, indent=2)
            st.download_button(
                label="📥 Download as JSON",
                data=json_data,
                file_name=f"comments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    else:
        st.warning("⚠️ No comments found. This could be due to:")
        st.markdown("""
        - The URL doesn't contain comments
        - The website blocks automated access
        - The comment structure is not recognized
        - Network issues or rate limiting
        """)

# Sidebar with instructions
with st.sidebar:
    st.markdown("### 📖 How to Use")
    st.markdown("""
    1. **Paste a URL** containing comments
    2. **Click Extract** to fetch comments
    3. **View results** in table or card format
    4. **Download data** as CSV or JSON
    
    ### 🎯 Supported Platforms
    - **Reddit** (best support)
    - **Generic websites** (basic support)
    
    ### 💡 Tips
    - For Reddit: Use the full post URL
    - Some sites may block automated access
    - Large comment threads may take longer
    """)
    
    st.markdown("### ⚙️ Settings")
    st.checkbox("Enable debug mode", help="Show additional technical information")
    
    st.markdown("---")
    st.markdown("Made with ❤️ using Streamlit")
