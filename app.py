import streamlit as st
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse
import json
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter, defaultdict
import difflib
import html

# Page configuration
st.set_page_config(
    page_title="HTML vs JS Crawler Pro - Screaming Frog Style",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🕷️"
)

# Custom CSS for professional look
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .status-success { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-error { color: #dc3545; font-weight: bold; }
    .crawl-table { font-size: 12px; }
    .sidebar-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<div class="main-header"><h1>🕷️ HTML vs JS Crawler Pro</h1><p>Professional-grade website analysis tool with HTML diff viewer</p></div>', unsafe_allow_html=True)

# Initialize session state
if 'crawl_results' not in st.session_state:
    st.session_state.crawl_results = []
if 'crawl_running' not in st.session_state:
    st.session_state.crawl_running = False
if 'driver_manager' not in st.session_state:
    st.session_state.driver_manager = None
if 'selected_url_for_diff' not in st.session_state:
    st.session_state.selected_url_for_diff = None

class WebDriverManager:
    """Manages a single, reusable WebDriver instance for stability in cloud environments."""
    def __init__(self):
        self.driver = None
        self._lock = threading.Lock()

    def get_driver(self):
        with self._lock:
            if self.driver is None:
                self.driver = self._create_driver()
            return self.driver

    def _create_driver(self):
        try:
            st.info("Initializing WebDriver... This may take a moment.")
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")

            # Performance settings to disable images and notifications
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)

            # Use webdriver-manager to handle driver installation
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            st.success("WebDriver initialized successfully.")
            return driver
        except Exception as e:
            st.error(f"Fatal Error: Failed to create WebDriver. The service may not be able to run. Error: {e}")
            st.stop()
            return None

    def cleanup(self):
        with self._lock:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    st.warning(f"Error while quitting WebDriver: {e}")
                finally:
                    self.driver = None


class HTMLDiffAnalyzer:
    def __init__(self, original_html, rendered_html):
        self.original_html = original_html
        self.rendered_html = rendered_html
        self.original_lines = self._clean_html(original_html).splitlines()
        self.rendered_lines = self._clean_html(rendered_html).splitlines()
        
    def _clean_html(self, html_content):
        """Clean and format HTML for better diff comparison"""
        if not html_content:
            return ""
        
        # Parse with BeautifulSoup for consistent formatting
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.prettify()
    
    def generate_diff(self, context_lines=3):
        """Generate unified diff between original and rendered HTML"""
        differ = difflib.unified_diff(
            self.original_lines,
            self.rendered_lines,
            fromfile='Original HTML',
            tofile='Rendered HTML',
            lineterm='',
            n=context_lines
        )
        return list(differ)
    
    def get_change_statistics(self):
        """Get statistics about changes between HTML versions"""
        matcher = difflib.SequenceMatcher(None, self.original_lines, self.rendered_lines)
        
        stats = {
            'total_lines_original': len(self.original_lines),
            'total_lines_rendered': len(self.rendered_lines),
            'lines_added': 0,
            'lines_removed': 0,
            'lines_modified': 0,
            'similarity_ratio': matcher.ratio(),
            'js_injections': 0,
            'meta_changes': 0,
            'structural_changes': 0
        }
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                stats['lines_added'] += (j2 - j1)
                # Check for JS injections
                for line in self.rendered_lines[j1:j2]:
                    if '<script' in line.lower() or 'javascript:' in line.lower():
                        stats['js_injections'] += 1
                    elif '<meta' in line.lower() or 'content=' in line.lower():
                        stats['meta_changes'] += 1
            elif tag == 'delete':
                stats['lines_removed'] += (i2 - i1)
            elif tag == 'replace':
                stats['lines_modified'] += max(i2 - i1, j2 - j1)
                stats['structural_changes'] += 1
        
        return stats

def create_streamlit_diff_viewer(diff_analyzer, search_term="", show_only_changes=False):
    """Create a working diff viewer using Streamlit components"""
    
    # Get statistics
    stats = diff_analyzer.get_change_statistics()
    
    # Display statistics in columns
    st.subheader("Diff Statistics")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Lines Added", stats['lines_added'])
    with col2:
        st.metric("Lines Removed", stats['lines_removed'])
    with col3:
        st.metric("Lines Modified", stats['lines_modified'])
    with col4:
        st.metric("JS Injections", stats['js_injections'])
    with col5:
        st.metric("Meta Changes", stats['meta_changes'])
    with col6:
        similarity_pct = stats['similarity_ratio'] * 100
        st.metric("Similarity", f"{similarity_pct:.1f}%")
    
    # Create side-by-side comparison using Streamlit columns
    st.subheader("HTML Comparison")
    
    original_lines = diff_analyzer.original_lines
    rendered_lines = diff_analyzer.rendered_lines
    
    # Generate diff using difflib
    matcher = difflib.SequenceMatcher(None, original_lines, rendered_lines)
    
    # Collect changes for display
    original_display = []
    rendered_display = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            if not show_only_changes:
                # Show unchanged lines
                for i in range(i1, i2):
                    line = original_lines[i]
                    if search_term and search_term.lower() in line.lower():
                        line = line.replace(search_term, f"**{search_term}**")
                    original_display.append(f"   {i+1:4d}: {line}")
                
                for j in range(j1, j2):
                    line = rendered_lines[j]
                    if search_term and search_term.lower() in line.lower():
                        line = line.replace(search_term, f"**{search_term}**")
                    rendered_display.append(f"   {j+1:4d}: {line}")
        
        elif tag == 'delete':
            # Lines removed from original
            for i in range(i1, i2):
                line = original_lines[i]
                if search_term and search_term.lower() in line.lower():
                    line = line.replace(search_term, f"**{search_term}**")
                original_display.append(f"❌ {i+1:4d}: {line}")
        
        elif tag == 'insert':
            # Lines added to rendered
            for j in range(j1, j2):
                line = rendered_lines[j]
                # Highlight JavaScript additions
                prefix = "✅"
                if '<script' in line.lower() or 'javascript:' in line.lower():
                    prefix = "🔥 JS"
                elif '<meta' in line.lower():
                    prefix = "📝 META"
                
                if search_term and search_term.lower() in line.lower():
                    line = line.replace(search_term, f"**{search_term}**")
                rendered_display.append(f"{prefix} {j+1:4d}: {line}")
        
        elif tag == 'replace':
            # Lines modified
            for i in range(i1, i2):
                line = original_lines[i]
                if search_term and search_term.lower() in line.lower():
                    line = line.replace(search_term, f"**{search_term}**")
                original_display.append(f"🔄 {i+1:4d}: {line}")
            
            for j in range(j1, j2):
                line = rendered_lines[j]
                prefix = "🔄"
                if '<script' in line.lower() or 'javascript:' in line.lower():
                    prefix = "🔥 JS"
                elif '<meta' in line.lower():
                    prefix = "📝 META"
                
                if search_term and search_term.lower() in line.lower():
                    line = line.replace(search_term, f"**{search_term}**")
                rendered_display.append(f"{prefix} {j+1:4d}: {line}")
    
    # Display in two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Original HTML")
        if original_display:
            # Use text area for better display
            original_text = "\n".join(original_display)
            st.text_area(
                "Original HTML Content",
                original_text,
                height=400,
                key="original_html_display",
                label_visibility="collapsed"
            )
        else:
            st.info("No original HTML content to display")
    
    with col2:
        st.markdown("### Rendered HTML")
        if rendered_display:
            rendered_text = "\n".join(rendered_display)
            st.text_area(
                "Rendered HTML Content",
                rendered_text,
                height=400,
                key="rendered_html_display",
                label_visibility="collapsed"
            )
        else:
            st.info("No rendered HTML content to display")
    
    # Show unified diff as well
    with st.expander("📄 Unified Diff View", expanded=False):
        diff_lines = diff_analyzer.generate_diff()
        if diff_lines:
            diff_text = "\n".join(diff_lines)
            st.code(diff_text, language="diff")
        else:
            st.info("No differences found")
    
    return stats

def display_diff_insights(diff_analyzer):
    """Display detailed insights about the differences"""
    
    original_lines = diff_analyzer.original_lines
    rendered_lines = diff_analyzer.rendered_lines
    matcher = difflib.SequenceMatcher(None, original_lines, rendered_lines)
    
    # Categorize changes
    js_changes = []
    meta_changes = []
    content_changes = []
    other_changes = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ['insert', 'replace']:
            lines = rendered_lines[j1:j2] if tag == 'insert' else rendered_lines[j1:j2]
            
            for line in lines:
                line_lower = line.lower()
                if '<script' in line_lower or 'javascript:' in line_lower:
                    js_changes.append(line.strip())
                elif '<meta' in line_lower or 'og:' in line_lower or 'twitter:' in line_lower:
                    meta_changes.append(line.strip())
                elif any(tag_name in line_lower for tag_name in ['<div', '<span', '<p', '<h1', '<h2', '<h3']):
                    content_changes.append(line.strip())
                else:
                    other_changes.append(line.strip())
    
    # Display categorized changes
    if js_changes:
        with st.expander(f"🔥 JavaScript Changes ({len(js_changes)})", expanded=True):
            for i, change in enumerate(js_changes[:10], 1):
                st.code(change, language="html")
                if i >= 10 and len(js_changes) > 10:
                    st.info(f"... and {len(js_changes) - 10} more JavaScript changes")
                    break
    
    if meta_changes:
        with st.expander(f"📝 Metadata Changes ({len(meta_changes)})", expanded=False):
            for i, change in enumerate(meta_changes[:10], 1):
                st.code(change, language="html")
                if i >= 10 and len(meta_changes) > 10:
                    st.info(f"... and {len(meta_changes) - 10} more metadata changes")
                    break
    
    if content_changes:
        with st.expander(f"📄 Content Changes ({len(content_changes)})", expanded=False):
            for i, change in enumerate(content_changes[:5], 1):
                st.code(change, language="html")
                if i >= 5 and len(content_changes) > 5:
                    st.info(f"... and {len(content_changes) - 5} more content changes")
                    break
    
    if other_changes:
        with st.expander(f"🔧 Other Changes ({len(other_changes)})", expanded=False):
            for i, change in enumerate(other_changes[:5], 1):
                st.code(change, language="html")
                if i >= 5 and len(other_changes) > 5:
                    st.info(f"... and {len(other_changes) - 5} more changes")
                    break

def show_diff_viewer_tab(crawl_results):
    """Updated diff viewer tab that actually works in Streamlit"""
    
    st.subheader("HTML Diff Viewer")
    st.write("Compare original HTML with JavaScript-rendered HTML to see what changes after page load.")
    
    # URL selector
    urls_with_data = [r['url'] for r in crawl_results if r.get('raw_html') and r.get('rendered_html')]
    
    if urls_with_data:
        selected_url = st.selectbox(
            "Select URL to analyze:",
            urls_with_data,
            key="diff_url_selector"
        )
        
        if selected_url:
            # Find the result for this URL
            selected_result = next((r for r in crawl_results if r['url'] == selected_url), None)
            
            if selected_result and selected_result.get('raw_html') and selected_result.get('rendered_html'):
                # Controls
                col1, col2 = st.columns(2)
                
                with col1:
                    search_term = st.text_input("Search in HTML:", placeholder="Enter search term...")
                
                with col2:
                    show_only_changes = st.checkbox("Show only changes", False)
                
                # Create diff analyzer
                diff_analyzer = HTMLDiffAnalyzer(
                    selected_result['raw_html'],
                    selected_result['rendered_html']
                )
                
                # Display the working diff viewer
                stats = create_streamlit_diff_viewer(
                    diff_analyzer,
                    search_term=search_term,
                    show_only_changes=show_only_changes
                )
                
                # Show detailed insights
                st.subheader("Change Insights")
                display_diff_insights(diff_analyzer)
                
                # Export options
                st.subheader("Export Options")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.download_button(
                        "📥 Download Original HTML",
                        selected_result['raw_html'],
                        f"original_{selected_url.replace('https://', '').replace('/', '_')}.html",
                        mime="text/html"
                    )
                
                with col2:
                    st.download_button(
                        "📥 Download Rendered HTML",
                        selected_result['rendered_html'],
                        f"rendered_{selected_url.replace('https://', '').replace('/', '_')}.html",
                        mime="text/html"
                    )
                
                with col3:
                    diff_lines = diff_analyzer.generate_diff()
                    diff_text = '\n'.join(diff_lines)
                    st.download_button(
                        "📥 Download Diff Report",
                        diff_text,
                        f"diff_{selected_url.replace('https://', '').replace('/', '_')}.diff",
                        mime="text/plain"
                    )
            
            else:
                st.warning("HTML data not available for this URL. Please re-crawl to generate diff data.")
    
    else:
        st.info("No URLs with HTML diff data available. Please crawl some URLs first.")

# Sidebar Configuration
with st.sidebar:
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.header("🔧 Crawler Configuration")

    st.info("Concurrency is limited to 1 on this hosted version for stability. Run locally for more power.")
    concurrent_requests = 1  # Hardcoded for stability on Render

    # Basic settings
    st.subheader("Basic Settings")
    concurrent_requests = st.slider("Concurrent Requests", 1, 5, 3)
    page_timeout = st.slider("Page Timeout (seconds)", 5, 30, 10)
    js_wait_time = st.slider("JS Wait Time (seconds)", 1, 10, 3)
    
    # Advanced settings
    st.subheader("Advanced Options")
    follow_redirects = st.checkbox("Follow Redirects", True)
    check_images = st.checkbox("Analyze Images", False)
    check_links = st.checkbox("Check Internal Links", False)
    mobile_simulation = st.checkbox("Mobile Simulation", False)
    
    # Diff Viewer Options
    st.subheader("🔍 Diff Viewer Options")
    preserve_formatting = st.checkbox("Preserve HTML Formatting", True)
    show_line_numbers = st.checkbox("Show Line Numbers", True)
    highlight_js_changes = st.checkbox("Highlight JS Changes", True)
    context_lines = st.slider("Context Lines", 0, 10, 3)
    
    # Filtering
    st.subheader("Content Filtering")
    ignore_query_params = st.checkbox("Ignore Query Parameters", True)
    exclude_patterns = st.text_area("Exclude URL Patterns (one per line)", placeholder="admin/\n/wp-content/\n.pdf")
    
    # Export options
    st.subheader("Export Options")
    export_format = st.selectbox("Export Format", ["CSV", "Excel", "JSON"])
    
    st.markdown('</div>', unsafe_allow_html=True)

def analyze_page_speed(response_time, size_bytes):
    """Analyze page speed metrics"""
    speed_score = 100
    
    # Response time analysis
    if response_time > 3:
        speed_score -= 30
    elif response_time > 1:
        speed_score -= 15
    
    # Size analysis
    if size_bytes > 1024 * 1024:  # > 1MB
        speed_score -= 25
    elif size_bytes > 512 * 1024:  # > 512KB
        speed_score -= 10
    
    return max(0, speed_score)

def extract_seo_data(soup):
    """Extract SEO-relevant data from HTML"""
    seo_data = {
        'title': '',
        'meta_description': '',
        'h1_count': 0,
        'h2_count': 0,
        'images_without_alt': 0,
        'internal_links': 0,
        'external_links': 0,
        'word_count': 0,
        'canonical_url': '',
        'meta_robots': '',
        'og_title': '',
        'og_description': '',
        'schema_markup': False
    }
    
    if not soup:
        return seo_data
    
    # Title
    title_tag = soup.find('title')
    seo_data['title'] = title_tag.get_text().strip() if title_tag else ''
    
    # Meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    seo_data['meta_description'] = meta_desc.get('content', '') if meta_desc else ''
    
    # Headings
    seo_data['h1_count'] = len(soup.find_all('h1'))
    seo_data['h2_count'] = len(soup.find_all('h2'))
    
    # Images without alt
    images = soup.find_all('img')
    seo_data['images_without_alt'] = sum(1 for img in images if not img.get('alt'))
    
    # Word count
    text = soup.get_text()
    seo_data['word_count'] = len(text.split())
    
    # Links analysis
    links = soup.find_all('a', href=True)
    for link in links:
        href = link['href']
        if href.startswith('http'):
            seo_data['external_links'] += 1
        else:
            seo_data['internal_links'] += 1
    
    # Canonical URL
    canonical = soup.find('link', rel='canonical')
    seo_data['canonical_url'] = canonical.get('href', '') if canonical else ''
    
    # Meta robots
    robots = soup.find('meta', attrs={'name': 'robots'})
    seo_data['meta_robots'] = robots.get('content', '') if robots else ''
    
    # Open Graph
    og_title = soup.find('meta', property='og:title')
    seo_data['og_title'] = og_title.get('content', '') if og_title else ''
    
    og_desc = soup.find('meta', property='og:description')
    seo_data['og_description'] = og_desc.get('content', '') if og_desc else ''
    
    # Schema markup
    schema_scripts = soup.find_all('script', type='application/ld+json')
    seo_data['schema_markup'] = len(schema_scripts) > 0
    
    return seo_data

def detect_technologies(soup, response_headers):
    """Detect web technologies used"""
    technologies = []
    
    # JavaScript frameworks
    scripts = soup.find_all('script', src=True)
    for script in scripts:
        src = script.get('src', '').lower()
        if 'react' in src:
            technologies.append('React')
        elif 'vue' in src:
            technologies.append('Vue.js')
        elif 'angular' in src:
            technologies.append('Angular')
        elif 'jquery' in src:
            technologies.append('jQuery')
    
    # Server detection from headers
    server = response_headers.get('server', '').lower()
    if 'nginx' in server:
        technologies.append('Nginx')
    elif 'apache' in server:
        technologies.append('Apache')
    elif 'cloudflare' in server:
        technologies.append('Cloudflare')
    
    # CMS detection
    html_text = str(soup).lower()
    if 'wp-content' in html_text or 'wordpress' in html_text:
        technologies.append('WordPress')
    elif 'drupal' in html_text:
        technologies.append('Drupal')
    elif 'joomla' in html_text:
        technologies.append('Joomla')
    
    return technologies

def crawl_single_url(url, driver_manager, config):
    """Crawl a single URL and return comprehensive analysis including raw HTML"""
    start_time = time.time()
    result = {
        'url': url,
        'status_code': 0,
        'response_time': 0,
        'size_bytes': 0,
        'raw_html_size': 0,
        'rendered_html_size': 0,
        'js_additions': 0,
        'js_percentage': 0,
        'speed_score': 0,
        'seo_score': 0,
        'technologies': [],
        'is_spa': False,
        'spa_score': 0,
        'errors': [],
        'seo_data': {},
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'raw_html': '',  # Store raw HTML for diff
        'rendered_html': ''  # Store rendered HTML for diff
    }
    
    try:
        # Fetch raw HTML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        
        raw_response = requests.get(url, headers=headers, timeout=config['timeout'])
        # This will raise an HTTPError for 4xx or 5xx status codes, ensuring we stop processing failed URLs.
        raw_response.raise_for_status()

        raw_html = raw_response.text
        raw_response_time = time.time() - start_time
        
        result['status_code'] = raw_response.status_code
        result['response_time'] = raw_response_time
        result['size_bytes'] = len(raw_html.encode('utf-8'))
        result['raw_html_size'] = result['size_bytes']
        result['raw_html'] = raw_html  # Store for diff
        
        # Parse raw HTML
        raw_soup = BeautifulSoup(raw_html, 'html.parser')
        
        # Get rendered HTML using WebDriver
        driver = driver_manager.get_driver()
        rendered_html = ""
        
        if driver:
            try:
                driver.set_page_load_timeout(config['timeout'])
                driver.get(url)
                
                # Wait for page load
                WebDriverWait(driver, config['timeout']).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Wait for JavaScript
                time.sleep(config['js_wait'])
                
                rendered_html = driver.page_source
                result['rendered_html_size'] = len(rendered_html.encode('utf-8'))
                result['rendered_html'] = rendered_html  # Store for diff
                
            except Exception as e:
                result['errors'].append(f"Selenium error: {str(e)}")
        
        # Parse rendered HTML
        rendered_soup = BeautifulSoup(rendered_html, 'html.parser') if rendered_html else raw_soup
        
        # Calculate JavaScript impact
        if rendered_html:
            raw_lines = raw_html.count('\n')
            rendered_lines = rendered_html.count('\n')
            result['js_additions'] = max(0, rendered_lines - raw_lines)
            result['js_percentage'] = (result['js_additions'] / max(rendered_lines, 1)) * 100
        
        # Extract SEO data
        result['seo_data'] = extract_seo_data(rendered_soup)
        
        # Calculate SEO score
        seo_score = 100
        if not result['seo_data']['title']:
            seo_score -= 20
        if not result['seo_data']['meta_description']:
            seo_score -= 15
        if result['seo_data']['h1_count'] != 1:
            seo_score -= 10
        if result['seo_data']['images_without_alt'] > 0:
            seo_score -= 10
        
        result['seo_score'] = max(0, seo_score)
        
        # Detect technologies
        result['technologies'] = detect_technologies(rendered_soup, raw_response.headers)
        
        # SPA detection
        spa_indicators = 0
        if result['js_percentage'] > 30:
            spa_indicators += 30
        if any(tech in ['React', 'Vue.js', 'Angular'] for tech in result['technologies']):
            spa_indicators += 40
        if rendered_soup.find('div', {'id': ['root', 'app']}):
            spa_indicators += 30
        
        result['spa_score'] = spa_indicators
        result['is_spa'] = spa_indicators > 50
        
        # Speed score
        result['speed_score'] = analyze_page_speed(result['response_time'], result['size_bytes'])
        
    except Exception as e:
        result['errors'].append(f"General error: {str(e)}")
    
    result['response_time'] = time.time() - start_time
    return result

def parse_sitemap(sitemap_url):
    """Fetches and parses a sitemap URL to extract all contained URLs."""
    urls = []
    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        locs = soup.find_all('loc')
        urls = [loc.text for loc in locs]
        st.success(f"Found {len(urls)} URLs in sitemap.")
    except Exception as e:
        st.error(f"Failed to parse sitemap: {e}")
    return urls

# Main interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎯 URL Input")
    input_method = st.radio("Input Method", ["Single URL", "Multiple URLs", "Sitemap URL"])
    
    if input_method == "Single URL":
        url_input = st.text_input("Enter URL:", "https://example.com")
        urls_to_crawl = [url_input] if url_input.strip() else []
    
    elif input_method == "Multiple URLs":
        urls_text = st.text_area("Enter URLs (one per line):", height=150)
        urls_to_crawl = [url.strip() for url in urls_text.split('\n') if url.strip()]
    
    else:  # Sitemap
        sitemap_url = st.text_input("Sitemap URL:", "https://example.com/sitemap.xml")
        urls_to_crawl = []
        if sitemap_url and st.button("Fetch URLs from Sitemap"):
            urls_to_crawl = parse_sitemap(sitemap_url)

with col2:
    st.subheader("📊 Quick Stats")
    if st.session_state.crawl_results:
        total_crawled = len(st.session_state.crawl_results)
        avg_speed_score = sum(r.get('speed_score', 0) for r in st.session_state.crawl_results) / total_crawled
        avg_seo_score = sum(r.get('seo_score', 0) for r in st.session_state.crawl_results) / total_crawled
        spa_count = sum(1 for r in st.session_state.crawl_results if r.get('is_spa', False))
        
        st.metric("Total Crawled", total_crawled)
        st.metric("Avg Speed Score", f"{avg_speed_score:.1f}")
        st.metric("Avg SEO Score", f"{avg_seo_score:.1f}")
        st.metric("SPAs Detected", spa_count)

# Control buttons
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🚀 Start Crawl", type="primary", disabled=st.session_state.crawl_running):
        if urls_to_crawl:
            st.session_state.crawl_running = True
            st.rerun()

with col2:
    if st.button("⏹️ Stop Crawl", disabled=not st.session_state.crawl_running):
        st.session_state.crawl_running = False
        st.rerun()

with col3:
    if st.button("🗑️ Clear Results"):
        st.session_state.crawl_results = []
        if st.session_state.driver_manager:
            st.session_state.driver_manager.cleanup()
            st.session_state.driver_manager = None
        st.session_state.selected_url_for_diff = None
        st.rerun()

with col4:
    if st.session_state.crawl_results:
        # Prepare data for export
        df = pd.DataFrame(st.session_state.crawl_results)
        if export_format == "CSV":
            csv = df.to_csv(index=False)
            st.download_button("💾 Export CSV", csv, "crawl_results.csv", "text/csv")
        elif export_format == "Excel":
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Crawl Results')
            excel_data = output.getvalue()
            st.download_button("💾 Export Excel", excel_data, "crawl_results.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Crawling logic
if st.session_state.crawl_running and urls_to_crawl:
    if st.session_state.driver_manager is None:
        st.session_state.driver_manager = WebDriverManager()
    
    config = {
        'timeout': page_timeout,
        'js_wait': js_wait_time,
        'concurrent': concurrent_requests
    }
    
    progress_container = st.container()
    with progress_container:
        st.subheader("🔄 Crawling in Progress")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process URLs
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = []
            for i, url in enumerate(urls_to_crawl):
                if not st.session_state.crawl_running:
                    break
                    
                future = executor.submit(crawl_single_url, url, st.session_state.driver_manager, config)
                futures.append((future, url, i))
            
            # Collect results
            for future, url, index in futures:
                if not st.session_state.crawl_running:
                    break
                    
                try:
                    # Get the result from the future
                    result = future.result(timeout=page_timeout + 15)  # Increased timeout for safety
                    st.session_state.crawl_results.append(result)                    
                    progress = (index + 1) / len(urls_to_crawl)
                    progress_bar.progress(progress)
                    status_text.text(f"Processed: {url}")
                    
                except Exception as e:
                    # If the future failed, create a partial result to record the error
                    error_result = {'url': url, 'status_code': 'Error', 'errors': [str(e)]}
                    st.session_state.crawl_results.append(error_result)
                    st.warning(f"Failed to process {url}: {e}")  # Use warning for non-blocking errors
    
    # Cleanup
    if st.session_state.driver_manager:
        st.session_state.driver_manager.cleanup()
        st.session_state.driver_manager = None
    st.session_state.crawl_running = False
    st.success("🎉 Crawling completed!")
    st.rerun()

# Results Display
if st.session_state.crawl_results:
    st.header("📊 Crawl Results")
    
    # Add HTML Diff Viewer Tab
    result_tabs = st.tabs(["📋 Summary", "🔍 HTML Diff Viewer", "📈 Performance", "🕷️ JavaScript Impact", "🎯 SEO Analysis", "🔧 Technologies"])
    
    with result_tabs[0]:  # Summary tab
        # Summary metrics
        results_df = pd.DataFrame(st.session_state.crawl_results)
        
        # Key metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            success_rate = (results_df['status_code'] == 200).mean() * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        with col2:
            avg_response_time = results_df['response_time'].mean()
            st.metric("Avg Response Time", f"{avg_response_time:.2f}s")
        
        with col3:
            avg_size = results_df['size_bytes'].mean() / 1024
            st.metric("Avg Page Size", f"{avg_size:.1f} KB")
        
        with col4:
            avg_js_impact = results_df['js_percentage'].mean()
            st.metric("Avg JS Impact", f"{avg_js_impact:.1f}%")
        
        with col5:
            high_js_pages = (results_df['js_percentage'] > 50).sum()
            st.metric("High JS Pages", high_js_pages)
        
        # Detailed results table
        st.subheader("📋 Detailed Results")
        
        # Prepare display dataframe
        display_cols = ['url', 'status_code', 'response_time', 'size_bytes', 'js_percentage', 
                       'speed_score', 'seo_score', 'is_spa', 'technologies']
        
        display_df = results_df[display_cols].copy()
        display_df['response_time'] = display_df['response_time'].round(2)
        display_df['js_percentage'] = display_df['js_percentage'].round(1)
        display_df['size_bytes'] = (display_df['size_bytes'] / 1024).round(1)  # Convert to KB
        
        # Color coding for status
        def color_status(val):
            if val == 200:
                return 'background-color: #d4edda'
            elif 300 <= val < 400:
                return 'background-color: #fff3cd'
            else:
                return 'background-color: #f8d7da'
        
        styled_df = display_df.style.map(color_status, subset=['status_code'])
        st.dataframe(styled_df, use_container_width=True, height=400)
    
    with result_tabs[1]:  # HTML Diff Viewer tab
        show_diff_viewer_tab(st.session_state.crawl_results)
    
    with result_tabs[2]:  # Performance tab
        col1, col2 = st.columns(2)
        
        with col1:
            # Response time distribution
            fig = px.histogram(results_df, x='response_time', 
                             title='Response Time Distribution',
                             labels={'response_time': 'Response Time (seconds)'})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Speed score vs page size
            fig = px.scatter(results_df, x='size_bytes', y='speed_score',
                           title='Speed Score vs Page Size',
                           labels={'size_bytes': 'Page Size (bytes)', 'speed_score': 'Speed Score'})
            st.plotly_chart(fig, use_container_width=True)
    
    with result_tabs[3]:  # JavaScript Impact tab
        col1, col2 = st.columns(2)
        
        with col1:
            # JS impact distribution
            fig = px.histogram(results_df, x='js_percentage',
                             title='JavaScript Impact Distribution',
                             labels={'js_percentage': 'JS Impact (%)'})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # SPA detection
            spa_counts = results_df['is_spa'].value_counts()
            if len(spa_counts) > 0:
                spa_labels = []
                spa_values = []
                
                for is_spa, count in spa_counts.items():
                    if is_spa:
                        spa_labels.append('SPA')
                    else:
                        spa_labels.append('Traditional')
                    spa_values.append(count)
                
                fig = px.pie(values=spa_values, names=spa_labels,
                            title='SPA vs Traditional Pages')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No SPA data available")
    
    with result_tabs[4]:  # SEO Analysis tab
        col1, col2 = st.columns(2)
        
        with col1:
            # SEO score distribution
            fig = px.histogram(results_df, x='seo_score',
                             title='SEO Score Distribution',
                             labels={'seo_score': 'SEO Score'})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Title length analysis
            title_lengths = [len(r.get('seo_data', {}).get('title', '')) for r in st.session_state.crawl_results]
            fig = px.histogram(x=title_lengths, title='Title Length Distribution',
                             labels={'x': 'Title Length (characters)'})
            st.plotly_chart(fig, use_container_width=True)
    
    with result_tabs[5]:  # Technologies tab
        # Technology usage
        all_technologies = []
        for result in st.session_state.crawl_results:
            all_technologies.extend(result.get('technologies', []))
        
        if all_technologies:
            tech_counts = Counter(all_technologies)
            fig = px.bar(x=list(tech_counts.keys()), y=list(tech_counts.values()),
                        title='Technology Usage',
                        labels={'x': 'Technology', 'y': 'Usage Count'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No technologies detected in crawled pages")
    
    # Issue detection section
    st.header("⚠️ Issues Detected")
    
    issues = []
    for result in st.session_state.crawl_results:
        url = result['url']
        
        if result['status_code'] != 200:
            issues.append({'URL': url, 'Issue': f"HTTP {result['status_code']}", 'Severity': 'High'})
        
        if result['response_time'] > 3:
            issues.append({'URL': url, 'Issue': 'Slow response time', 'Severity': 'Medium'})
        
        if result['speed_score'] < 50:
            issues.append({'URL': url, 'Issue': 'Poor speed score', 'Severity': 'Medium'})
        
        if result['seo_score'] < 70:
            issues.append({'URL': url, 'Issue': 'SEO issues detected', 'Severity': 'Low'})
        
        seo_data = result.get('seo_data', {})
        if not seo_data.get('title'):
            issues.append({'URL': url, 'Issue': 'Missing title tag', 'Severity': 'High'})
        
        if not seo_data.get('meta_description'):
            issues.append({'URL': url, 'Issue': 'Missing meta description', 'Severity': 'Medium'})
        
        # Diff-specific issues
        if result.get('js_percentage', 0) > 80:
            issues.append({'URL': url, 'Issue': 'Excessive JavaScript modifications', 'Severity': 'Medium'})
    
    if issues:
        issues_df = pd.DataFrame(issues)
        
        # Color code by severity
        def color_severity(val):
            if val == 'High':
                return 'background-color: #f8d7da'
            elif val == 'Medium':
                return 'background-color: #fff3cd'
            else:
                return 'background-color: #cce5ff'
        
        styled_issues = issues_df.style.map(color_severity, subset=['Severity'])
        st.dataframe(styled_issues, use_container_width=True)
    else:
        st.success("🎉 No major issues detected!")

# Footer
st.markdown("---")
st.markdown("""
### 🚀 **Professional Features**
- **Advanced HTML Diff Viewer** with side-by-side comparison and change highlighting
- **Concurrent crawling** with WebDriver pooling for maximum speed
- **Comprehensive SEO analysis** including title tags, meta descriptions, headings
- **Technology detection** for frameworks and server technologies  
- **SPA identification** with confidence scoring
- **Performance metrics** with speed scoring algorithm
- **Issue detection** with severity levels
- **Professional visualizations** with interactive charts
- **Export capabilities** in multiple formats
- **Real-time diff analysis** with JavaScript injection detection

### 🔍 **HTML Diff Viewer Features**
- **Side-by-side comparison** of original vs rendered HTML
- **Syntax highlighting** with change categorization
- **Search functionality** within HTML content
- **Filter by change types** (JavaScript, Metadata, Content, etc.)
- **Export options** for original, rendered, and diff files
- **Detailed insights** grouped by change categories
- **Performance impact analysis** of JavaScript modifications

### 💡 **Pro Tips**
- Use **concurrent requests** (3-5) for faster crawling of multiple URLs
- Enable **mobile simulation** for mobile-first analysis
- Use **URL exclusion patterns** to skip irrelevant pages
- Monitor **JS percentage** to identify over-engineered pages
- Use the **HTML Diff Viewer** to understand JavaScript impact on page structure
- **Search within diffs** to find specific changes or elements
- **Export diff reports** for documentation and analysis
""")
