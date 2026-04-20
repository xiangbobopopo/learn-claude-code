#!/usr/bin/env python3
"""
Web Scraping Tools and Examples
Various web scraping techniques using different libraries
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import re
from urllib.parse import urljoin, urlparse
import sqlite3
from datetime import datetime

class WebScraper:
    """Basic web scraper using requests and BeautifulSoup"""
    
    def __init__(self, delay=1):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.delay = delay
        
    def get_page(self, url):
        """Fetch a web page"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            time.sleep(self.delay)  # Be respectful
            return response
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def parse_html(self, html_content):
        """Parse HTML content with BeautifulSoup"""
        return BeautifulSoup(html_content, 'html.parser')
    
    def scrape_example_page(self):
        """Scrape a simple example page"""
        # Create a simple HTML page for demo
        demo_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Demo Page</title></head>
        <body>
            <h1>Welcome to Demo Page</h1>
            <div class="articles">
                <article class="post">
                    <h2><a href="/post1">First Post</a></h2>
                    <p class="summary">This is the first post summary.</p>
                    <span class="date">2024-01-15</span>
                </article>
                <article class="post">
                    <h2><a href="/post2">Second Post</a></h2>
                    <p class="summary">This is the second post summary.</p>
                    <span class="date">2024-01-16</span>
                </article>
            </div>
            <div class="sidebar">
                <h3>Categories</h3>
                <ul>
                    <li><a href="/tech">Technology</a></li>
                    <li><a href="/science">Science</a></li>
                    <li><a href="/sports">Sports</a></li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Save demo page
        with open("demo_page.html", "w") as f:
            f.write(demo_html)
        
        # Parse and extract data
        soup = self.parse_html(demo_html)
        
        # Extract articles
        articles = []
        for article in soup.find_all('article', class_='post'):
            title_elem = article.find('h2').find('a')
            summary_elem = article.find('p', class_='summary')
            date_elem = article.find('span', class_='date')
            
            articles.append({
                'title': title_elem.text if title_elem else '',
                'link': title_elem.get('href') if title_elem else '',
                'summary': summary_elem.text if summary_elem else '',
                'date': date_elem.text if date_elem else ''
            })
        
        # Extract categories
        categories = []
        sidebar = soup.find('div', class_='sidebar')
        if sidebar:
            for li in sidebar.find('ul').find_all('li'):
                a_tag = li.find('a')
                if a_tag:
                    categories.append({
                        'name': a_tag.text,
                        'link': a_tag.get('href')
                    })
        
        return {
            'articles': articles,
            'categories': categories,
            'title': soup.find('h1').text if soup.find('h1') else ''
        }
    
    def scrape_with_regex(self, html_content, patterns):
        """Extract data using regular expressions"""
        results = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, html_content)
            results[name] = matches
        return results
    
    def save_to_json(self, data, filename):
        """Save scraped data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {filename}")
    
    def save_to_csv(self, data, filename):
        """Save scraped data to CSV file"""
        if not data:
            return
            
        # Assuming data is a list of dictionaries
        if isinstance(data, list) and len(data) > 0:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            print(f"Data saved to {filename}")

class DatabaseScraper(WebScraper):
    """Web scraper with database storage"""
    
    def __init__(self, db_path="scraped_data.db"):
        super().__init__()
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                link TEXT,
                summary TEXT,
                date TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                link TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_to_database(self, scraped_data):
        """Save scraped data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save articles
        for article in scraped_data.get('articles', []):
            cursor.execute('''
                INSERT INTO articles (title, link, summary, date)
                VALUES (?, ?, ?, ?)
            ''', (article['title'], article['link'], article['summary'], article['date']))
        
        # Save categories
        for category in scraped_data.get('categories', []):
            cursor.execute('''
                INSERT INTO categories (name, link)
                VALUES (?, ?)
            ''', (category['name'], category['link']))
        
        conn.commit()
        conn.close()
        print(f"Data saved to database: {self.db_path}")

class APIScraper:
    """API-based data collection"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; API Scraper)'
        })
    
    def get_json_api(self, url, params=None):
        """Fetch data from JSON API"""
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching API {url}: {e}")
            return None
    
    def demo_jsonplaceholder_api(self):
        """Demo: Fetch data from JSONPlaceholder API"""
        # Free fake API for testing
        base_url = "https://jsonplaceholder.typicode.com"
        
        # Fetch posts
        posts = self.get_json_api(f"{base_url}/posts")
        if posts:
            print(f"Fetched {len(posts)} posts")
            
            # Display first few posts
            for post in posts[:3]:
                print(f"- {post['title'][:50]}...")
        
        # Fetch users
        users = self.get_json_api(f"{base_url}/users")
        if users:
            print(f"\nFetched {len(users)} users")
            for user in users[:3]:
                print(f"- {user['name']} ({user['email']})")
        
        return {'posts': posts[:10] if posts else [], 'users': users[:10] if users else []}

# Demo and examples
class ScrapingExamples:
    """Collection of scraping examples and tutorials"""
    
    @staticmethod
    def show_scraping_methods():
        """Show different scraping methods"""
        print("=== Web Scraping Methods ===")
        
        print("\n1. BeautifulSoup (HTML parsing):")
        print("""
        from bs4 import BeautifulSoup
        import requests
        
        response = requests.get('https://example.com')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find elements
        titles = soup.find_all('h1')
        links = soup.find_all('a', href=True)
        """)
        
        print("\n2. Regular Expressions:")
        print("""
        import re
        
        # Extract email addresses
        emails = re.findall(r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b', html_content)
        
        # Extract phone numbers
        phones = re.findall(r'\\b\\d{3}-\\d{3}-\\d{4}\\b', html_content)
        """)
        
        print("\n3. XPath (with lxml):")
        print("""
        from lxml import html
        
        tree = html.fromstring(html_content)
        elements = tree.xpath('//div[@class="example"]/text()')
        """)
        
        print("\n4. API Requests:")
        print("""
        import requests
        import json
        
        response = requests.get('https://api.example.com/data')
        data = response.json()
        
        # Process JSON data
        for item in data['items']:
            print(item['title'])
        """)
    
    @staticmethod
    def show_best_practices():
        """Show web scraping best practices"""
        print("\n=== Web Scraping Best Practices ===")
        print("""
        1. Check robots.txt before scraping
        2. Use appropriate delays between requests
        3. Set a descriptive User-Agent header
        4. Handle errors gracefully
        5. Respect rate limits
        6. Cache responses when possible
        7. Use sessions for multiple requests
        8. Consider using APIs when available
        9. Be mindful of legal and ethical considerations
        10. Test on small datasets first
        """)

if __name__ == "__main__":
    # Demo the scraping tools
    print("🚀 Web Scraping Demo")
    
    # Show examples
    examples = ScrapingExamples()
    examples.show_scraping_methods()
    examples.show_best_practices()
    
    # Demo basic scraper
    scraper = WebScraper()
    scraped_data = scraper.scrape_example_page()
    
    print("\n📊 Scraped Data:")
    print(f"Title: {scraped_data['title']}")
    print(f"Articles: {len(scraped_data['articles'])}")
    print(f"Categories: {len(scraped_data['categories'])}")
    
    # Save data
    scraper.save_to_json(scraped_data, "scraped_data.json")
    if scraped_data['articles']:
        scraper.save_to_csv(scraped_data['articles'], "articles.csv")
    
    # Demo API scraper
    api_scraper = APIScraper()
    api_data = api_scraper.demo_jsonplaceholder_api()
    
    # Demo database scraper
    db_scraper = DatabaseScraper()
    db_scraper.save_to_database(scraped_data)
