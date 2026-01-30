import base64
import re

def decode_google_news_url(source_url):
    try:
        match = re.search(r'articles/([^?]+)', source_url)
        if not match: return source_url
        
        encoded_str = match.group(1)
        
        # Base64 decode
        padding = (4 - len(encoded_str) % 4) % 4
        decoded_bytes = base64.urlsafe_b64decode(encoded_str + "=" * padding)
        
        # L'URL réelle est souvent précédée de quelques octets de longueur.
        # Dans le format CBMi, l'URL commence après l'octet 0x08 0x?? 0x22 0x??
        # On va chercher le premier "http"
        
        try:
            # On essaye de trouver "http" dans les octets
            s = decoded_bytes
            # On cherche la séquence http (h=104, t=116, t=116, p=112)
            for i in range(len(s) - 4):
                if s[i] == 104 and s[i+1] == 116 and s[i+2] == 116 and s[i+3] == 112:
                    # On a trouvé le début. Maintenant il faut trouver la fin.
                    # La fin est souvent marquée par un caractère non-imprimable
                    # ou la fin de la chaîne.
                    end = i
                    while end < len(s) and 32 <= s[end] < 127:
                        end += 1
                    return s[i:end].decode('utf-8')
        except:
            pass
            
        return source_url
    except:
        return source_url

# Test avec les liens du 1/10/25
links = [
    "https://news.google.com/rss/articles/CBMikwFBVV95cUxQMWFIOU5iSy1FMGNtR0JaSkp6eTN5UlR5Skk0WmFJZTk2cXVYc0xJN19HWXAtUFBndUItcW9xbVM0LVZNMFFuVF96SmlXMUNoc0lISzhMa1dpQWJNbm1VQWxxWW8wdG5FcVl3bk9SUExhWWJiWkkzWVEwcVdMOG80WjRwOEJqZ3FmRlFoY2ZYd1hEeFE?oc=5",
    "https://news.google.com/rss/articles/CBMi0AFBVV95cUxOV29hSk5abWpJM0xwTGFpMkdqZXY5Z2JkZzE5UHpVSWNYMERtOVA3dXZyVlo5dkN3Vzd6S0RDSlpUM3FlT1hxbDNDa3o3MmNLWmd3V3JCSlpGTGo3VHVnUmdCRjVLcE1WTjVOUzc4cVRtLUsyRW1MZVdieW5GUHE5aEVCUXR0SXBLQTRRcHVPOFB4YjJwYjRRek1Ra3J4XzRjb3BySHlBb2EzeEg1dVZMSkQyZEVrYU1EYmdWT0ljU3cxa2xfZThjQVVYUzFtYUha?oc=5",
    "https://news.google.com/rss/articles/CBMivwFBVV95cUxPQVJpSkpYdnN1ZmRLNWZ3Z3FQVjZKRWd0RGdJQmVRNlpsem9zSGxGUmNHcnpTOEZlYl9EZXZoMzc5c0RQajNmZThrQUFBaW96eVJ5aVJmcjBQeDhBVlRKVzZmeDgybEozelBXVmdVTnEwZDk2MldNbVZoRExJcy01aGl3WUhLOWxjXy15R0x3SXEtaWtvZFZOLXZNUUxrVHQwSnQ5Vk41Z1BKa2w0dzZTUjF5djdMajlTOTNwUlRZdw?oc=5"
]

for l in links:
    print(f"Original: {l[:50]}...")
    print(f"Decoded:  {decode_google_news_url(l)}")
    print("-" * 20)
