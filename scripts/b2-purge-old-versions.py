"""Purge les ANCIENNES VERSIONS de fichiers du compte Backblaze B2
(les versions courantes sont conservées).

Le compte dépasse légèrement les 10 Go gratuits à cause des vieilles
versions de `asso-franklin-turso`, ce qui déclenche le blocage
« storage cap exceeded » sur tous les uploads.

Usage :
    python scripts/b2-purge-old-versions.py            # aperçu seul
    python scripts/b2-purge-old-versions.py --apply    # suppression réelle
    python scripts/b2-purge-old-versions.py --bucket asso-franklin-turso --apply
"""

import argparse
import os
import sys

from b2sdk.v2 import InMemoryAccountInfo, B2Api

ENV_PATH = r"C:\dev\mulhouse-news\.env"


def load_keys():
    key_id = key = None
    for line in open(ENV_PATH, encoding="utf-8"):
        if line.startswith("B2_APPLICATION_KEY_ID="):
            key_id = line.split("=", 1)[1].strip()
        elif line.startswith("B2_APPLICATION_KEY="):
            key = line.split("=", 1)[1].strip()
    return key_id, key


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge des anciennes versions B2")
    parser.add_argument("--apply", action="store_true", help="Supprime réellement (sinon aperçu)")
    parser.add_argument("--bucket", type=str, default=None, help="Limiter à un bucket")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    key_id, key = load_keys()
    api = B2Api(InMemoryAccountInfo())
    api.authorize_account("production", key_id, key)

    total_gain = 0
    for bucket in api.list_buckets():
        if args.bucket and bucket.name != args.bucket:
            continue
        # ls renvoie les versions par nom, de la plus récente à la plus ancienne :
        # la 1re rencontreée pour un nom = version courante.
        courant, n_courant = 0, 0
        vieilles: list = []
        vus: set[str] = set()
        for v, _ in bucket.ls(latest_only=False, recursive=True):
            if v.file_name not in vus:
                vus.add(v.file_name)
                courant += v.size
                n_courant += 1
            else:
                vieilles.append(v)
        taille_vieilles = sum(v.size for v in vieilles)
        print(f"\n{bucket.name}")
        print(f"  versions courantes : {n_courant:>7} fichiers — {courant/1e9:7.2f} Go (conservées)")
        print(f"  anciennes versions : {len(vieilles):>7} fichiers — {taille_vieilles/1e9:7.2f} Go "
              f"{'→ SUPPRESSION' if args.apply else '→ seraient supprimées'}")
        total_gain += taille_vieilles

        if args.apply and vieilles:
            done = 0
            for v in vieilles:
                api.delete_file_version(v.id_, v.file_name)
                done += 1
                if done % 50 == 0:
                    print(f"    … {done}/{len(vieilles)} supprimées")

    print(f"\nGain total : {total_gain/1e9:.2f} Go"
          + ("" if args.apply else " (aperçu — relancer avec --apply pour supprimer)"))


if __name__ == "__main__":
    main()
