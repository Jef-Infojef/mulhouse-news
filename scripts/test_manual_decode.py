import base64
import re

def manual_decode(google_url):
    try:
        # L'URL est de la forme https://news.google.com/rss/articles/CBMi...
        # On extrait la partie après /articles/
        match = re.search(r'articles/([^?]+)', google_url)
        if not match:
            return google_url
        
        encoded_str = match.group(1)
        
        # Le format CBMi... est un encodage spécifique. 
        # Souvent, l'URL réelle commence après quelques octets de métadonnées.
        # On va essayer de décoder le base64 et chercher une URL.
        
        # Padding si nécessaire
        missing_padding = len(encoded_str) % 4
        if missing_padding:
            encoded_str += '=' * (4 - missing_padding)
            
        decoded_bytes = base64.urlsafe_b64decode(encoded_str)
        
        # On cherche une chaîne qui ressemble à une URL dans les octets décodés
        # Les URL commencent souvent par http
        decoded_text = ""
        try:
            # On essaye plusieurs encodages
            decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
        except:
            return google_url

        # Recherche de motifs http
        url_match = re.search(r'https?://[^\s\x00-\x1f\x7f-\x9f<>"]+', decoded_text)
        if url_match:
            return url_match.group(0)
            
        return google_url
    except Exception as e:
        return google_url

# Test avec un de tes liens
test_link = "https://news.google.com/rss/articles/CBMikwFBVV95cUxQMWFIOU5iSy1FMGNtR0JaSkp6eTN5UlR5Skk0WmFJZTk2cXVYc0xJN19HWXAtUFBndUItcW9xbVM0LVZNMFFuVF96SmlXMUNoc0lISzhMa1dpQWJNbm1VQWxxWW8wdG5FcVl3bk9SUExhWWJiWkkzWVEwcVdMOG80WjRwOEJqZ3FmRlFoY2ZYd1hEeFE?oc=5"
print(f"Test décodage manuel : {manual_decode(test_link)}")
