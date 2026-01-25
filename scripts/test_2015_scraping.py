import requests
import xml.etree.ElementTree as ET

def test_old_news():
    CITY = "Mulhouse"
    day_str = "2009-12-15"
    next_day_str = "2009-12-16"
    rss_url = f"https://news.google.com/rss/search?q=%22{CITY}%22+after:{day_str}+before:{next_day_str}&hl=fr&gl=FR&ceid=FR:fr"
    
    print(f"[*] Test de recherche RSS pour le {day_str}...")
    # ... (reste du code)

if __name__ == "__main__":
    test_old_news()
