import requests
import xml.etree.ElementTree as ET

def main():
    url = "https://news.google.com/rss/search?q=Mulhouse&hl=fr&gl=FR&ceid=FR:fr"
    try:
        resp = requests.get(url, timeout=15)
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        
        print(f"--- 10 dernières actus RSS ({len(items)} au total) ---")
        for item in items[:10]:
            title = item.find("title").text
            pub_date = item.find("pubDate").text
            print(f"- {title}")
            print(f"  Date : {pub_date}")
            print("-" * 20)
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    main()
