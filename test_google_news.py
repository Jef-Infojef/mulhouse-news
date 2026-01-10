#!/usr/bin/env python3
"""Test script to extract real article URLs from Google News RSS"""

import requests
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import re
import base64
from googlenewsdecoder import gnewsdecoder

# Fetch Google News RSS
print("[*] Fetching Google News RSS feed...")
rss_url = "https://news.google.com/rss/search?q=Mulhouse&hl=fr&gl=FR&ceid=FR:fr"

response = requests.get(rss_url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

if response.status_code != 200:
    print(f"[!] Error fetching RSS: {response.status_code}")
    exit(1)

# Parse XML
try:
    root = ET.fromstring(response.content)
except Exception as e:
    print(f"[!] Error parsing XML: {e}")
    exit(1)

# Function to extract real URL from Google News RSS link
def extract_real_url_from_google_news(google_news_url):
    """Decode Google News RSS URL to get the real article URL"""
    try:
        print(f"      [*] Decoding Google News URL...")
        result = gnewsdecoder(google_news_url)

        # gnewsdecoder returns a dict with 'status' and 'decoded_url'
        if isinstance(result, dict) and result.get('status') and result.get('decoded_url'):
            decoded_url = result['decoded_url']
            print(f"      [+] Successfully decoded: {decoded_url}")
            return decoded_url
        else:
            print(f"      [!] Decoding failed: {result}")
            return None
    except Exception as e:
        print(f"      [!] Error decoding: {e}")
        return None

# Get namespace
ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}

# Find items
items = root.findall('.//item')
print(f"[+] Found {len(items)} articles\n")

# Look at first few articles
for idx, item in enumerate(items[:3]):
    print(f"\n{'='*80}")

    title_elem = item.find('title')
    title = title_elem.text if title_elem is not None else "N/A"
    print(f"Article {idx + 1}: {title}")
    print(f"{'='*80}")

    # Get link (Google News URL)
    link_elem = item.find('link')
    google_link = link_elem.text if link_elem is not None else "N/A"
    print(f"\n1. RSS Link (Google News URL):")
    print(f"   {google_link}\n")

    # Get description
    desc_elem = item.find('description')
    description = desc_elem.text if desc_elem is not None else ""

    if description:
        print(f"2. Description HTML (first 500 chars):")
        print(f"   {description[:500]}...\n")

        # Extract all links from description using regex
        link_pattern = r'href=["\']([^"\']+)["\']'
        links = re.findall(link_pattern, description)

        print(f"3. Trying to extract real article URL from Google News link:")
        real_article_url = extract_real_url_from_google_news(google_link)

        if real_article_url:
            print(f"\n4. Testing real article URL:")
            try:
                print(f"   Fetching: {real_article_url[:80]}...")
                article_response = requests.get(real_article_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                print(f"   Status: {article_response.status_code}")
                print(f"   Final URL: {article_response.url}")
                print(f"   Content length: {len(article_response.text)} bytes")

                # Look for og:image
                og_image_match = re.search(r"<meta\s+property=['\"]og:image['\"][^>]*content=['\"]([^'\"]+)['\"]", article_response.text, re.IGNORECASE)
                if og_image_match:
                    image_url = og_image_match.group(1)
                    print(f"   [+] og:image FOUND: {image_url[:100]}...")
                else:
                    print(f"   [!] og:image NOT FOUND")
            except Exception as e:
                print(f"   [!] Error fetching: {e}")
        else:
            print(f"\n4. [!] No real article URL found!")
