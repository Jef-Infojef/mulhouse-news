import os

folder = "M+Mag"

# Règles de remplacement (ordre important pour éviter les conflits)
replacements = {
    "mars-avril-mai": "printemps",
    "avril-mai-juin": "printemps",
    "juillet-août-septembre": "été",
    "octobre-novembre-décembre": "automne",
    "_décembre_": "_hiver_", # Pour les numéros de décembre seul
    "janvier-février-mars": "hiver"
}

print("--- Harmonisation des noms de fichiers ---")

for filename in os.listdir(folder):
    if not filename.endswith(".pdf"):
        continue

    new_name = filename
    for old_pattern, new_pattern in replacements.items():
        if old_pattern in new_name:
            new_name = new_name.replace(old_pattern, new_pattern)
    
    # Correction spécifique pour s'assurer que décembre_202X devient hiver_202X
    # (Le pattern _décembre_ ci-dessus gère le milieu, mais on vérifie)
    
    if new_name != filename:
        old_path = os.path.join(folder, filename)
        new_path = os.path.join(folder, new_name)
        
        # Vérification si le fichier cible existe déjà
        if os.path.exists(new_path):
             print(f"[SKIP] {new_name} existe déjà.")
        else:
            os.rename(old_path, new_path)
            print(f"[OK] {filename} -> {new_name}")

print("Terminé.")
