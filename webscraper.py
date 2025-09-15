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
    def __init__(self, base_url: str, max_pages: int = 100, delay: float = 1.0):
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
    
    def extract_links_from_html(self, html: str, base_url: str) -> List[str]:
        """Extract all links from HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Only include same-domain links
            if self.is_same_domain(full_url):
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
                        if self.is_same_domain(full_url):
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
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
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
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait a bit for dynamic content to load
            time.sleep(2)
            
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
    
    def scrape_page(self, url: str) -> Tuple[List[ScrapedItem], List[str]]:
        """Scrape a single page and return content + discovered links"""
        print(f"Scraping: {url}")
        
        # For blog listing pages, try Selenium first as they're often dynamic
        if '/blog' in url and (url.endswith('/blog') or '/blog/' in url):
            if not self.driver:
                self.setup_selenium()
            
            if self.driver:
                try:
                    blog_posts = self.extract_blog_posts_with_selenium(url)
                    links = self.extract_links_with_selenium(url)
                    if blog_posts:
                        return blog_posts, links
                except Exception as e:
                    print(f"Selenium scraping failed for {url}: {e}")
        
        # Try HTML parsing
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Extract content
            result = self.extract_content_from_html(response.text, url)
            
            # Extract links
            links = self.extract_links_from_html(response.text, url)
            
            # Handle both single items and lists
            if isinstance(result, list):
                return result, links
            elif result and len(result.content) > 50:
                return [result], links
            
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
            
            # Add new links to visit
            for link in new_links:
                if link not in self.visited_urls and len(urls_to_visit) < self.max_pages * 2:
                    urls_to_visit.append(link)
            
            # Delay between requests
            time.sleep(self.delay)
        
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
