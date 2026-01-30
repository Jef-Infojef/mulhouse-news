# 📘 Documentation Technique - Mulhouse News

Ce document détaille l'architecture technique, le pipeline d'automatisation et les processus de récupération de données (scraping) du projet Mulhouse News.

---

## 1. Vue d'ensemble de l'Architecture

Le projet fonctionne sur une architecture hybride **Next.js + Python** :

*   **Frontend & API :** Next.js (App Router) hébergé sur **Vercel**.
*   **Base de Données :** PostgreSQL géré par **Neon** (Serverless Postgres).
*   **Stockage Images :** **Backblaze B2** (Object Storage S3-compatible).
*   **Moteur de Scraping :** Scripts Python exécutés via **GitHub Actions**.
*   **Orchestration :** Déclencheur externe via **cron-job.org**.

---

## 2. Système d'Automatisation (Cron Job)

Pour garantir une fraîcheur des données en temps réel (actualisation toutes les 5 minutes), nous contournons le planificateur natif de GitHub (trop imprécis) au profit d'un déclencheur externe.

### Flux d'Exécution
1.  **Le Déclencheur (Cron-job.org)** :
    *   Toutes les **5 minutes**, `cron-job.org` envoie une requête HTTP `POST` authentifiée.
    *   **Cible :** API GitHub (`api.github.com/repos/.../dispatches`).
    *   **Authentification :** Token personnel GitHub (PAT) avec droits `repo`.

2.  **Le Récepteur (GitHub Actions)** :
    *   GitHub reçoit l'événement `workflow_dispatch`.
    *   Il démarre immédiatement le workflow défini dans `.github/workflows/scrape-news.yml`.

3.  **L'Exécution (Runner Ubuntu)** :
    *   Installe Python 3.11 et Node.js.
    *   Installe les dépendances (`requests`, `beautifulsoup4`, `curl_cffi`, `prisma`, etc.).
    *   Lance séquentiellement les scripts de scraping.

---

## 3. Pipeline de Scraping (Détail des Scripts)

Le scraping est divisé en deux phases pour optimiser les performances et réduire les appels inutiles.

### Phase 1 : Découverte (`scripts/scrape_and_seed.py`)
*   **Rôle :** Trouver les nouvelles URLs d'articles.
*   **Sources :** Google News (RSS), Flux RSS locaux, Pages d'accueil (DNA, L'Alsace, M+, etc.).
*   **Méthode :**
    *   Récupère les listes d'articles.
    *   Vérifie l'existence de chaque URL en base de données (pour éviter les doublons).
    *   Insère les **nouveaux articles** avec les infos de base (Titre, URL, Date, Source).
    *   *Si aucun nouvel article n'est trouvé, le processus s'arrête souvent ici.*

### Phase 2 : Enrichissement (`scripts/scrape_content_full.py`)
*   **Rôle :** Récupérer le contenu complet et les images pour les articles incomplets.
*   **Cible :** Articles en base où `content` est `NULL`.
*   **Technologie :**
    *   Utilise `curl_cffi` pour simuler un vrai navigateur (Chrome) et contourner les protections anti-bot (Cloudflare, Datadome).
    *   Utilise `GoogleNewsDecoder` pour résoudre les liens Google News obfusqués.
*   **Gestion des Images :**
    *   Télécharge l'image source.
    *   L'upload vers **Backblaze B2**.
    *   Génère une URL publique (CDN) et met à jour l'article en base.

---

## 4. Gestion des Erreurs et Logs

*   **Logs GitHub :** Chaque exécution est visible dans l'onglet "Actions" du dépôt.
*   **Logs Base de Données :**
    *   En cas d'échec critique du script Python, un script de secours (`scripts/log_github_failure.py`) est appelé.
    *   Il enregistre l'erreur dans la table `ScrapingLog` de la base de données.
*   **Interface Admin :** Les logs sont consultables via l'interface web du site (`/admin/logs`).

---

## 5. Configuration Technique Requise

### Variables d'Environnement (Secrets GitHub)
Le bon fonctionnement dépend des clés suivantes dans GitHub Secrets :

*   `DATABASE_URL` : URL de connexion PostgreSQL (Neon).
*   `ALSACE_COOKIES` : Cookies de session (si nécessaire pour accès abonné).
*   `B2_APPLICATION_KEY_ID` & `B2_APPLICATION_KEY` : Identifiants Backblaze.
*   `B2_BUCKET_NAME` : Nom du bucket de stockage.

### Dépendances Clés (Python)
*   `curl_cffi` : Client HTTP impersonnel (imite les navigateurs).
*   `beautifulsoup4` : Parsing HTML.
*   `psycopg2-binary` : Connexion PostgreSQL.
*   `googlenewsdecoder` : Décodage des URLs Google News.

---

## 6. Maintenance

*   **Changement de fréquence :** Modifier le job sur `cron-job.org`.
*   **Arrêt d'urgence :** Désactiver le workflow dans l'onglet Actions de GitHub ou mettre en pause le job sur `cron-job.org`.
*   **Mise à jour des sélecteurs CSS :** Si un site source change son design, il faut mettre à jour les classes CSS dans `scripts/scrape_content_full.py`.
