import os
import psycopg2
from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import random

# Configuration BDD
DATABASE_URL = os.getenv("DATABASE_URL")

# --- LE COOKIE EN DUR (Découpé pour éviter les erreurs de syntaxe) ---
C = [
    "consentTrackingPub=1; Edition=%7B%22code%22%3A%22WALS00%22%2C%22label%22%3A%22Edition%20nationale%22%2C%22url%22%3A%22%2F%22%7D; ",
    "_pcid=%7B%22browserId%22%3A%22mktjfuc6u30qco4c%22%2C%22_t%22%3A%22n0hydbqo%7Cmktjfueo%22%7D; ",
    "_pctx=%7Bu%7DN4IgrgzgpgThIC4B2YA2qA05owMoBcBDfSREQpAeyRCwgEt8oBJAE0RXSwH18ykADAAsAnqwBGAR0kAfALYBrfACsAZmCiSQAXyA; ",
    "didomi_token=eyJ1c2VyX2lkIjoiMTliZjQ3ZDgtZGJhYi02NmQzLWFmMTEtZjYyMDkzYzU4ZTYxIiwiY3JlYXRlZCI6IjIwMjYtMDEtMjVUMDk6MzA6MjcuNjQyWi씨",
    "InVwZGF0ZWQiOiIyMDI2LTAxLTI1VDA5OjMwOjMwLjIxN1oiLCJ2ZW5kb3JzIjp7ImVuYWJsZWQiOlsiZ29vZ2xlIiwidHdpdHRlciIsImM6ZHluYWRtaWMtWGtiQnRlSkQiL",
    "CJjOnRhcGFkaW5jLVZEVFVVY0t3IiwiYzplYmF5aW5jLWJOR3Jpa1F3IiwiYzp6ZWJlc3RvZi1jZDdOWUVMTCIsImM6dW5ydWx5Z3JvLW5LeUxxZEtpIiwiYzppbnN0YWdyYW0i",
    "LCJjOm1hZ25pdGVpbi1lUEVwYkNRNyIsImM6cG9vb2wtVnloQ2l0N04iLCJjOm9yYWNsZWRhdC16MmNwS0NZdCIsImM6c2lnbmFsZGlnLWlMN25NZzdRIiwiYzppcHJvc3BlY3Qt",
    "cUppdEZQRUIiLCJjOmlkY2xpY2ttLTZVbnFSaWI3IiwiYzp5b3V0dWJlIiwiYzpibHVlc2t5LURlem1oeWgzIiwiYzp0aHJlYWRzLWtlUVk0S1E4IiwiYzptYXN0b2Rvbi0ybkZDb",
    "VJSOCIsImM6YWR0aGVvcmVuLUJQUGRjVEZuIiwiYzpncm91cG11ay1tRkJyTHlBNCIsImM6YW1vYi1temdEZ0JRUiIsImM6aW5za2lubWVkLWl6Z2VkaWtDIiwiYzpsaXF1aWRtdC",
    "-INkVuYVZqRiIsImM6cm9rdWFkdmVyLWloYVp6Y2Q5IiwiYzphZG9taWstV0phTGpkaEEiLCJjOmFkdmVybGluZS1ZWTdrcU5aNyIsImM6c3BhcmtsaXRuLVhyTVFWcXpkIiwiYzpiaW",
    "5nLWFkcyIsImM6YWItdGFzdHkiLCJjOnNpcmRhdGFjby15N3ppN0VKYiIsImM6bWljcm9zb2Z0LW9uZWRyaXZlLWxpdmUtc2RrIiwiYzpjaGFydGJlYXQiLCJjOm15ZmVlbGJhY2si",
    "LCJjOmNsaWNraW50ZXh0IiwiYzpwb29vbC1ld1o2NmVnZiIsImM6cHVic3RhY2stV3JDYkV5Y00iLCJjOmFjcG0tSkIzNEJicmQiLCJjOm1pY3Jvc29mdC1hbmFseXRpY3MiLCJjOmFw",
    "cHNmbHllci13RE5ia0NiNiIsImM6YXBsb3plLXg0N0pmWFVLIiwiYzphdGludGVybmUtY1dRS0hlSloiLCJjOm9uZXNpZ25hbC1uS1hmQ3BZcyIsImM6YWNhc3QtQ2M3MmNoWHAiLCJjO",
    "nNvdW5kY2xvdWQteEtNREdYNEwiLCJjOmZsb3VyaXNoLXhueFlNWjZOIiwiYzpnZW5pYWxseS1aOGJSaHFFbiIsImM6Z29vZ2xlbWFwLWREN0NaQ0pnIiwiYzppbmZvZ3JhbS1xcWhkM",
    "2hmTSIsImM6bWFwczRuZXdzLTNYOVZRVzc2IiwiYzpwbGF5YnV6ei1qaEpxQ0F4SyIsImM6c2hvcnRoYW5kLTZHTUZLMkJXIiwiYzpzdG9yeW1hcC1MWnBpZDdZcSIsImM6dGltZWxpbmU",
    "qLWU2WFJDS1VYIiwiYzpqdXh0YXBvc2UtTVpnSEZmWXgiLCJjOmR5bmFkbWljbWE0NzhlUmpLY1YiLCJjOmFkb3Rtb2IiLCJjOnBvd2Vyc3BhY2Utd0ZKY3kyd2YiLCJjOnN1YnNjcmliZS1",
    "abXdVZVVUCIsImM6a2V0Y2h1cGFkLWl3VFFFOEZxIiwiYzptZWV0cmljc2ctTmRFTjhXeFQiLCJjOmVteGRpZ2l0YS1HM1FRQmg0USIsImM6bWljcm9zb2Z0IiwiYy1r b2NoYXZhaW4tTkFU",
    "QzhaMmEiLCJjOmJ5dGVkYW5jZS1mYmtOUDhCYyIsImM6YWR3YXlzc2FzLUxOaTJaWjlxIiwiYzpwcmViaWRvcmctSGlqaXJZZGIiLCJjOmplbGx5ZmlzaC1iOU5XOWI5NiIsImM6YmF0Y2gtS",
    "jJBeFlWVkEiLCJjOmtleW1hbnRpY3MtdEoyd0pYamkiLCJjOmFtYXpvbmFkLWlNVXE4TndaIl19LCJwdXJwb3NlcyI6eyJlbmFibGVkIjpbImdlb2xvY2F0aW9uX2RhdGEiLCJkZXZpY2VfY2g",
    "hcmFjdGVyaXN0aWNzIiwicmVzZWF1eHNvLTlLYmpid05oIiwibWFya2V0aW5nIiwiYWR2ZXJ0aXNpbmciLCJhdWRpZW5jZW0teGVkZVUyZ1EiLCJjb250ZW51c3YtaEZUOGlmZFIiLCJjb250Z",
    "W51c2MtcFhBVlV0OHIiLCJtZXN1cmVkYS1oN0dRZXJyVCJ9LCJ2ZW5kb3JzX2xpIjp7ImVuYWJsZWQiOlsimM6YWRvbWlrLVdKYUxqZGhBIl19LCJ2ZXJzaW9uIjoyLCJhYyI6IkNuV0FPQUZrQ",
    "VNvQjVnRWxnYTBCUVdDblVBQUEuQUFBQSJ9; ",
    "euconsent-v2=CQelaIAQelaIAAHABBENCOFsAP_gAABAAAAALAFB7C7fSWFjeTJnYPpEaQBcwVAKokAhBACJAQgBiBoEIJQQlmAKIATAAKAKABAAgERAAQBhCABAAACAAIABISAEIAAQIQAAIqA",
    "EAAARAwAACBhBGwEAEAAQgEAQAAEAgAMAAAqAQFBAAYAgBEAQAAAhAACFAAAAADAgAAAAAAAAAggAAAAAIAIAEAEEAFAAEABAAAEAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAABADiACADgAYpABg",
    "ACC-xKADAAEF9h0AGAAIL7EIAMAAQX2CQAYAAgvsWgAwABBfY.f_wAAAgAAAAA; ",
    "_cb=CT4njhPQyICCZpIHY; AFFICHE_C=xHfNhf7@Dl3E72; _fbp=fb.1.1769333430905.653501527339543221; ",
    "__gpi=UID=000012eb608f5251:T=1769333432:RT=1769333432:S=ALNI_MZVHkKWBCo1hvzSXb201J0-X_NXgg; ",
    "ivbsdid=%7B%22id%22%3A%22di3pbr6zi7yofu_5883%22%7D; ivNotCD=y; ivdtbrk=20481.2,10; ivBlk=n; ",
    "KiosqueEditionFavorite=%7B%22code%22%3A%22%22%7D; ",
    "FCCDCF=%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%223f28e89d-859c-4be9-82e2-78ee39209598%5C%22%2C%5B1769333505%2C135000000%5D%5D%22%5D%5D%5D; ",
    "firstid=bcc0da5b69e24828bc825f8384fb49b1; _poool=a9e8824c-9ccb-4edb-b337-3c24cc693195; ",
    "FCNEC=%5B%5B%22AKsRol95H01BqGssAqaHknvp_fsQVeh4rDbXLkyZ3A1fF2rhMiQ5gCVHSdHyIiGqJ9RXrdharHt9XLBFQAlxX1jz2lD5oAkwMGBWwdMNRSJXm3TPX2TqgP-k9bFtXeZITDqQl1aS9IbrYgz7s",
    "L3K6EmBUwOWUJQ4og%3D%3D%22%5D%5D; __gads=ID=ca3603f984e0c3ef:T=1769333432:RT=1769342527:S=ALNI_MalYUAIwBW_-bbVYxBa6sIa2EJLKw; ",
    "__eoi=ID=af42d27622f6c64e:T=1769333432:RT=1769342527:S=AA-AfjabK956GIxTSvgQLpxxYaea; ",
    "_gcl_au=1.1.1648400513.1769333431.1823243669.1769342600.1769342612; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; pa_privacy=%22optin%22; ",
    "pa_user=%7B%22id%22%3A%228246aa30a2265c36238a26c10c58d6d227a374aed1171db579eb7e677fa448db%22%7D; _cb_svref=https%3A%2F%2Fwww.lalsace.fr%2F; ",
    "dicbo_id=%7B%22dicbo_fetch%22%3A1769342614700%7D; _uetsid=7d8152f0f9d011f087deb7014c251b67; _uetvid=7d816590f9d011f0a1a4f76cb8577de8; ",
    "_chartbeat2=.1769333430367.1769342761358.1.Dfsjy0DC_8_h3HEgqC1m2onBi9Iqe.2; ",
    "ABTastySession=mrasn=&lp=https%253A%252F%252Fwww.lalsace.fr%252Fpolitique%252F2025%252F01%252F31%252Ffrederic-marquet-travaille-a-la-possibilite-d-un-projet-pour-",
    "les-municipales-de-2026; ABTasty=uid=5svw99t7fp8v4zv3&fst=1769333430654&pst=1769333430654&cst=1769342037036&ns=2&pvt=14&pvis=4&th=692669.859303.7.7.1.1.1769333504",
    "986.1769333538671.1.1_1566046.1951403.10.2.2.1.1769333431091.1769342526751.0.2_1572478.1959819.2.2.1.1.1769333494564.1769333505027.0.1; _MFB_=fHw1fHx8W118fHx8; ",
    "cto_bundle=y36C6V8lMkI1MkZZYlg2ZEpaRHFPME9mSk9hT2paMzdYQ1BGalVxVEFVeUM3U2QlMkY2b1laSHJIMFZkV1Jab2ZScklBTXBhZDBkYWJNcHdJNEY3dkdLd01IZkl3Tm43MEFFb0clMkI5UEd6V3dORDZ",
    "0d0lpOXYyVWh1WUgxWjR2Ym1WdGM1YjhOZXA3dk9UJTJGZXRBOWhCc2g2ekh4WDEwZyUzRCUzRDsg",
    ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98D1B5FBA5ED6F75DA2154C170A9B4FB92EA4CB0D6C81A40A52AD65AFB0727966F889410319B10A8C773401B0F9280B6BF20264DF3EA440622DF6D13D47CDEC7896F16746ABAED0F1F3FEC70E833EA8A0FFCAC61D00E10F34726A4D44BA894564322F789D394D318E5EDB13B744BCA1A621315F8B74A54E0C6A8636136CD45368AEA175711CAB86E75CF690BBF6AD1B37BD62F10BE676CDF76CCD5C7CD6C59E8BA2D4D2CBAD05364649D21AB1BBD0EAE80047DD67C905325F3FDD2D3696B087AC21E52B2DBF1AB9D79F4809DA722B217CA2352E5001B33071CE388D1CAC0D055FD2"
]
COOKIES_RAW = "".join(C)

def fetch_content(url):
    try:
        time.sleep(random.uniform(1.0, 3.0))
        headers = {
            "Cookie": COOKIES_RAW,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.lalsace.fr/",
        }
        
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=30)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        text_parts = []
        
        # Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())

        # Corps (Détection large)
        elements = soup.select('.textComponent p, .paywall2 p, .article-content p')
        for el in elements:
            txt = el.get_text().strip()
            if len(txt) > 25 and txt not in text_parts:
                text_parts.append(txt)

        if text_parts:
            return "\n\n".join(text_parts)
        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper L'Alsace Novembre 2025 (Mode Split Strings)...")
    
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    conn = psycopg2.connect(clean_url)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE source ILIKE '%Alsace%' 
          AND \"publishedAt\" >= '2025-11-01' AND \"publishedAt\" < '2025-12-01'
          AND (content IS NULL OR LENGTH(content) < 500)
        ORDER BY \"publishedAt\" DESC
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article à traiter.")
        return

    print(f"[*] {len(articles)} articles à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        content = fetch_content(link)
        
        if content and len(content) > 400:
            try:
                cur.execute('UPDATE \"Article\" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                print(f"   ✅ OK ({len(content)} chars)")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Erreur BDD: {e}")
                conn.rollback()
        else:
            len_c = len(content) if content else 0
            print(f"   ⚠️ Échec ou court ({len_c} chars).")

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {success_count} articles mis à jour.")

if __name__ == "__main__":
    main()
