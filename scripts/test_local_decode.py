import base64
import re

def try_decode_locally(google_url):
    print(f"\n[*] Analyse de : {google_url[:60]}...")
    try:
        # 1. Extraction de la partie base64
        if "articles/" in google_url:
            encoded_str = google_url.split("articles/")[1].split("?")[0]
        else:
            encoded_str = google_url

        # 2. Décodage base64 (avec padding correct)
        padding = (4 - len(encoded_str) % 4) % 4
        decoded_bytes = base64.urlsafe_b64decode(encoded_str + "=" * padding)
        
        # 3. Recherche de chaînes de caractères qui ressemblent à des domaines ou URLs
        # On cherche des séquences de caractères imprimables de longueur raisonnable
        # Souvent l'URL est là, mais un peu "sale"
        
        # On cherche tout ce qui ressemble à du texte entre des caractères binaires
        text_chunks = re.findall(b'[a-zA-Z0-9\-\.\/\:\%\&\?\=\_]{10,}', decoded_bytes)
        
        found_urls = []
        for chunk in text_chunks:
            try:
                candidate = chunk.decode('utf-8')
                if candidate.startswith("http") or ("." in candidate and "/" in candidate):
                    found_urls.append(candidate)
            except:
                continue
        
        if found_urls:
            # On prend la plus longue ou celle qui commence par http
            best = max(found_urls, key=len)
            return best
            
        return "Pas d'URL trouvée dans les octets."
    except Exception as e:
        return f"Erreur : {e}"

# Test sur 2 liens différents du 1er octobre
test_links = [
    "https://news.google.com/rss/articles/CBMivwFBVV95cUxPQVJpSkpYdnN1ZmRLNWZ3Z3FQVjZKRWd0RGdJQmVRNlpsem9zSGxGUmNHcnpTOEZlYl9EZXZoMzc5c0RQajNmZThrQUFBaW96eVJ5aVJmcjBQeDhBVlRKVzZmeDgybEozelBXVmdVTnEwZDk2MldNbVZoRExJcy01aGl3WUhLOWxjXy15R0x3SXEtaWtvZFZOLXZNUUxrVHQwSnQ5Vk41Z1BKa2w0dzZTUjF5djdMajlTOTNwUlRZdw?oc=5",
    "https://news.google.com/rss/articles/CBMi0AFBVV95cUxOV29hSk5abWpJM0xwTGFpMkdqZXY5Z2JkZzE5UHpVSWNYMERtOVA3dXZyVlo5dkN3Vzd6S0RDSlpUM3FlT1hxbDNDa3o3MmNLWmd3V3JCSlpGTGo3VHVnUmdCRjVLcE1WTjVOUzc4cVRtLUsyRW1MZVdieW5GUHE5aEVCUXR0SXBLQTRRcHVPOFB4YjJwYjRRek1Ra3J4XzRjb3BySHlBb2EzeEg1dVZMSkQyZEVrYU1EYmdWT0ljU3cxa2xfZThjQVVYUzFtYUha?oc=5"
]

for l in test_links:
    result = try_decode_locally(l)
    print(f"[+] Résultat : {result}")
