# CR — Doublons DNA / L'Alsace dans la base

**Date :** 17/08/2026
**Base :** Supabase PostgreSQL (table `Article`, 27 104 articles au total)

## 1. Constat principal

**DNA et L'Alsace sont les deux éditions d'un même groupe de presse (EBRA) : les articles publiés sur `dna.fr` sont systématiquement repris à l'identique sur `lalsace.fr`** (même titre, même chemin d'URL, seul le domaine change). Le scraper importe les deux flux, et la contrainte d'unicité sur `link` ne détecte rien car les URLs diffèrent (domaine).

### Chiffres clés

| Type | Nombre |
|---|---|
| Articles DNA (famille) | 2 142 |
| Articles L'Alsace (famille) | 9 706 |
| **Paires croisées DNA ↔ L'Alsace (même article)** | **543** |
| — dont chemin d'URL strictement identique (doublon garanti) | 473 |
| — dont slug légèrement différent (même article à ~99 %) | 70 |
| Doublons intra DNA (2 liens DNA pour le même article) | 1 |
| Doublons intra L'Alsace (2 liens lalsace.fr pour le même article) | 14 |
| **Total doublons « en trop » (si on garde 1 exemplaire sur 2)** | **~558** |

### Répartition par année (paires croisées)

| Année | Paires |
|---|---|
| 2012 | 1 |
| 2017 | 1 |
| 2018 | 9 |
| 2019 | 17 |
| 2020 | 17 |
| 2021 | 12 |
| 2022 | 5 |
| 2025 | 1 |
| **2026** | **480** |

→ **Le problème est massif et récent** : 480 doublons sur 543 datent de 2026, ce qui suggère que le flux EBRA (ou sa fréquence de scraping) a changé en 2026.

## 2. Détail des cas particuliers

### 2.1 Champ `source` non normalisé (cause racine n°1)
`source` contient 5 orthographes pour DNA et 2 pour L'Alsace :
- DNA : `DNA` (1 467), `DNA.fr` (599), `Dna.fr` (41), `dna.fr` (20), `DNA - Les Dernières Nouvelles d'Alsace` (30)
- L'Alsace : `L'Alsace` (9 585), `lalsace.fr` (121)

### 2.2 Intra L'Alsace : 4 paires `c.lalsace.fr` vs `www.lalsace.fr`
Même article, domaine `c.` vs `www.` (Lyddy, Bontà Italiana, Manka, Dirringer, Habib Diarra).

### 2.3 Faux positifs à vérifier avant suppression (~4 cas)
Quelques paires ont des titres identiques mais semblent être des **publications récurrentes distinctes** :
- « Rendez-vous famille avec Laurence Mellinger » (21/03 vs 18/04 — 2 dates différentes)
- « La foire-kermesse de Mulhouse est installée… » (2018 vs 2019)
- « Diaporama. La semaine écoulée vue par nos photographes » (08/03 vs 03/05)

## 3. Recommandations

1. **Dédupliquer l'existant** : pour chaque paire, conserver l'article L'Alsace (le plus ancien/le plus riche ?) et supprimer l'article DNA en cascade (les `ArticleImage`/`ArticleGoogleTag` sont en `onDelete: Cascade`), **ou** marquer les doublons `hidden = true` (moins destructif, réversible).
2. **Corriger le scraper** : ne plus importer les articles dont l'URL slug existe déjà chez l'autre domaine EBRA (déduplication par slug de chemin plutôt que par URL complète), et normaliser `source` (une seule orthographe par titre).
3. **À terme** : ne garder qu'un des deux flux (dna.fr ou lalsace.fr) — le contenu étant le même, importer les deux n'apporte rien.

## 4. Scripts d'analyse utilisés
Détection par titre normalisé (accents/punctuation ignorés, suffixe `- DNA` / `- L'Alsace` retiré du titre) puis croisement des liens.