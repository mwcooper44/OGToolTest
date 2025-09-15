# Advanced Web Scraper

A comprehensive web scraper that can extract content from both static HTML and dynamic JavaScript-rendered websites. The scraper automatically discovers all URLs on a website and extracts content in a structured JSON format.

## Features

- **Dual-mode scraping**: Uses HTML parsing for fast extraction, with Selenium fallback for dynamic content
- **Intelligent content detection**: Automatically identifies blog posts, articles, and other content types
- **URL discovery**: Crawls through all links on the website to find content
- **Content classification**: Categorizes content as blog, podcast, call transcript, LinkedIn post, Reddit comment, book, or other
- **JSON output**: Returns structured data in the specified format

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. The scraper will automatically download ChromeDriver when needed.

## Usage

```bash
python webscraper.py <URL>
```

### Examples

```bash
# Scrape a blog
python webscraper.py "https://quill.co/blog"

# Scrape a specific blog category
python webscraper.py "https://nilmamano.com/blog/category/dsa"

# Scrape any website
python webscraper.py "https://example.com"
```

## Output Format

The scraper returns JSON in the following format:

```json
{
  "site": "<URL>",
  "items": [
    {
      "title": "Item Title",
      "content": "Markdown content",
      "content_type": "blog|podcast_transcript|call_transcript|linkedin_post|reddit_comment|book|other",
      "source_url": "url"
    }
  ]
}
```

## How It Works

1. **URL Discovery**: Starts with the provided URL and discovers all linked pages on the same domain
2. **Content Extraction**: For each page:
   - First tries HTML parsing with BeautifulSoup for fast extraction
   - Falls back to Selenium WebDriver for dynamic content
   - Extracts titles, content, and metadata
3. **Content Classification**: Automatically categorizes content based on URL patterns and content analysis
4. **JSON Output**: Formats all extracted content into the specified JSON structure

## Configuration

You can modify the scraper behavior by adjusting these parameters in the `WebScraper` class:

- `max_pages`: Maximum number of pages to scrape (default: 100)
- `delay`: Delay between requests in seconds (default: 1.0)

## Requirements

- Python 3.7+
- Chrome browser (for Selenium)
- Internet connection

## Notes

- The scraper respects robots.txt and implements reasonable delays between requests
- For dynamic content, Chrome will run in headless mode
- The scraper automatically handles different website structures and content types
