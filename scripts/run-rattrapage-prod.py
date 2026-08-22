"""Wrapper : charge les identifiants Convex PROD (MulhouseGPT) puis lance
rattrape_alsace_mulhouse.py avec les arguments passés.

    python scripts/run-rattrapage-prod.py --start 2011-12-01 --end 2011-12-31
"""

import os
import sys
from pathlib import Path

NEWS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEWS_ROOT / "scripts"))

from dotenv import load_dotenv

load_dotenv(r"C:\dev\MulhouseGPT\.env.local", override=True)

import convex_client  # noqa: E402

if not convex_client.use_convex():
    print("❌ Convex non configuré")
    sys.exit(1)
print(f"[*] Déploiement : {convex_client.get_convex_url()}")

import runpy

runpy.run_path(str(NEWS_ROOT / "scripts" / "rattrape_alsace_mulhouse.py"), run_name="__main__")
