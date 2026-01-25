import requests
import re
import html

url = "https://www.lesechos.fr/pme-regions/grand-est/mulhouse-veut-tirer-parti-de-son-port-de-plaisance-2208849"
cookie_val = "97970E87FF01CC9A9FAC842D8A4644DF~000000000000000000000000000000~YAAQh8RNFyDmeCObAQAA8J5gsR4KnigL2GY9yXsAstD2XqPhezpmTszF46xnseO/QVk6Q7QnPjBxyPTuIE/AHCfC/PiUPIXzlWmIO+RSNeHo5dlPADpLlyv0OIvf4GEJzBLhY3pvodRpC3vEtLrtKN2R7ROSrVosegIfB4dlbRHddn7/2fbCrKz5fYuqjVkCG8ug8PgiqJLZKxdWipKFK1tFbdRP7s67ciFHSeXUd82Wy6NdP/SstAa+37zG9dnbgCmWG2XNT6hJFCwf8HJw4KfvCHozcl0x13oaI3O0WYGyJBQvJbHxZ9qaAfVRXW8kSvaC2nPZhU/JSWmTsKj/uP73Crr7v8bRnL9DxhURUpaqGXaJO99d0daSorJ6e3HqMO9spvH/PYVvpCh/ag=="

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
    'Cookie': f'ak_bmsc={cookie_val}',
}

try:
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        html_c = r.text
        # Regex plus permissive pour les meta tags
        # On cherche content="..." n'importe où dans la balise qui a property="og:image"
        m_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\\]+)["\']', html_c)
        if not m_img: m_img = re.search(r'<meta[^>]+content=["\']([^"\\]+)["\'][^>]+property=["\']og:image["\']', html_c)
        
        m_desc = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]*content=["\']([^"\\]+)["\']', html_c)
        if not m_desc: m_desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]*content=["\']([^"\\]+)["\']', html_c)
        
        if m_img: print(f"Image : {m_img.group(1)}")
        if m_desc: print(f"Description : {html.unescape(m_desc.group(1))[:150]}...")
        
        if not m_img and not m_desc:
            print("Métadonnées toujours non trouvées. Recherche brute...")
            # On cherche juste og:image dans le texte pour voir
            if "og:image" in html_c:
                print("og:image est présent dans le texte.")
            if "og:description" in html_c:
                print("og:description est présent dans le texte.")

    else:
        print(f"Status: {r.status_code}")

except Exception as e:
    print(f"Erreur : {e}")