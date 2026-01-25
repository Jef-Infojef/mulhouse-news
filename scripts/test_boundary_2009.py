import requests
import xml.etree.ElementTree as ET

def test_date(date_str, next_date_str):
    CITY = "Mulhouse"
    rss_url = f"https://news.google.com/rss/search?q=%22{CITY}%22+after:{date_str}+before:{next_date_str}&hl=fr&gl=FR&ceid=FR:fr"
    print(f"[*] Recherche : {date_str} ...")
    try:
        resp = requests.get(rss_url, timeout=10)
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        print(f"    -> {len(items)} articles trouvés.")
    except Exception as e:
        print(f"    -> ❌ Erreur : {e}")

test_date("2009-12-01", "2009-12-02")
test_date("2009-12-15", "2009-12-16")
test_date("2009-12-31", "2010-01-01")
test_date("2010-01-01", "2010-01-02")
