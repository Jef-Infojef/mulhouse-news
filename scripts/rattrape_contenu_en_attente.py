"""Vide le stock d'articles L'Alsace en attente de contenu, avec avancement.

Le cron `scrape-news` ne traite qu'un lot par passage, et l'archive remonte à
2006 : plusieurs milliers d'articles ont un titre, un lien et une date, mais
pas de texte. Ils ont été découverts par les sitemaps journaliers et jamais
rouverts. Rien n'est récupérable ailleurs — vérifié sur l'export Convex du
30/08/2026, ces articles y sont vides aussi.

CE QUE CE SCRIPT NE PEUT PAS RATTRAPER, et c'est l'essentiel du stock :
`fetch_grdc_content` rejette tout corps de moins de 400 caractères, pour ne
pas ranger l'amorce gratuite d'un article payant à la place de l'article.
Mesure du 16/09/2026 sur 30 articles tirés au hasard dans ce stock : corps
réel de 186 caractères en médiane, et AUCUN au-dessus de 400. Les brèves
d'archive — résultats sportifs, questions du jour, annonces locales de
2009-2019 — sont donc sous le seuil par nature, et le resteront.

Le stock de ~5 400 articles lalsace.fr sans texte n'est pas un retard de
scraping : c'est un plancher. Ce script sert à rattraper ce qui arrive
vraiment à passer — l'actualité récente, les articles complets — pas à vider
un compteur qui ne descendra plus.

Ce script fait à la main ce que le cron ferait s'il tournait en continu :

  1. `scrape_content_full --archive` ouvre les articles sans texte (API interne
     GRDC) et consigne ce qu'il lit dans le journal RAG ;
  2. `rag_sync_articles --journal` déverse ce journal dans `Article` et
     `KnowledgeChunk` sur l'Aiven.

L'étape 2 n'est pas optionnelle : depuis que Convex est coupé, le scraper de
contenu n'écrit plus nulle part d'autre que le journal. Sans elle, le texte
récupéré serait perdu en fin de run — et le chat ne le verrait pas non plus.

Usage:
  python scripts/rattrape_contenu_en_attente.py --compter       # ne fait rien
  python scripts/rattrape_contenu_en_attente.py --tout          # vide le stock
  python scripts/rattrape_contenu_en_attente.py --tout --max 500
  python scripts/rattrape_contenu_en_attente.py --limit 50      # un seul lot

Ctrl+C : le lot en cours est perdu, pas les précédents. Le script est
reprenable tel quel, la liste de travail étant relue en base à chaque lot.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

import psycopg2
from dotenv import load_dotenv

_racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _env in (".envenv", ".env.local", ".env"):
    load_dotenv(os.path.join(_racine, _env))

# Même critère que `aiven_client.articles_sans_contenu` : sous 150 caractères,
# il n'y a qu'un chapô, pas un article.
STOCK_SQL = (
    'SELECT count(*) FROM "Article" '
    "WHERE hidden = false AND link LIKE %s "
    "  AND (content IS NULL OR length(content) < 150)"
)
CLE_COOLDOWN = "SCRAPE_CONTENT_RETRY_COOLDOWNS"


def stock(cur, recent_seulement: bool = False) -> int:
    sql, args = STOCK_SQL, ["%lalsace.fr%"]
    if recent_seulement:
        sql += ' AND "publishedAt" > NOW() - INTERVAL %s'
        args.append("30 days")
    cur.execute(sql, args)
    return cur.fetchone()[0]


def cooldowns_actifs(cur) -> int:
    """Combien d'articles sont encore sous cooldown.

    Ils restent en tête de la liste ASC et sont ignorés sans requête HTTP : un
    lot de 50 qui tombe sur 50 cooldowns n'avance à rien. On élargit donc la
    fenêtre d'autant. Compter ici, plutôt que déduire l'écart entre le lot
    demandé et les gains, évite de confondre « déjà jugé sans corps » et
    « échec du jour ».
    """
    cur.execute('SELECT value FROM "AppConfig" WHERE key = %s', (CLE_COOLDOWN,))
    ligne = cur.fetchone()
    if not ligne or not ligne[0]:
        return 0
    try:
        donnees = json.loads(ligne[0])
    except Exception:
        return 0
    maintenant, actifs = datetime.now(), 0
    for valeur in donnees.values():
        brut = valeur.get("until") if isinstance(valeur, dict) else valeur
        try:
            if datetime.fromisoformat(str(brut).replace("Z", "")) > maintenant:
                actifs += 1
        except Exception:
            continue
    return actifs


def duree(secondes: float) -> str:
    if secondes != secondes or secondes < 0 or secondes > 86400 * 30:
        return "?"
    s = int(secondes)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m{s % 60:02d}"
    return f"{s // 3600}h{(s % 3600) // 60:02d}"


class Avancement:
    """Ligne d'avancement réécrite en place : débit, reste, heure de fin.

    Trois compteurs distincts, parce qu'ils ne coûtent pas le même temps :
    un article rempli demande deux requêtes, un article sans corps une seule,
    et un article déjà jugé lors d'un passage précédent aucune. Les mélanger
    donnerait un ETA qui s'effondre dès qu'on traverse une série de brèves.
    """

    def __init__(self, objectif: int):
        self.objectif = max(objectif, 1)
        self.faits = 0
        self.vides = 0
        self.ignores = 0
        self.debut = time.time()
        self._dernier = 0.0

    def tick(self, genre: str):
        if genre == "rempli":
            self.faits += 1
        elif genre == "vide":
            self.vides += 1
        else:
            self.ignores += 1
        self.afficher()

    def afficher(self, force: bool = False):
        maintenant = time.time()
        if not force and maintenant - self._dernier < 0.4:
            return
        self._dernier = maintenant

        ecoule = maintenant - self.debut
        traites = self.faits + self.vides
        pct = 100.0 * traites / self.objectif
        largeur = 26
        plein = min(largeur, int(largeur * traites / self.objectif))
        barre = "#" * plein + "." * (largeur - plein)

        if traites >= 3 and ecoule > 5:
            debit = traites / ecoule
            secondes = (self.objectif - traites) / debit
            reste = duree(secondes)
            fin = (datetime.now() + timedelta(seconds=secondes)).strftime("%H:%M")
            vitesse = f"{debit * 60:.0f}/min"
        else:
            reste, fin, vitesse = "...", "--:--", "..."

        deja = f", {self.ignores} deja juges" if self.ignores else ""
        ligne = (f"  [{barre}] {traites}/{self.objectif} ({pct:4.1f}%)  "
                 f"{self.faits} remplis, {self.vides} sans corps{deja}  "
                 f"{vitesse}  reste {reste}  fin ~{fin}")
        sys.stdout.write(chr(13) + ligne[:158].ljust(158))
        sys.stdout.flush()


def lancer_lot(fenetre: int, ordre: str, env: dict, av: Avancement) -> None:
    """Un lot d'ouvertures, la sortie du scraper étant lue au fil de l'eau.

    C'est la seule façon de montrer l'avancement PENDANT un lot plutôt
    qu'entre deux lots : un lot de 50 dure plusieurs minutes.
    """
    cmd = [sys.executable, "-u", "scripts/scrape_content_full.py", "--archive",
           "--limit", str(fenetre), "--order", ordre, "--worklist-aiven"]
    p = subprocess.Popen(cmd, cwd=_racine, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                         errors="replace", bufsize=1)
    for ligne in p.stdout:
        if "[GRDC] Contenu complet" in ligne:
            av.tick("rempli")
        elif ("Contenu trop court" in ligne or "Contenu partiel refus" in ligne
                or "Mode non-abonn" in ligne):
            av.tick("vide")
        elif "En cooldown jusqu" in ligne:
            av.tick("cooldown")
    p.wait()


def indexer(env: dict, journal: str) -> None:
    """Journal -> Article + KnowledgeChunk. Silencieux sauf échec."""
    r = subprocess.run(
        [sys.executable, "scripts/rag_sync_articles.py", "--journal", journal,
         "--journal-only"],
        cwd=_racine, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(os.linesep + "  [!] indexation en echec : "
              + (r.stdout or "").strip()[-300:])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tout", action="store_true", help="boucler jusqu'a epuisement")
    p.add_argument("--lot", type=int, default=50, help="articles par lot (defaut 50)")
    p.add_argument("--limit", type=int, default=0, help="un seul lot de N articles")
    p.add_argument("--max", type=int, default=0, help="s'arreter apres N traites")
    p.add_argument("--order", choices=["desc", "asc"], default="asc",
                   help="asc : les plus anciens d'abord (defaut archive)")
    p.add_argument("--compter", action="store_true", help="afficher le stock et sortir")
    args = p.parse_args()

    if not os.environ.get("RAG_DATABASE_URL"):
        print("RAG_DATABASE_URL manquant : c'est la base qui fait autorite.",
              file=sys.stderr)
        return 1

    conn = psycopg2.connect(os.environ["RAG_DATABASE_URL"])
    conn.autocommit = True
    cur = conn.cursor()

    depart = stock(cur)
    recent = stock(cur, True)
    gel = cooldowns_actifs(cur)
    print(f"Stock L'Alsace sans contenu : {depart}, dont {recent} publies dans "
          f"les 30 derniers jours")
    if gel:
        print(f"  {gel} deja juges sans corps, en cooldown : ignores sans requete")
    # Le gros du stock est constitue de breves sous le seuil de 400 caracteres
    # de fetch_grdc_content : les rouvrir ne donnera rien. Le dire ici evite de
    # lancer un run de plusieurs heures en esperant voir le compteur descendre.
    if depart - recent > 500:
        print(f"  ATTENTION : ~{depart - recent} articles d'archive dont le corps")
        print("  est sous les 400 caracteres exiges. Ils seront rouverts puis")
        print("  rejetes : c'est un plancher, pas un retard. Viser --order desc")
        print("  pour ne travailler que sur l'actualite recente.")
    if args.compter:
        return 0

    objectif = min(args.limit or args.max or depart, depart)
    lot = args.limit or args.lot
    print(f"Objectif : {objectif} articles, lots de {lot}, ordre {args.order}")
    print("Ctrl+C pour arreter : le lot en cours est perdu, pas les precedents.")
    print()

    env = dict(os.environ)
    env["USE_CONVEX"] = "1"
    journal = os.path.join(_racine, "rag-journal.jsonl")
    env["RAG_JOURNAL_PATH"] = journal
    if os.path.exists(journal):
        os.replace(journal, journal + ".precedent")

    av = Avancement(objectif)
    debut = time.time()
    interrompu = False
    steriles = 0

    try:
        while True:
            avant = stock(cur)
            if avant == 0:
                break
            # Fenetre = le lot voulu, plus les cooldowns qui seront sautes sans
            # requete. Plafonnee : au-dela, lire la liste coute plus qu'elle ne
            # rapporte.
            lancer_lot(min(lot + cooldowns_actifs(cur), 1000), args.order, env, av)
            indexer(env, journal)
            open(journal, "w", encoding="utf-8").close()

            steriles = steriles + 1 if stock(cur) == avant else 0
            if not args.tout:
                break
            if args.max and (av.faits + av.vides) >= args.max:
                break
            if steriles >= 3:
                print(os.linesep + "  [i] trois lots sans gain : le reste est "
                      "sans corps ou en cooldown (7 jours).")
                break
    except KeyboardInterrupt:
        interrompu = True

    av.afficher(force=True)
    restant = stock(cur)
    print(os.linesep)
    print("=== bilan" + (" (interrompu)" if interrompu else "") + " ===")
    print(f"  duree      : {duree(time.time() - debut)}")
    print(f"  remplis    : {depart - restant}")
    print(f"  sans corps : {av.vides}")
    print(f"  stock      : {depart} -> {restant}")
    if restant:
        print(f"  relancer   : python scripts/{os.path.basename(__file__)} --tout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
