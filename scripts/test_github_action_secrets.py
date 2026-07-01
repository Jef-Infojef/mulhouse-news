import os, sys

secrets = {
    "DATABASE_URL": os.environ.get("DATABASE_URL"),
    "ALSACE_COOKIES": os.environ.get("ALSACE_COOKIES"),
    "B2_ENDPOINT": os.environ.get("B2_ENDPOINT"),
    "B2_APPLICATION_KEY_ID": os.environ.get("B2_APPLICATION_KEY_ID"),
    "B2_APPLICATION_KEY": os.environ.get("B2_APPLICATION_KEY"),
    "B2_BUCKET_NAME": os.environ.get("B2_BUCKET_NAME"),
    "B2_PUBLIC_URL": os.environ.get("B2_PUBLIC_URL"),
}

print("=== Vérification des Secrets GitHub ===\n")

missing = []
present = []

for name, value in secrets.items():
    if value and value.strip():
        display = value[:50] + "..." if len(value) > 50 else value
        print(f"✅ {name}: {display}")
        present.append(name)
    else:
        print(f"❌ {name}: NON DÉFINI")
        missing.append(name)

print(f"\n=== Résumé ===")
print(f"✅ Présents: {len(present)}")
if missing:
    print(f"❌ Manquants: {len(missing)} → {', '.join(missing)}")
    sys.exit(1)
else:
    print("✅ Tous les secrets sont correctement définis")
