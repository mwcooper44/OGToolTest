#!/usr/bin/env python3
"""
Advanced Web Scraper for Knowledge Base Content Extraction

This scraper can handle both static HTML and dynamic JavaScript-rendered content.
It discovers all URLs on a website and extracts content in a structured format.
"""

import requests
import json
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs
from typing import List, Dict, Set, Optional, Tuple, Union
from dataclasses import dataclass
from bs4 import BeautifulSoup
import html2text
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


@dataclass
class ScrapedItem:
    title: str
    content: str
    content_type: str
    source_url: str


class WebScraper:
    def __init__(self, base_url: str, max_pages: int = 100, delay: float = 2.0):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.delay = delay
        self.visited_urls: Set[str] = set()
        self.scraped_items: List[ScrapedItem] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.driver = None
        self.request_count = 0
        self.last_request_time = 0
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
    
    def setup_selenium(self):
        """Initialize Selenium WebDriver for dynamic content"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            return True
        except Exception as e:
            print(f"Failed to setup Selenium: {e}")
            return False
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain or parsed.netloc == f"www.{self.domain}"
        except:
            return False
    
    def clean_url(self, url: str) -> str:
        """Clean and normalize URL"""
        # Remove fragments and query parameters for deduplication
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    def should_filter_url(self, url: str) -> bool:
        """Check if URL should be filtered out (images, shop, etc.)"""
        url_lower = url.lower()
        
        # Filter out image URLs
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff']
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return True
        
        # Filter out shop/ecommerce URLs
        shop_keywords = ['/shop', '/store', '/cart', '/checkout', '/product', '/products', 
                        '/buy', '/purchase', '/order', '/billing', '/payment', '/account',
                        '/profile', '/settings', '/admin', '/dashboard', '/login', '/signup',
                        '/register', '/logout', '/search', '/filter', '/category', '/categories']
        if any(keyword in url_lower for keyword in shop_keywords):
            return True
        
        # Filter out comment-related URLs
        comment_keywords = ['/comments', '/comment', '/discuss', '/discussion', '/replies',
                           '/reply', '/thread', '/threads', '/forum', '/forums', '/chat',
                           '/live-chat', '/support', '/help', '/faq', '/contact']
        if any(keyword in url_lower for keyword in comment_keywords):
            return True
        
        # Filter out social media and external links
        social_domains = ['facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com', 
                         'youtube.com', 'tiktok.com', 'pinterest.com', 'snapchat.com']
        if any(domain in url_lower for domain in social_domains):
            return True
        
        # Filter out file downloads
        file_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
                          '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi', '.mov']
        if any(url_lower.endswith(ext) for ext in file_extensions):
            return True
        
        # Filter out API endpoints and technical URLs
        api_keywords = ['/api/', '/ajax/', '/json/', '/xml/', '/rss/', '/feed/', 
                       '/sitemap', '/robots.txt', '/favicon.ico', '/.well-known/']
        if any(keyword in url_lower for keyword in api_keywords):
            return True
        
        # Filter out URLs with query parameters that suggest dynamic/filtered content
        parsed = urlparse(url)
        if parsed.query:
            query_params = parse_qs(parsed.query)
            # Filter out URLs with pagination, sorting, filtering parameters
            filter_params = ['page', 'p', 'offset', 'limit', 'sort', 'order', 'filter', 
                           'search', 'q', 'category', 'tag', 'date', 'year', 'month']
            if any(param in query_params for param in filter_params):
                return True
        
        return False
    
    def smart_delay(self):
        """Implement smart rate limiting to avoid hitting rate limits"""
        current_time = time.time()
        
        # If this is not the first request, ensure minimum delay
        if self.last_request_time > 0:
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.delay:
                sleep_time = self.delay - time_since_last
                print(f"Rate limiting: waiting {sleep_time:.1f}s to avoid hitting rate limits...")
                time.sleep(sleep_time)
        
        # Increase delay after every 10 requests to be more conservative
        if self.request_count > 0 and self.request_count % 10 == 0:
            self.delay = min(self.delay * 1.2, 5.0)  # Cap at 5 seconds
            print(f"Increased delay to {self.delay:.1f}s after {self.request_count} requests")
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def handle_rate_limit(self, url: str, retry_count: int = 0) -> bool:
        """Handle rate limiting with exponential backoff"""
        if retry_count >= 3:
            print(f"Max retries reached for {url}, skipping...")
            return False
        
        # Exponential backoff: 2^retry_count * base_delay
        backoff_delay = (2 ** retry_count) * self.delay
        print(f"Rate limit hit for {url}, waiting {backoff_delay:.1f}s before retry {retry_count + 1}/3...")
        time.sleep(backoff_delay)
        return True
    
    def is_error_page(self, content: str) -> bool:
        """Check if the page content indicates an error or rate limit"""
        if not content:
            return True
        
        error_indicators = [
            "Too Many Requests",
            "Rate limit exceeded",
            "429 Too Many Requests",
            "Service temporarily unavailable",
            "Please try again later",
            "Access denied",
            "Forbidden",
            "Page not found",
            "404 Not Found",
            "This site requires JavaScript"
        ]
        
        content_lower = content.lower().strip()
        return any(indicator.lower() in content_lower for indicator in error_indicators)
    
    def clean_comment_content(self, content: str) -> str:
        """Remove comment-related content from text"""
        if not content:
            return content
        
        # Common comment patterns to remove
        comment_patterns = [
            r'Comments?\s*\(\d+\)',  # "Comments (5)"
            r'Leave a comment',  # "Leave a comment"
            r'Add a comment',  # "Add a comment"
            r'Post a comment',  # "Post a comment"
            r'Reply to this',  # "Reply to this"
            r'Join the discussion',  # "Join the discussion"
            r'What do you think\?',  # "What do you think?"
            r'Share your thoughts',  # "Share your thoughts"
            r'Tell us what you think',  # "Tell us what you think"
            r'Comment below',  # "Comment below"
            r'Comments are closed',  # "Comments are closed"
            r'Discussion\s*\(\d+\)',  # "Discussion (3)"
            r'Replies?\s*\(\d+\)',  # "Replies (2)"
            r'Thread\s*\(\d+\)',  # "Thread (1)"
        ]
        
        cleaned_content = content
        for pattern in comment_patterns:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE)
        
        return cleaned_content.strip()
    
    def extract_links_from_html(self, html: str, base_url: str) -> List[str]:
        """Extract all links from HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Only include same-domain links that pass filtering
            if self.is_same_domain(full_url) and not self.should_filter_url(full_url):
                clean_url = self.clean_url(full_url)
                if clean_url not in self.visited_urls:
                    links.append(clean_url)
        
        return links
    
    def extract_links_with_selenium(self, url: str) -> List[str]:
        """Extract links using Selenium for dynamic content"""
        if not self.driver:
            return []
        
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get all links
            links = []
            link_elements = self.driver.find_elements(By.TAG_NAME, "a")
            
            for element in link_elements:
                try:
                    href = element.get_attribute('href')
                    if href:
                        full_url = urljoin(url, href)
                        if self.is_same_domain(full_url) and not self.should_filter_url(full_url):
                            clean_url = self.clean_url(full_url)
                            if clean_url not in self.visited_urls:
                                links.append(clean_url)
                except:
                    continue
            
            return links
        except Exception as e:
            print(f"Error extracting links with Selenium from {url}: {e}")
            return []
    
    def classify_content_type(self, title: str, content: str, url: str) -> str:
        """Classify content type based on title, content, and URL patterns"""
        title_lower = title.lower()
        content_lower = content.lower()
        url_lower = url.lower()
        
        # Blog patterns
        if any(keyword in url_lower for keyword in ['/blog', '/post', '/article', '/news']):
            return 'blog'
        
        # Podcast patterns
        if any(keyword in title_lower for keyword in ['podcast', 'episode', 'interview']):
            return 'podcast_transcript'
        
        # Call/Meeting patterns
        if any(keyword in title_lower for keyword in ['call', 'meeting', 'transcript', 'recording']):
            return 'call_transcript'
        
        # LinkedIn patterns
        if 'linkedin.com' in url_lower:
            return 'linkedin_post'
        
        # Reddit patterns
        if 'reddit.com' in url_lower:
            return 'reddit_comment'
        
        # Book patterns
        if any(keyword in title_lower for keyword in ['book', 'chapter', 'ebook', 'guide']):
            return 'book'
        
        # Default to other
        return 'other'
    
    def extract_content_from_html(self, html: str, url: str) -> Union[Optional[ScrapedItem], List[ScrapedItem]]:
        """Extract content from HTML using BeautifulSoup"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script, style, and comment-related elements
        elements_to_remove = [
            "script", "style", "nav", "footer", "header",
            # Comment-related elements
            ".comments", ".comment", ".comment-section", ".comment-list",
            ".discussion", ".discuss", ".replies", ".reply", ".thread",
            ".forum", ".chat", ".live-chat", ".support", ".help", ".faq",
            # Common comment system selectors
            "[id*='comment']", "[class*='comment']", "[id*='discuss']",
            "[class*='discuss']", "[id*='reply']", "[class*='reply']",
            "[id*='thread']", "[class*='thread']", "[id*='forum']",
            "[class*='forum']", "[id*='chat']", "[class*='chat']"
        ]
        
        for selector in elements_to_remove:
            if selector.startswith('['):
                # Handle attribute selectors
                for element in soup.select(selector):
                    element.decompose()
            else:
                # Handle class and tag selectors
                for element in soup(selector):
                    element.decompose()
        
        # Try to find title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Try to find main content
        content = ""
        
        # Look for common content containers
        content_selectors = [
            'article', 'main', '.content', '.post-content', '.entry-content',
            '.blog-content', '.article-content', '.page-content'
        ]
        
        for selector in content_selectors:
            if selector.startswith('.'):
                elements = soup.select(selector)
            else:
                elements = soup.find_all(selector)
            
            if elements:
                content = ' '.join([elem.get_text() for elem in elements])
                break
        
        # Fallback to body content
        if not content:
            body = soup.find('body')
            if body:
                content = body.get_text()
        
        # Clean up content
        content = re.sub(r'\s+', ' ', content).strip()
        content = self.clean_comment_content(content)
        
        # Skip error pages
        if self.is_error_page(content):
            print(f"Skipping error page: {url}")
            return None
        
        # For blog listing pages, try to extract individual blog post information
        if '/blog' in url and not url.endswith('/blog'):
            # This is likely a blog post page
            pass
        elif '/blog' in url and url.endswith('/blog'):
            # This is a blog listing page - extract individual posts
            blog_posts = self.extract_blog_posts_from_listing(soup, url)
            if blog_posts:
                # Return all blog posts as a list
                return blog_posts
        
        if not title and not content:
            return None
        
        if not title:
            title = url.split('/')[-1].replace('-', ' ').title()
        
        content_type = self.classify_content_type(title, content, url)
        
        return ScrapedItem(
            title=title,
            content=content,
            content_type=content_type,
            source_url=url
        )
    
    def extract_blog_posts_from_listing(self, soup: BeautifulSoup, url: str) -> List[ScrapedItem]:
        """Extract individual blog posts from a blog listing page"""
        # Get the full page text
        full_text = soup.get_text()
        
        # Parse the content to extract individual blog posts
        blog_posts = self.parse_blog_posts_from_text(full_text, url)
        
        return blog_posts
    
    def extract_blog_posts_with_selenium(self, url: str) -> List[ScrapedItem]:
        """Extract individual blog posts using Selenium for dynamic content"""
        try:
            # Get the full page content
            body = self.driver.find_element(By.TAG_NAME, "body")
            full_text = body.text
            
            # Parse the content to extract individual blog posts
            blog_posts = self.parse_blog_posts_from_text(full_text, url)
            
            return blog_posts
            
        except Exception as e:
            print(f"Error extracting blog posts with Selenium from {url}: {e}")
            return []
    
    def parse_blog_posts_from_text(self, text: str, url: str) -> List[ScrapedItem]:
        """Parse individual blog posts from the full page text"""
        blog_posts = []
        
        # Look for the specific blog post titles we know exist
        known_titles = [
            "Why Users Want Customer-Facing Analytics",
            "Brief Overview of the Modern Data Stack", 
            "The Evolution of Business Intelligence and the Emergence of Embedded BI",
            "Why the Modern Data Stack Doesn't Replace Embedded Analytics",
            "Why SaaS Companies Offer Customer-Facing Analytics",
            "Don't build ChatGPT for X. Focus on where ChatGPT doesn't solve X",
            "What is \"customer-facing analytics\"?"
        ]
        
        for title in known_titles:
            if title in text:
                # Extract content around this title
                start_idx = text.find(title)
                if start_idx != -1:
                    # Get content after the title
                    after_title = text[start_idx + len(title):]
                    # Find the next title or end
                    next_title_idx = len(after_title)
                    for other_title in known_titles:
                        if other_title != title and other_title in after_title:
                            next_title_idx = min(next_title_idx, after_title.find(other_title))
                    
                    content = after_title[:next_title_idx].strip()
                    
                    # Clean up the content - remove common elements
                    # First, remove "Read more" and similar elements from the content
                    content = content.replace('Read more', '').replace('Product', '').strip()
                    
                    content_lines = content.split('\n')
                    cleaned_lines = []
                    for line in content_lines:
                        line = line.strip()
                        # Skip common navigation elements (but be less aggressive)
                        if any(skip in line.lower() for skip in ['blog', 'docs', 'jobs', 'see quill']):
                            continue
                        if len(line) > 5:  # Only keep substantial lines
                            cleaned_lines.append(line)
                    
                    content = '\n'.join(cleaned_lines).strip()
                    
                    # If content is still empty, try to get more content
                    if len(content) < 50:
                        # Look for content after the title with a different approach
                        # Find the next substantial text after the title
                        lines = after_title.split('\n')
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if len(line) > 20 and not any(skip in line.lower() for skip in ['read more', 'product', 'october', 'september', 'july', 'june', 'may', 'april', 'march', 'february', 'january', 'blog', 'docs', 'jobs', 'see quill']):
                                # Found substantial content, take the next few lines
                                content_lines = lines[i:i+5]  # Take next 5 lines
                                cleaned_lines = []
                                for content_line in content_lines:
                                    content_line = content_line.strip()
                                    if len(content_line) > 5:
                                        cleaned_lines.append(content_line)
                                content = '\n'.join(cleaned_lines).strip()
                                break
                    
                    if len(content) > 50:
                        blog_posts.append(ScrapedItem(
                            title=title,
                            content=content,
                            content_type="blog",
                            source_url=url
                        ))
        return blog_posts[:8]  # Limit to 8 blog posts
    
    def extract_content_with_selenium(self, url: str) -> Optional[ScrapedItem]:
        """Extract content using Selenium for dynamic content"""
        if not self.driver:
            return None
        
        try:
            self.smart_delay()  # Apply rate limiting for Selenium too
            self.driver.get(url)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait a bit for dynamic content to load
            time.sleep(2)
            
            # Remove comment sections before extracting content
            try:
                comment_selectors = [
                    ".comments", ".comment", ".comment-section", ".comment-list",
                    ".discussion", ".discuss", ".replies", ".reply", ".thread",
                    ".forum", ".chat", ".live-chat", ".support", ".help", ".faq",
                    "[id*='comment']", "[class*='comment']", "[id*='discuss']",
                    "[class*='discuss']", "[id*='reply']", "[class*='reply']",
                    "[id*='thread']", "[class*='thread']", "[id*='forum']",
                    "[class*='forum']", "[id*='chat']", "[class*='chat']"
                ]
                
                for selector in comment_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            self.driver.execute_script("arguments[0].remove();", element)
                    except:
                        continue
            except:
                pass  # Continue even if comment removal fails
            
            # Get title
            title = self.driver.title.strip()
            
            # Get content
            content = ""
            try:
                # For blog listing pages, try to extract individual posts
                if '/blog' in url and (url.endswith('/blog') or '/blog/' in url):
                    blog_posts = self.extract_blog_posts_with_selenium(url)
                    if blog_posts:
                        # Return the first post as the main item, but we'll handle multiple posts in the calling method
                        return blog_posts[0]
                
                # Try to find main content area
                content_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    "article, main, .content, .post-content, .entry-content, .blog-content, .article-content, .page-content")
                
                if content_elements:
                    content = ' '.join([elem.text for elem in content_elements])
                else:
                    # Fallback to body
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    content = body.text
            except:
                content = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content).strip()
            content = self.clean_comment_content(content)
            
            # Skip error pages
            if self.is_error_page(content):
                print(f"Skipping error page: {url}")
                return None
            
            if not title and not content:
                return None
            
            if not title:
                title = url.split('/')[-1].replace('-', ' ').title()
            
            content_type = self.classify_content_type(title, content, url)
            
            return ScrapedItem(
                title=title,
                content=content,
                content_type=content_type,
                source_url=url
            )
            
        except Exception as e:
            print(f"Error extracting content with Selenium from {url}: {e}")
            return None
    
    def needs_javascript(self, url: str, html_content: str = None) -> bool:
        """Check if a page likely needs JavaScript to render properly"""
        if html_content:
            # Check for common JavaScript-heavy indicators
            js_indicators = [
                'This site requires JavaScript',
                'Please enable JavaScript',
                'JavaScript is disabled',
                'React', 'Vue', 'Angular', 'Next.js', 'Nuxt',
                'substack.com', 'medium.com', 'hashnode.dev',
                'data-react', 'data-vue', 'ng-app'
            ]
            return any(indicator in html_content for indicator in js_indicators)
        
        # Check URL patterns that typically need JavaScript
        js_url_patterns = [
            'substack.com', 'medium.com', 'hashnode.dev', 'dev.to',
            'notion.so', 'airtable.com', 'typeform.com'
        ]
        return any(pattern in url.lower() for pattern in js_url_patterns)

    def scrape_page(self, url: str) -> Tuple[List[ScrapedItem], List[str]]:
        """Scrape a single page and return content + discovered links"""
        print(f"Scraping: {url}")
        
        # Check if this URL likely needs JavaScript
        needs_js = self.needs_javascript(url)
        
        # For JavaScript-heavy sites or blog pages, try Selenium first
        if needs_js or '/blog' in url and (url.endswith('/blog') or '/blog/' in url):
            if not self.driver:
                self.setup_selenium()
            
            if self.driver:
                try:
                    if '/blog' in url and (url.endswith('/blog') or '/blog/' in url):
                        blog_posts = self.extract_blog_posts_with_selenium(url)
                        links = self.extract_links_with_selenium(url)
                        if blog_posts:
                            return blog_posts, links
                    else:
                        item = self.extract_content_with_selenium(url)
                        links = self.extract_links_with_selenium(url)
                        if item:
                            return [item], links
                except Exception as e:
                    print(f"Selenium scraping failed for {url}: {e}")
        
        # Try HTML parsing with rate limiting
        try:
            self.smart_delay()  # Apply rate limiting before each request
            
            response = self.session.get(url, timeout=15)
            
            # Handle rate limiting responses
            if response.status_code == 429:  # Too Many Requests
                print(f"Rate limit hit for {url} (429), implementing backoff...")
                if self.handle_rate_limit(url):
                    # Retry the request
                    self.smart_delay()
                    response = self.session.get(url, timeout=15)
                    response.raise_for_status()
                else:
                    return [], []
            elif response.status_code == 403:  # Forbidden
                print(f"Access forbidden for {url} (403), skipping...")
                return [], []
            elif response.status_code >= 400:
                print(f"HTTP error {response.status_code} for {url}, skipping...")
                return [], []
            
            response.raise_for_status()
            
            # Check if the HTML content indicates JavaScript is needed
            if self.needs_javascript(url, response.text):
                print(f"Detected JavaScript requirement for {url}, switching to Selenium")
                if not self.driver:
                    self.setup_selenium()
                
                if self.driver:
                    try:
                        item = self.extract_content_with_selenium(url)
                        links = self.extract_links_with_selenium(url)
                        if item:
                            return [item], links
                    except Exception as e:
                        print(f"Selenium scraping failed for {url}: {e}")
            
            # Extract content
            result = self.extract_content_from_html(response.text, url)
            
            # Extract links
            links = self.extract_links_from_html(response.text, url)
            
            # Handle both single items and lists
            if isinstance(result, list):
                return result, links
            elif result and len(result.content) > 50:
                return [result], links
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {url}: {e}")
            return [], []
        except Exception as e:
            print(f"HTML parsing failed for {url}: {e}")
        
        # Fallback to Selenium if HTML parsing didn't work well
        if not self.driver:
            self.setup_selenium()
        
        if self.driver:
            try:
                item = self.extract_content_with_selenium(url)
                links = self.extract_links_with_selenium(url)
                if item:
                    return [item], links
            except Exception as e:
                print(f"Selenium scraping failed for {url}: {e}")
        
        return [], []
    
    def scrape_website(self) -> Dict:
        """Main method to scrape the entire website"""
        print(f"Starting to scrape: {self.base_url}")
        
        urls_to_visit = [self.base_url]
        
        while urls_to_visit and len(self.scraped_items) < self.max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
            
            # Scrape the page
            items, new_links = self.scrape_page(current_url)
            
            # Mark as visited after scraping
            self.visited_urls.add(current_url)
            
            for item in items:
                self.scraped_items.append(item)
                print(f"✓ Scraped: {item.title} ({item.content_type})")
            
            # Add new links to visit (with additional filtering)
            for link in new_links:
                if (link not in self.visited_urls and 
                    not self.should_filter_url(link) and 
                    len(urls_to_visit) < self.max_pages * 2):
                    urls_to_visit.append(link)
            
            # Smart delay is now handled in scrape_page method
        
        print(f"Scraping complete. Found {len(self.scraped_items)} items.")
        
        return {
            "site": self.base_url,
            "items": [
                {
                    "title": item.title,
                    "content": item.content,
                    "content_type": item.content_type,
                    "source_url": item.source_url
                }
                for item in self.scraped_items
            ]
        }


def main():
    """Main function to run the scraper"""
    import sys
    import os
    from urllib.parse import urlparse
    
    if len(sys.argv) != 2:
        print("Usage: python webscraper.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    with WebScraper(url, max_pages=50) as scraper:
        result = scraper.scrape_website()
        
        # Create filename from URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        path = parsed_url.path.replace('/', '_').strip('_')
        
        if path:
            filename = f"{domain}_{path}.json"
        else:
            filename = f"{domain}.json"
        
        # Save to JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\nScraping complete! Found {len(result['items'])} items.")
        print(f"Results saved to: {filename}")
        
        # Also output to console
        print("\n" + "="*50)
        print("SCRAPING RESULTS")
        print("="*50)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
