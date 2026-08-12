import os
import re
import fitz  # PyMuPDF

def extract_date_from_pdf(filepath):
    try:
        doc = fitz.open(filepath)
        if doc.page_count > 0:
            # On extrait le texte des 2 premières pages car la date est souvent sur la couverture ou le sommaire
            text = ""
            for i in range(min(2, doc.page_count)):
                text += doc[i].get_text()
            
            # Patterns possibles : 
            # "mars/avril/mai 2021"
            # "printemps 2025"
            # "Hiver 2025-2026"
            # "juin/juillet/août 2021"
            
            # On cherche des mots clés de mois ou saisons suivis d'une année
            months = "janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre|janv|fév|sept|oct|nov|déc"
            seasons = "printemps|été|Automne|hiver"
            pattern = rf"(({months}|{seasons}).*?\d{{4}})"
            
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                date_str = match.group(1).replace("\n", " ").strip()
                # Nettoyage simple
                date_str = re.sub(r'\s+', ' ', date_str)
                return date_str
        return None
    except Exception as e:
        return f"Error: {e}"

folder = "M+Mag"
files = sorted([f for f in os.listdir(folder) if f.startswith("MM") and f.endswith(".pdf")])

print("| Fichier | Date extraite |")
print("|---|---|")
for f in files:
    date = extract_date_from_pdf(os.path.join(folder, f))
    print(f"| {f} | {date} |")
