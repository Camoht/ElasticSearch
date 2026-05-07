"""
indexer.py — C'est le fichier de chargement et indexation des données CinéSearch.
"""

import json
import os
import time

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from config import get_es_client, wait_for_elasticsearch, INDEX_NAME

# ── Chemin vers le dataset ─────────────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "movies_cleaned_v2.json")
DATA_PATH_UTF8 = os.path.join(os.path.dirname(__file__), "..", "data", "movies_cleaned_v2_utf8.json")


# ── Conversion encodage latin-1 → utf-8 ────────────────────────────────────────
# Le fichier fourni est encodé en latin-1 alors qu'ES attend de l'utf-8.
def convert_encoding(src: str, dst: str) -> None:
    """
    Cette fonction convertit le fichier JSON de latin-1 vers utf-8.
    """
    print(f"="*80)
    print(f"\n⏳ Conversion de l'encodage en cours...")

    if os.path.exists(dst):
        print(f"    ℹ️  Fichier utf-8 déjà existant, conversion ignorée.")
        return
    print("    🔄 Conversion de l'encodage latin-1 → utf-8...")
    with open(src, "r", encoding="latin-1") as f:
        content = f.read()
    with open(dst, "w", encoding="utf-8") as f:
        f.write(content)
    print("    ✅ Conversion terminée.")


# ── Parsing du format bulk et construction des actions ─────────────────────────
# Source : Notebook de Guillaume.
# Format du fichier : lignes alternées méta / document :
#   - Ligne paire → {"index": {"_index": "movies", "_id": 1, ...}}
#   - Ligne impaire → {"fields": {"title": "...", "rating": ...}, "id": "tt..."}
def parse_bulk_file(filepath: str, index_name: str = INDEX_NAME) -> list:
    """
    Cette fonction parse le fichier JSON au format bulk Elasticsearch.
    
    Elle retourne une liste d'actions prêtes pour helpers.bulk().
    """
    actions = []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"    📂 Fichier lu : {len(lines)} lignes détectées.")

    # Lecture par pas de 2 : ligne paire = méta et ligne impaire = document.
    for i in range(0, len(lines), 2):

        # Ignorer les lignes vides.
        if not lines[i].strip():
            continue

        try:
            # Ligne de métadonnées : récupérer l'ID.
            meta = json.loads(lines[i])["index"]
            doc_id = meta.get("_id")

            # Ligne de document : extraire les champs via ["fields"].
            doc = json.loads(lines[i + 1])
            source = doc["fields"]

            actions.append({
                "_index": index_name,
                "_id": doc_id,
                "_source": source
            })

        except (json.JSONDecodeError, KeyError, IndexError):
            # Ignorer les lignes malformées.
            continue

    print(f"    📋 {len(actions)} documents parsés et prêts à l'indexation.")
    return actions


# ── Étape 3 : Indexation bulk ──────────────────────────────────────────────────
# Source : Notebook de Guillaume.
def index_movies(es: Elasticsearch, actions: list) -> None:
    """
    Cette fonction indexe tous les documents dans Elasticsearch via l'API bulk.
    
    Elle affiche une barre de progression et un résumé final.
    """
    if not actions:
        print("❌ Aucun document à indexer.")
        return

    print(f"="*80)
    print(f"\n⏳ Indexation de {len(actions)} films en cours...")
    start = time.time()

    # Indexation par lots avec helpers.bulk() (cours Chapitre 5.4).
    # stats_only=True : retourne (nb_succès, nb_erreurs) au lieu de la liste complète.
    success, errors = bulk(es, actions, stats_only=True, raise_on_error=False)

    elapsed = time.time() - start

    # Résumé final.
    print(f"    ✅ Films indexés avec succès : {success}")
    if errors:
        print(f"    ⚠️  Erreurs rencontrées       : {errors}")
    else:
        print(f"    ✅ Aucune erreur d'indexation.")
    print(f"    ⏱️  Temps total               : {elapsed:.2f}s")
    print(f"{'='*80}")


# ── Étape 4 : Vérification post-indexation ─────────────────────────────────────
# Source : cours Chapitre 5.3 (READ) + énoncé Partie 2.2.
def verify_indexation(es: Elasticsearch, index_name: str = INDEX_NAME) -> None:
    """
    Cette fonction vérifie l'indexation :
      - Compte le nombre de documents indexés (es.count);
      - Affiche un échantillon de 3 documents (es.search);
    """
    # Attendre le refresh ES.
    time.sleep(2)

    # Nombre de documents indexés (énoncé Partie 2.2).
    count = es.count(index=index_name)["count"]
    print(f"\n⏳ Vérification de l'indexation en cours...")
    print(f"\n    📊 Nombre de documents dans l'index '{index_name}' : {count}")
    print(f"="*80)

    # Échantillon de 3 documents pour vérification visuelle (énoncé Partie 2.2).
    print("\n🎬 Échantillon de 3 films indexés :")
    result = es.search(index=index_name, size=3)
    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        title   = src.get("title", "N/A")
        rating  = src.get("rating", "N/A")
        year    = src.get("year", "N/A")
        directors = src.get("directors", [])
        print(f"    🎥 {title} ({year}) — Note : {rating} — Réalisateur(s) : {directors}")

    print(f"="*80)


# ── Point d'entrée ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # 1. Connexion à Elasticsearch.
    es = get_es_client()
    if not wait_for_elasticsearch(es):
        exit(1)

    # 2. Conversion de l'encodage.
    convert_encoding(DATA_PATH, DATA_PATH_UTF8)

    # 3. Parsing du fichier bulk et construction des actions.
    actions = parse_bulk_file(DATA_PATH_UTF8)

    # 4. Indexation bulk dans Elasticsearch.
    index_movies(es, actions)

    # 5. Vérification post-indexation : nombre de documents et échantillon.
    verify_indexation(es)

# ── Commandes ──────────────────────────────────────────────────────────────────
#
#   Lancer l'indexation :
#       --> python src/indexer.py
#
#   Vérifier le nombre de documents (dans Kibana Dev Tools) :
#       --> GET /movies/_count
#
#   Voir un échantillon de documents (dans Kibana Dev Tools) :
#       --> GET /movies/_search
#
#   Vérifier que le mapping est toujours correct (dans Kibana Dev Tools) :
#       --> GET /movies/_mapping
# ───────────────────────────────────────────────────────────────────────────────