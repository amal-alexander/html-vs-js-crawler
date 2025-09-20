import streamlit as st
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager, ChromeType
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
import os
# Define a consistent, modern User-Agent to avoid being blocked
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


# Page configuration
st.set_page_config(
    page_title="HTML vs JS Crawler Pro - Screaming Frog Style",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🕷️"
)

# Enhanced CSS for better diff visualization
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
    
    /* Enhanced Diff Viewer Styles */
    .diff-container {
        display: flex;
        height: 600px;
        border: 1px solid #ddd;
        border-radius: 8px;
        overflow: hidden;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 13px;
        background: #f8f9fa;
    }
    
    .diff-panel {
        flex: 1;
        overflow: auto;
        padding: 15px;
        line-height: 1.6;
    }
    
    .diff-panel.original {
        background: #ffffff;
        border-right: 3px solid #667eea;
    }
    
    .diff-panel.rendered {
        background: #f8fbff;
    }
    
    .diff-header {
        position: sticky;
        top: 0;
        background: #667eea;
        color: white;
        padding: 10px 15px;
        font-weight: bold;
        font-size: 14px;
        margin: -15px -15px 15px -15px;
        border-bottom: 1px solid #5a67d8;
        z-index: 100;
    }
    
    .line-number {
        display: inline-block;
        width: 50px;
        color: #888;
        text-align: right;
        margin-right: 15px;
        user-select: none;
        border-right: 2px solid #e0e0e0;
        padding-right: 8px;
        font-size: 11px;
    }
    
    .line-content {
        white-space: pre-wrap;
        word-wrap: break-word;
        display: inline-block;
        width: calc(100% - 70px);
        vertical-align: top;
    }
    
    .line-added {
        background: linear-gradient(90deg, #d4edda 0%, #c3e6cb 100%);
        border-left: 4px solid #28a745;
        padding: 4px 8px;
        margin: 2px 0;
        border-radius: 4px;
    }
    
    .line-removed {
        background: linear-gradient(90deg, #f8d7da 0%, #f1aeb5 100%);
        border-left: 4px solid #dc3545;
        padding: 4px 8px;
        margin: 2px 0;
        border-radius: 4px;
    }
    
    .line-modified {
        background: linear-gradient(90deg, #fff3cd 0%, #ffeaa7 100%);
        border-left: 4px solid #ffc107;
        padding: 4px 8px;
        margin: 2px 0;
        border-radius: 4px;
    }
    
    .line-unchanged {
        opacity: 0.6;
        background: #fafafa;
        padding: 2px 8px;
        margin: 1px 0;
    }
    
    .js-injection {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 6px 10px;
        border-radius: 5px;
        font-weight: bold;
        margin: 5px 0;
        border-left: 5px solid #155724;
        box-shadow: 0 2px 4px rgba(40, 167, 69, 0.3);
    }
    
    .meta-injection {
        background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);
        color: #212529;
        padding: 6px 10px;
        border-radius: 5px;
        font-weight: bold;
        margin: 5px 0;
        border-left: 5px solid #856404;
        box-shadow: 0 2px 4px rgba(255, 193, 7, 0.3);
    }
    
    .css-injection {
        background: linear-gradient(135deg, #6f42c1 0%, #e83e8c 100%);
        color: white;
        padding: 6px 10px;
        border-radius: 5px;
        font-weight: bold;
        margin: 5px 0;
        border-left: 5px solid #4c2a85;
        box-shadow: 0 2px 4px rgba(111, 66, 193, 0.3);
    }
    
    .content-change {
        background: linear-gradient(135deg, #17a2b8 0%, #6610f2 100%);
        color: white;
        padding: 6px 10px;
        border-radius: 5px;
        font-weight: bold;
        margin: 5px 0;
        border-left: 5px solid #0c5460;
        box-shadow: 0 2px 4px rgba(23, 162, 184, 0.3);
    }
    
    .highlight-js-element {
        background: #28a745;
        color: white;
        padding: 2px 6px;
        border-radius: 3px;
        font-weight: bold;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    
    .highlight-meta-element {
        background: #ffc107;
        color: #212529;
        padding: 2px 6px;
        border-radius: 3px;
        font-weight: bold;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    
    .highlight-css-element {
        background: #6f42c1;
        color: white;
        padding: 2px 6px;
        border-radius: 3px;
        font-weight: bold;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    
    .search-highlight {
        background: #ffff00;
        padding: 1px 3px;
        border-radius: 2px;
        font-weight: bold;
    }
    
    .diff-stats {
        display: flex;
        gap: 20px;
        padding: 15px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .diff-stat {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 5px;
        padding: 10px;
        background: white;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        min-width: 80px;
    }
    
    .diff-stat-value {
        font-size: 24px;
        font-weight: bold;
    }
    
    .diff-stat-label {
        font-size: 12px;
        color: #666;
        text-align: center;
    }
    
    .diff-stat.added .diff-stat-value { color: #28a745; }
    .diff-stat.removed .diff-stat-value { color: #dc3545; }
    .diff-stat.modified .diff-stat-value { color: #ffc107; }
    .diff-stat.js .diff-stat-value { color: #28a745; }
    .diff-stat.similarity .diff-stat-value { color: #17a2b8; }
    
    .change-summary {
        background: white;
        padding: 20px;
        border-radius: 8px;
        margin: 20px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .change-item {
        padding: 10px;
        margin: 8px 0;
        border-radius: 6px;
        border-left: 4px solid #ddd;
    }
    
    .change-item.js-change {
        background: #d4edda;
        border-left-color: #28a745;
    }
    
    .change-item.meta-change {
        background: #fff3cd;
        border-left-color: #ffc107;
    }
    
    .change-item.css-change {
        background: #e2d9f3;
        border-left-color: #6f42c1;
    }
    
    .change-item.content-change {
        background: #d1ecf1;
        border-left-color: #17a2b8;
    }
    
    .injection-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
        margin-right: 8px;
    }
    
    .injection-badge.js {
        background: #28a745;
        color: white;
    }
    
    .injection-badge.meta {
        background: #ffc107;
        color: #212529;
    }
    
    .injection-badge.css {
        background: #6f42c1;
        color: white;
    }
    
    .filter-controls {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
        flex-wrap: wrap;
        padding: 15px;
        background: #f8f9fa;
        border-radius: 8px;
    }
    
    .filter-button {
        padding: 8px 15px;
        border: 2px solid #ddd;
        border-radius: 20px;
        background: white;
        cursor: pointer;
        font-size: 12px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .filter-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .filter-button.active {
        background: #667eea;
        color: white;
        border-color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<div class="main-header"><h1>🕷️ HTML vs JS Crawler Pro</h1><p>Professional-grade website analysis tool with enhanced JavaScript injection detection</p></div>', unsafe_allow_html=True)

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
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--window-size=1920,1080")
            options.add_argument(f"user-agent={USER_AGENT}")
            
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)

            # For Streamlit Cloud, Chrome is installed by setup.sh
            if os.path.exists("/usr/bin/google-chrome-stable"):
                st.info("Chrome binary found. Using system-installed Chrome.")
                options.binary_location = "/usr/bin/google-chrome-stable"
                # webdriver-manager will find the corresponding chromedriver
                service = ChromeService(ChromeDriverManager().install())
            else:
                # For local development, fall back to webdriver-manager.
                st.info("System Chrome not found. Using webdriver-manager to download Chromium.")
                service = ChromeService(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())

            driver = webdriver.Chrome(service=service, options=options)
            st.success("WebDriver initialized successfully.")
            return driver

        except Exception as e:
            st.error(f"Fatal Error: Failed to create WebDriver. The service may not be able to run. Error: {e}")
            st.stop()

    def cleanup(self):
        with self._lock:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    st.warning(f"Error while quitting WebDriver: {e}")
                finally:
                    self.driver = None

class EnhancedHTMLDiffAnalyzer:
    def __init__(self, original_html, rendered_html):
        self.original_html = original_html
        self.rendered_html = rendered_html
        self.original_soup = BeautifulSoup(original_html, 'html.parser') if original_html else None
        self.rendered_soup = BeautifulSoup(rendered_html, 'html.parser') if rendered_html else None
        self.original_lines = self._clean_html(original_html).splitlines()
        self.rendered_lines = self._clean_html(rendered_html).splitlines()
        
    def _clean_html(self, html_content):
        """Clean and format HTML for better diff comparison"""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.prettify()
    
    def detect_javascript_injections(self):
        """Detect JavaScript elements that were added during rendering"""
        injections = []
        
        if not self.original_soup or not self.rendered_soup:
            return injections
            
        # Find script tags
        original_scripts = set()
        rendered_scripts = set()
        
        for script in self.original_soup.find_all('script'):
            script_content = str(script)
            original_scripts.add(script_content)
            
        for script in self.rendered_soup.find_all('script'):
            script_content = str(script)
            rendered_scripts.add(script_content)
            if script_content not in original_scripts:
                injections.append({
                    'type': 'javascript',
                    'element': 'script',
                    'content': script_content[:200] + '...' if len(script_content) > 200 else script_content,
                    'full_content': script_content,
                    'src': script.get('src', 'inline'),
                    'description': f"Script tag {'with src: ' + script.get('src') if script.get('src') else 'with inline code'}"
                })
        
        # Find inline JavaScript (onclick, onload, etc.)
        js_attributes = ['onclick', 'onload', 'onmouseover', 'onmouseout', 'onchange', 'onsubmit']
        
        for attr in js_attributes:
            original_elements = self.original_soup.find_all(attrs={attr: True}) if self.original_soup else []
            rendered_elements = self.rendered_soup.find_all(attrs={attr: True}) if self.rendered_soup else []
            
            original_js = {elem.get(attr) for elem in original_elements}
            
            for elem in rendered_elements:
                js_code = elem.get(attr)
                if js_code and js_code not in original_js:
                    injections.append({
                        'type': 'javascript',
                        'element': elem.name,
                        'content': f'{attr}="{js_code}"',
                        'full_content': str(elem),
                        'src': 'inline_attribute',
                        'description': f"JavaScript in {attr} attribute on {elem.name} element"
                    })
        
        return injections
    
    def detect_meta_changes(self):
        """Detect meta tag changes"""
        changes = []
        
        if not self.original_soup or not self.rendered_soup:
            return changes
            
        original_metas = {str(meta) for meta in self.original_soup.find_all('meta')}
        rendered_metas = {str(meta) for meta in self.rendered_soup.find_all('meta')}
        
        # New meta tags
        for meta_str in rendered_metas - original_metas:
            meta = BeautifulSoup(meta_str, 'html.parser').find('meta')
            changes.append({
                'type': 'metadata',
                'element': 'meta',
                'content': meta_str,
                'full_content': meta_str,
                'name': meta.get('name', meta.get('property', 'unknown')),
                'description': f"Meta tag: {meta.get('name', meta.get('property', 'unknown'))}"
            })
            
        return changes
    
    def detect_css_changes(self):
        """Detect CSS/style changes"""
        changes = []
        
        if not self.original_soup or not self.rendered_soup:
            return changes
            
        # Style tags
        original_styles = {str(style) for style in self.original_soup.find_all('style')}
        rendered_styles = {str(style) for style in self.rendered_soup.find_all('style')}
        
        for style_str in rendered_styles - original_styles:
            changes.append({
                'type': 'stylesheet',
                'element': 'style',
                'content': style_str[:200] + '...' if len(style_str) > 200 else style_str,
                'full_content': style_str,
                'description': "Inline CSS styles"
            })
            
        # Link tags for CSS
        original_links = {str(link) for link in self.original_soup.find_all('link', rel='stylesheet')}
        rendered_links = {str(link) for link in self.rendered_soup.find_all('link', rel='stylesheet')}
        
        for link_str in rendered_links - original_links:
            link = BeautifulSoup(link_str, 'html.parser').find('link')
            changes.append({
                'type': 'stylesheet',
                'element': 'link',
                'content': link_str,
                'full_content': link_str,
                'href': link.get('href', ''),
                'description': f"CSS link: {link.get('href', '')}"
            })
            
        return changes
    
    def get_enhanced_statistics(self):
        """Get comprehensive statistics about changes"""
        stats = {
            'total_lines_original': len(self.original_lines),
            'total_lines_rendered': len(self.rendered_lines),
            'lines_added': 0,
            'lines_removed': 0,
            'lines_modified': 0,
            'similarity_ratio': 0,
            'js_injections': 0,
            'meta_changes': 0,
            'css_changes': 0,
            'content_changes': 0
        }
        
        if not self.original_lines and not self.rendered_lines:
            return stats
            
        matcher = difflib.SequenceMatcher(None, self.original_lines, self.rendered_lines)
        stats['similarity_ratio'] = matcher.ratio()
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                stats['lines_added'] += (j2 - j1)
            elif tag == 'delete':
                stats['lines_removed'] += (i2 - i1)
            elif tag == 'replace':
                stats['lines_modified'] += max(i2 - i1, j2 - j1)
        
        # Count injections
        js_injections = self.detect_javascript_injections()
        meta_changes = self.detect_meta_changes()
        css_changes = self.detect_css_changes()
        
        stats['js_injections'] = len(js_injections)
        stats['meta_changes'] = len(meta_changes)
        stats['css_changes'] = len(css_changes)
        
        return stats

def create_enhanced_diff_viewer(diff_analyzer, search_term="", show_only_changes=False):
    """Create enhanced HTML diff viewer with JavaScript injection highlighting"""
    
    stats = diff_analyzer.get_enhanced_statistics()
    js_injections = diff_analyzer.detect_javascript_injections()
    meta_changes = diff_analyzer.detect_meta_changes()
    css_changes = diff_analyzer.detect_css_changes()
    
    # Stats HTML with enhanced styling
    stats_html = f"""
    <div class="diff-stats">
        <div class="diff-stat">
            <div class="diff-stat-value">{stats['total_lines_original']} → {stats['total_lines_rendered']}</div>
            <div class="diff-stat-label">Total Lines</div>
        </div>
        <div class="diff-stat added">
            <div class="diff-stat-value">{stats['lines_added']}</div>
            <div class="diff-stat-label">Lines Added</div>
        </div>
        <div class="diff-stat removed">
            <div class="diff-stat-value">{stats['lines_removed']}</div>
            <div class="diff-stat-label">Lines Removed</div>
        </div>
        <div class="diff-stat modified">
            <div class="diff-stat-value">{stats['lines_modified']}</div>
            <div class="diff-stat-label">Lines Modified</div>
        </div>
        <div class="diff-stat js">
            <div class="diff-stat-value">{stats['js_injections']}</div>
            <div class="diff-stat-label">JS Injections</div>
        </div>
        <div class="diff-stat">
            <div class="diff-stat-value">{stats['meta_changes']}</div>
            <div class="diff-stat-label">Meta Changes</div>
        </div>
        <div class="diff-stat similarity">
            <div class="diff-stat-value">{stats['similarity_ratio']:.1%}</div>
            <div class="diff-stat-label">Similarity</div>
        </div>
    </div>
    """
    
    # Create side-by-side comparison
    original_lines = diff_analyzer.original_lines
    rendered_lines = diff_analyzer.rendered_lines
    
    matcher = difflib.SequenceMatcher(None, original_lines, rendered_lines)
    
    original_html = []
    rendered_html = []
    
    # Track JavaScript and meta injections for highlighting
    js_injection_lines = set()
    meta_injection_lines = set()
    css_injection_lines = set()
    
    # Find lines that contain injections
    for injection in js_injections:
        for i, line in enumerate(rendered_lines):
            if injection['element'] in line.lower() and ('script' in line.lower() or injection['src'] in line):
                js_injection_lines.add(i)
    
    for change in meta_changes:
        for i, line in enumerate(rendered_lines):
            if 'meta' in line.lower() and change['name'].lower() in line.lower():
                meta_injection_lines.add(i)
                
    for change in css_changes:
        for i, line in enumerate(rendered_lines):
            if 'style' in line.lower() or ('link' in line.lower() and 'css' in line.lower()):
                css_injection_lines.add(i)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            if not show_only_changes:
                for i in range(i1, i2):
                    line = html.escape(original_lines[i])
                    if search_term and search_term.lower() in line.lower():
                        line = line.replace(search_term, f'<span class="search-highlight">{search_term}</span>')
                    original_html.append(f'<div class="line-unchanged"><span class="line-number">{i+1}</span><span class="line-content">{line}</span></div>')
                
                for j in range(j1, j2):
                    line = html.escape(rendered_lines[j])
                    if search_term and search_term.lower() in line.lower():
                        line = line.replace(search_term, f'<span class="search-highlight">{search_term}</span>')
                    rendered_html.append(f'<div class="line-unchanged"><span class="line-number">{j+1}</span><span class="line-content">{line}</span></div>')
        
        elif tag == 'delete':
            for i in range(i1, i2):
                line = html.escape(original_lines[i])
                if search_term and search_term.lower() in line.lower():
                    line = line.replace(search_term, f'<span class="search-highlight">{search_term}</span>')
                original_html.append(f'<div class="line-removed"><span class="line-number">{i+1}</span><span class="line-content">- {line}</span></div>')
        
        elif tag == 'insert':
            for j in range(j1, j2):
                line = html.escape(rendered_lines[j])
                line_class = "line-added"
                
                # Enhanced highlighting for different types of injections
                if j in js_injection_lines:
                    line_class = "js-injection"
                    line = f'<span class="highlight-js-element">🟢 JS INJECTION</span> {line}'
                elif j in meta_injection_lines:
                    line_class = "meta-injection"
                    line = f'<span class="highlight-meta-element">🟡 META TAG</span> {line}'
                elif j in css_injection_lines:
                    line_class = "css-injection"
                    line = f'<span class="highlight-css-element">🟣 CSS</span> {line}'
                elif '<script' in line.lower():
                    line_class = "js-injection"
                    line = f'<span class="highlight-js-element">🟢 SCRIPT</span> {line}'
                elif '<meta' in line.lower():
                    line_class = "meta-injection"
                    line = f'<span class="highlight-meta-element">🟡 META</span> {line}'
                elif 'style' in line.lower() or ('link' in line.lower() and 'css' in line.lower()):
                    line_class = "css-injection"
                    line = f'<span class="highlight-css-element">🟣 STYLE</span> {line}'
                
                if search_term and search_term.lower() in line.lower():
                    line = line.replace(search_term, f'<span class="search-highlight">{search_term}</span>')
                    
                rendered_html.append(f'<div class="{line_class}"><span class="line-number">{j+1}</span><span class="line-content">+ {line}</span></div>')
        
        elif tag == 'replace':
            for i in range(i1, i2):
                line = html.escape(original_lines[i])
                if search_term and search_term.lower() in line.lower():
                    line = line.replace(search_term, f'<span class="search-highlight">{search_term}</span>')
                original_html.append(f'<div class="line-modified"><span class="line-number">{i+1}</span><span class="line-content">~ {line}</span></div>')
            
            for j in range(j1, j2):
                line = html.escape(rendered_lines[j])
                line_class = "line-modified"
                
                # Enhanced highlighting for replacements
                if j in js_injection_lines:
                    line_class = "js-injection"
                    line = f'<span class="highlight-js-element">🟢 JS MODIFIED</span> {line}'
                elif j in meta_injection_lines:
                    line_class = "meta-injection"
                    line = f'<span class="highlight-meta-element">🟡 META MODIFIED</span> {line}'
                elif j in css_injection_lines:
                    line_class = "css-injection"
                    line = f'<span class="highlight-css-element">🟣 CSS MODIFIED</span> {line}'
                elif '<script' in line.lower():
                    line_class = "js-injection"
                    line = f'<span class="highlight-js-element">🟢 SCRIPT MOD</span> {line}'
                elif '<meta' in line.lower():
                    line_class = "meta-injection"
                    line = f'<span class="highlight-meta-element">🟡 META MOD</span> {line}'
                elif 'style' in line.lower():
                    line_class = "css-injection"
                    line = f'<span class="highlight-css-element">🟣 STYLE MOD</span> {line}'
                
                if search_term and search_term.lower() in line.lower():
                    line = line.replace(search_term, f'<span class="search-highlight">{search_term}</span>')
                    
                rendered_html.append(f'<div class="{line_class}"><span class="line-number">{j+1}</span><span class="line-content">~ {line}</span></div>')
    
    # Complete HTML
    complete_html = f"""
    {stats_html}
    <div class="diff-container">
        <div class="diff-panel original">
            <div class="diff-header">
                Original HTML ({len(original_lines)} lines)
            </div>
            {''.join(original_html)}
        </div>
        <div class="diff-panel rendered">
            <div class="diff-header">
                Rendered HTML ({len(rendered_lines)} lines) - JS Injections Highlighted
            </div>
            {''.join(rendered_html)}
        </div>
    </div>
    """
    
    return complete_html, js_injections, meta_changes, css_changes

# Sidebar Configuration
with st.sidebar:
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.header("🔧 Crawler Configuration")

    st.info("Concurrency is limited to 1 on this hosted version for stability. Run locally for more power.")
    concurrent_requests = 1

    # Basic settings
    st.subheader("Basic Settings")
    page_timeout = st.slider("Page Timeout (seconds)", 5, 30, 10)
    enable_js_rendering = st.checkbox("Enable JavaScript Rendering", True, help="Enable to render JavaScript using a headless browser. Disabling this will only fetch the initial HTML and will be much faster.")
    js_wait_time = st.slider("JS Wait Time (seconds)", 1, 10, 3)
    
    # Advanced settings
    st.subheader("Advanced Options")
    follow_redirects = st.checkbox("Follow Redirects", True)
    check_images = st.checkbox("Analyze Images", False)
    check_links = st.checkbox("Check Internal Links", False)
    mobile_simulation = st.checkbox("Mobile Simulation", False)
    
    # Enhanced Diff Viewer Options
    st.subheader("🔍 Enhanced Diff Viewer")
    preserve_formatting = st.checkbox("Preserve HTML Formatting", True)
    show_line_numbers = st.checkbox("Show Line Numbers", True)
    highlight_js_changes = st.checkbox("Highlight JS Injections", True)
    highlight_meta_changes = st.checkbox("Highlight Meta Changes", True)
    highlight_css_changes = st.checkbox("Highlight CSS Changes", True)
    context_lines = st.slider("Context Lines", 0, 10, 3)
    
    # Filtering
    st.subheader("Content Filtering")
    ignore_query_params = st.checkbox("Ignore Query Parameters", True)
    exclude_patterns = st.text_area("Exclude URL Patterns (one per line)", placeholder="admin/\n/wp-content/\n.pdf")
    
    # Export options
    st.subheader("Export Options")
    export_format = st.selectbox("Export Format", ["CSV", "Excel", "JSON", "Issues (CSV)"])
    
    st.markdown('</div>', unsafe_allow_html=True)

def analyze_page_speed(response_time, size_bytes):
    """Analyze page speed metrics"""
    speed_score = 100
    
    if response_time > 3:
        speed_score -= 30
    elif response_time > 1:
        speed_score -= 15
    
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
        'raw_html': '',
        'rendered_html': ''
    }

    raw_html = ""
    rendered_html = ""
    raw_response = None # To store the response from requests
    use_selenium_for_all = False

    # --- Step 1: Attempt to fetch with Requests (fast path) ---
    try:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.9', 'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Ch-Ua-Platform': '"Windows"', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none', 'Sec-Fetch-User': '?1', 'Upgrade-Insecure-Requests': '1', 'User-Agent': USER_AGENT,
        }
        
        raw_response = requests.get(url, headers=headers, timeout=config['timeout'])
        result['status_code'] = raw_response.status_code
        raw_response.raise_for_status()
        raw_html = raw_response.text

    except requests.exceptions.HTTPError as e:
        result['status_code'] = e.response.status_code
        result['errors'].append(f"Request failed with status {e.response.status_code}. Falling back to full Selenium mode.")
        use_selenium_for_all = True
    except requests.exceptions.RequestException as e:
        result['errors'].append(f"Request failed: {str(e)}. Falling back to full Selenium mode.")
        use_selenium_for_all = True

    # --- Step 2: Fetch with Selenium (if needed or enabled) ---
    if config.get('enable_js', True):
        try:
            driver = driver_manager.get_driver()
            if not driver:
                raise WebDriverException("Failed to get a WebDriver instance.")

            # If requests failed, we must use Selenium for everything.
            # If requests succeeded, we still use Selenium for the rendered view.
            driver.set_page_load_timeout(config['timeout'])
            driver.get(url)

            # If requests failed, Selenium's initial load is our "raw" HTML
            if use_selenium_for_all:
                raw_html = driver.page_source
                result['status_code'] = 200 # Assume success if Selenium loads it

            # Wait for JS execution
            WebDriverWait(driver, config['timeout']).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(config['js_wait'])
            
            # Get the final, rendered HTML
            rendered_html = driver.page_source

        except (WebDriverException, TimeoutException) as e:
            result['errors'].append(f"Selenium processing failed: {str(e)}")
            # If Selenium fails, we can't proceed with rendering.
            # We might still have raw_html from requests, so we don't return yet.
            rendered_html = raw_html # Fallback to raw_html if rendering fails
        except Exception as e:
            result['errors'].append(f"An unexpected error occurred during Selenium processing: {str(e)}")
            rendered_html = raw_html
    else:
        # If JS is disabled, rendered is the same as raw
        rendered_html = raw_html

    # --- Step 3: Populate results and Analyze ---
    result['raw_html'] = raw_html
    result['rendered_html'] = rendered_html
    result['raw_html_size'] = len(raw_html.encode('utf-8'))
    result['rendered_html_size'] = len(rendered_html.encode('utf-8'))
    result['size_bytes'] = result['raw_html_size'] # Base size on initial load

    # If we failed to get any HTML at all, return early.
    if not raw_html and not rendered_html:
        result['response_time'] = time.time() - start_time
        return result
        
    try:
        rendered_soup = BeautifulSoup(rendered_html, 'html.parser')
        
        # Calculate JavaScript impact
        if raw_html and rendered_html:
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
        if raw_response:
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
        result['errors'].append(f"Processing error during analysis: {str(e)}")
    
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
            st.download_button("💾 Export Results (CSV)", csv, "crawl_results.csv", "text/csv")
        
        elif export_format == "Excel":
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Crawl Results')
            excel_data = output.getvalue()
            st.download_button("💾 Export Results (Excel)", excel_data, "crawl_results.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        elif export_format == "JSON":
            json_data = df.to_json(orient='records', indent=4)
            st.download_button("💾 Export Results (JSON)", json_data, "crawl_results.json", "application/json")
            
        elif export_format == "Issues (CSV)":
            issues = []
            for r in st.session_state.crawl_results:
                url = r['url']
                if r.get('status_code') != 200:
                    issues.append({'URL': url, 'Issue': f"HTTP Status {r.get('status_code', 'N/A')}", 'Severity': 'High'})
                if r.get('response_time', 0) > 3:
                    issues.append({'URL': url, 'Issue': f"Slow response: {r.get('response_time', 0):.2f}s", 'Severity': 'Medium'})
                
                seo_data = r.get('seo_data', {})
                if not seo_data.get('title'):
                    issues.append({'URL': url, 'Issue': 'Missing title tag', 'Severity': 'High'})
                if not seo_data.get('meta_description'):
                    issues.append({'URL': url, 'Issue': 'Missing meta description', 'Severity': 'Medium'})
                if seo_data.get('h1_count', 0) != 1:
                    issues.append({'URL': url, 'Issue': f"Incorrect H1 count: {seo_data.get('h1_count', 0)}", 'Severity': 'Low'})
                if r.get('js_percentage', 0) > 80:
                    issues.append({'URL': url, 'Issue': f"Excessive JS modification: {r.get('js_percentage', 0):.1f}%", 'Severity': 'Medium'})
            
            if issues:
                issues_df = pd.DataFrame(issues)
                issues_csv = issues_df.to_csv(index=False)
                st.download_button("💾 Export Issues (CSV)", issues_csv, "crawl_issues.csv", "text/csv")
            else:
                st.download_button("💾 Export Issues (CSV)", "No issues found.", "crawl_issues.csv", "text/csv", disabled=True)

# Crawling logic
if st.session_state.crawl_running and urls_to_crawl:
    if st.session_state.driver_manager is None:
        st.session_state.driver_manager = WebDriverManager()
    
    config = {
        'timeout': page_timeout,
        'js_wait': js_wait_time,
        'enable_js': enable_js_rendering,
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
                    result = future.result(timeout=page_timeout + 15)
                    st.session_state.crawl_results.append(result)                    
                    progress = (index + 1) / len(urls_to_crawl)
                    progress_bar.progress(progress)
                    status_text.text(f"Processed: {url}")
                    
                except Exception as e:
                    error_result = {'url': url, 'status_code': 'Error', 'errors': [str(e)]}
                    st.session_state.crawl_results.append(error_result)
                    st.warning(f"Failed to process {url}: {e}")
    
    # Cleanup
    if st.session_state.driver_manager:
        st.session_state.driver_manager.cleanup()
        st.session_state.driver_manager = None
    st.session_state.crawl_running = False
    st.success("🎉 Crawling completed!")
    st.rerun()

# Results Display
if st.session_state.crawl_results:
    st.header("📊 Crawl Results & Analysis")
    
    results_df = pd.DataFrame(st.session_state.crawl_results)
    
    result_tabs = st.tabs([
        "📋 Summary", 
        "🔍 Enhanced HTML Diff Viewer", 
        "📈 Performance", 
        "🕷️ JavaScript Impact", 
        "🎯 SEO Analysis", 
        "🔧 Technologies",
        "⚠️ Issues Detected"
    ])
    
    with result_tabs[0]:  # Summary tab
        st.subheader("Crawl Summary")
        display_cols = ['url', 'status_code', 'response_time', 'size_bytes', 'js_percentage', 
                       'speed_score', 'seo_score', 'is_spa', 'technologies']
        
        display_df = results_df[[col for col in display_cols if col in results_df.columns]].copy()
        if 'response_time' in display_df:
            display_df['response_time'] = display_df['response_time'].round(2)
        if 'js_percentage' in display_df:
            display_df['js_percentage'] = display_df['js_percentage'].round(1)
        if 'size_bytes' in display_df:
            display_df['size_bytes'] = (display_df['size_bytes'] / 1024).round(1)
        
        def color_status(val):
            if val == 200: return 'background-color: #d4edda'
            elif isinstance(val, int) and 300 <= val < 400: return 'background-color: #fff3cd'
            else: return 'background-color: #f8d7da'
        
        if 'status_code' in display_df:
            styled_df = display_df.style.map(color_status, subset=['status_code'])
            st.dataframe(styled_df, use_container_width=True, height=400)
        else:
            st.dataframe(display_df, use_container_width=True, height=400)

    with result_tabs[1]:  # Enhanced HTML Diff Viewer tab
        st.subheader("🔍 Enhanced HTML Diff Viewer")
        st.write("Compare original HTML with JavaScript-rendered HTML to see what changes after page load, with a focus on injections.")
        
        urls_with_data = [r['url'] for r in st.session_state.crawl_results if r.get('raw_html')]
        
        if urls_with_data:
            selected_url = st.selectbox("Select URL to analyze:", urls_with_data, key="diff_url_selector")
            
            if selected_url:
                selected_result = next((r for r in st.session_state.crawl_results if r['url'] == selected_url), None)
                
                if selected_result and selected_result.get('raw_html'):
                    rendered_html_for_diff = selected_result.get('rendered_html', '')
                    
                    col1, col2 = st.columns([2,1])
                    with col1:
                        search_term = st.text_input("🔍 Search in HTML:", placeholder="Enter search term...")
                    with col2:
                        show_only_changes = st.checkbox("Show only changes", False)

                    diff_analyzer = EnhancedHTMLDiffAnalyzer(selected_result['raw_html'], rendered_html_for_diff)
                    
                    st.subheader("🔄 Side-by-Side HTML Comparison")
                    if not rendered_html_for_diff:
                        st.warning("Rendered HTML is not available for this URL. Displaying raw HTML vs. empty content.")
                    
                    diff_html, js_injections, meta_changes, css_changes = create_enhanced_diff_viewer(
                        diff_analyzer,
                        search_term=search_term,
                        show_only_changes=show_only_changes
                    )
                    
                    st.markdown(diff_html, unsafe_allow_html=True)
                    
                    st.subheader("💡 Injection & Change Summary")
                    if not any([js_injections, meta_changes, css_changes]):
                        st.info("No significant JavaScript, meta, or CSS injections were detected.")
                    else:
                        if js_injections:
                            with st.expander(f"🟢 JavaScript Injections ({len(js_injections)})", expanded=True):
                                for item in js_injections:
                                    st.markdown(f"""
                                    <div class="change-item js-change">
                                        <span class="injection-badge js">JS</span>
                                        <strong>{item['description']}</strong>
                                        <pre><code>{html.escape(item['content'])}</code></pre>
                                    </div>
                                    """, unsafe_allow_html=True)
                        if meta_changes:
                            with st.expander(f"🟡 Meta Tag Changes ({len(meta_changes)})"):
                                for item in meta_changes:
                                    st.markdown(f"""
                                    <div class="change-item meta-change">
                                        <span class="injection-badge meta">META</span>
                                        <strong>{item['description']}</strong>
                                        <pre><code>{html.escape(item['content'])}</code></pre>
                                    </div>
                                    """, unsafe_allow_html=True)
                        if css_changes:
                            with st.expander(f"🟣 CSS & Style Changes ({len(css_changes)})"):
                                for item in css_changes:
                                    st.markdown(f"""
                                    <div class="change-item css-change">
                                        <span class="injection-badge css">CSS</span>
                                        <strong>{item['description']}</strong>
                                        <pre><code>{html.escape(item['content'])}</code></pre>
                                    </div>
                                    """, unsafe_allow_html=True)
                else:
                    st.warning("Raw HTML data not available for this URL. Please re-crawl to generate diff data.")
        else:
            st.info("No URLs with HTML diff data available. Please crawl some URLs first.")

    with result_tabs[2]:  # Performance tab
        st.subheader("Performance Analysis")
        if not results_df.empty and 'response_time' in results_df.columns:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.histogram(results_df, x='response_time', title='Response Time Distribution', labels={'response_time': 'Response Time (s)'})
                st.plotly_chart(fig, width='stretch')
            with col2:
                fig = px.scatter(results_df, x='size_bytes', y='speed_score', title='Speed Score vs. Page Size', labels={'size_bytes': 'Page Size (bytes)', 'speed_score': 'Speed Score'})
                st.plotly_chart(fig, width='stretch')
        else:
            st.info("No performance data to display.")

    with result_tabs[3]:  # JavaScript Impact tab
        st.subheader("JavaScript Impact Analysis")
        if not results_df.empty and 'js_percentage' in results_df.columns:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.histogram(results_df, x='js_percentage', title='JavaScript Impact Distribution', labels={'js_percentage': 'JS Impact (%)'})
                st.plotly_chart(fig, width='stretch')
            with col2:
                if 'is_spa' in results_df.columns:
                    spa_counts = results_df['is_spa'].value_counts().reset_index()
                    spa_counts.columns = ['is_spa', 'count']
                    spa_counts['label'] = spa_counts['is_spa'].apply(lambda x: 'SPA' if x else 'Traditional')
                    fig = px.pie(spa_counts, values='count', names='label', title='SPA vs. Traditional Pages')
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.info("No SPA data to display.")
        else:
            st.info("No JavaScript impact data to display.")

    with result_tabs[4]:  # SEO Analysis tab
        st.subheader("SEO Analysis")
        if not results_df.empty and 'seo_score' in results_df.columns:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.histogram(results_df, x='seo_score', title='SEO Score Distribution', labels={'seo_score': 'SEO Score'})
                st.plotly_chart(fig, width='stretch')
            with col2:
                title_lengths = [len(r.get('seo_data', {}).get('title', '')) for r in st.session_state.crawl_results]
                fig = px.histogram(x=title_lengths, title='Title Length Distribution', labels={'x': 'Title Length (chars)'})
                st.plotly_chart(fig, width='stretch')
        else:
            st.info("No SEO data to display.")

    with result_tabs[5]:  # Technologies tab
        st.subheader("Technology Detection")
        all_technologies = [tech for result in st.session_state.crawl_results for tech in result.get('technologies', [])]
        if all_technologies:
            tech_counts = Counter(all_technologies)
            tech_df = pd.DataFrame(tech_counts.items(), columns=['Technology', 'Count']).sort_values('Count', ascending=False)
            fig = px.bar(tech_df, x='Technology', y='Count', title='Technology Usage Across Crawled Pages')
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No technologies detected.")

    with result_tabs[6]: # Issues Detected
        st.subheader("⚠️ Issues Detected")
        issues = []
        for r in st.session_state.crawl_results:
            url = r['url']
            if r.get('status_code') != 200:
                issues.append({'URL': url, 'Issue': f"HTTP Status {r.get('status_code', 'N/A')}", 'Severity': 'High'})
            if r.get('response_time', 0) > 3:
                issues.append({'URL': url, 'Issue': f"Slow response: {r.get('response_time', 0):.2f}s", 'Severity': 'Medium'})
            
            seo_data = r.get('seo_data', {})
            if not seo_data.get('title'):
                issues.append({'URL': url, 'Issue': 'Missing title tag', 'Severity': 'High'})
            if not seo_data.get('meta_description'):
                issues.append({'URL': url, 'Issue': 'Missing meta description', 'Severity': 'Medium'})
            if seo_data.get('h1_count', 0) != 1:
                issues.append({'URL': url, 'Issue': f"Incorrect H1 count: {seo_data.get('h1_count', 0)}", 'Severity': 'Low'})
            if r.get('js_percentage', 0) > 80:
                issues.append({'URL': url, 'Issue': f"Excessive JS modification: {r.get('js_percentage', 0):.1f}%", 'Severity': 'Medium'})

        if issues:
            issues_df = pd.DataFrame(issues)
            def color_severity(val):
                if val == 'High': return 'background-color: #f8d7da'
                elif val == 'Medium': return 'background-color: #fff3cd'
                else: return 'background-color: #d1ecf1'
            
            styled_issues = issues_df.style.map(color_severity, subset=['Severity'])
            st.dataframe(styled_issues, use_container_width=True)
        else:
            st.success("🎉 No major issues detected!")

# Footer
st.markdown("---")
st.markdown("""
### 🚀 **Professional Features**
- **Enhanced HTML Diff Viewer** with side-by-side comparison and injection highlighting.
- **Concurrent crawling** with a stable WebDriver manager.
- **Comprehensive SEO analysis** including titles, metas, and headings.
- **Technology detection** for frameworks and server technologies.
- **SPA identification** with confidence scoring.
- **Performance metrics** with a speed scoring algorithm.
- **Automated issue detection** with severity levels.
- **Interactive visualizations** for crawl data.
- **Export capabilities** in multiple formats.

### 💡 **Pro Tips**
- Use the **Enhanced Diff Viewer** to pinpoint exactly what JavaScript is adding or changing on your pages.
- Monitor the **JS Impact** and **Issues** tabs to find pages that are heavily reliant on client-side rendering.
- **Export** your results to share with your team or for further analysis.
""", unsafe_allow_html=True)
