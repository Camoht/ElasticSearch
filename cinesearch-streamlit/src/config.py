"""
config.py — C'est le fichier de configuration centrale du projet CinéSearch.

Il contient : Les paramètres de connexion Elasticsearch, le nom de l'index,
              et la création du mapping.
"""

import time
from elasticsearch import Elasticsearch

# ── Paramètres de connexion ────────────────────────────────────────────────────
# Après
import os
ES_HOST = os.environ.get("ELASTICSEARCH_HOST", "http://localhost:9200")
INDEX_NAME = "movies"
REQUEST_TIMEOUT = 30

# ── Mapping de l'index movies ──────────────────────────────────────────────────
# Source : cours Chapitre 5.7 et tableau Chapitre 2.5.
MOVIES_MAPPING = {
    "properties": {
        "title": {
            "type": "text",
            "analyzer": "standard",
            # Multi-field : full-text (standard) + agrégations exactes (keyword).
            "fields": {
                "keyword": {"type": "keyword"}
            }
        },
        "directors": {
            "type": "text",
            # Multi-field : full-text ET agrégations (cours Partie 1.2).
            "fields": {
                "keyword": {"type": "keyword"}
            }
        },
        "actors": {
            "type": "text",
            # Multi-field : full-text ET agrégations (cours Partie 1.2).
            "fields": {
                "keyword": {"type": "keyword"}
            }
        },
        "genres": {
            # keyword pur : valeurs exactes pour filtrage et agrégations.
            "type": "keyword"
        },
        "year": {
            # Année de sortie du film.
            "type": "integer"
        },
        "rating": {
            # Note moyenne du film (ex: 8.8).
            "type": "float"
        },
        "rank": {
            # Classement du film dans le dataset (ex: 1 pour le meilleur film).
            "type": "integer"
        },
        "release_date": {
            # Date de sortie du film au format ISO 8601.
            "type": "date"
        },
        "plot": {
            # Synopsis du film avec Analyzer anglais pour stemming EN (cours Chapitre 2.6 + 5.7).
            "type": "text",
            "analyzer": "english",
            "fielddata": True
        },
        "running_time_secs": {
            # Durée du film en secondes (ex: 8520 pour 2h22).
            "type": "integer"
        },
        "image_url": {
            # URL de l'affiche du film (stocké mais non indexé).
            "type": "keyword",
            "index": False   # Non indexé : stocké mais non recherchable (cours 5.7).
        }
    }
}


# ── Fonctions utilitaires ──────────────────────────────────────────────────────

def get_es_client() -> Elasticsearch:
    """
    Cette fonction retourne un client Elasticsearch connecté à ES_HOST.
    Le paramètre "request_timeout" est défini pour éviter les timeouts lors de l'attente d'ES.
    """
    return Elasticsearch(ES_HOST, request_timeout=REQUEST_TIMEOUT)


def wait_for_elasticsearch(es: Elasticsearch, max_retries: int = 30) -> bool:
    """
    Cette fonction attend qu'Elasticsearch soit prêt (qu'il est démarré) avant de continuer.
    
    Elle retourne "True" si ES est disponible, "False" si le timeout est atteint.
    """
    print(f"="*80)
    print(f"\n⏳ Connexion à Elasticsearch en cours...")
    for i in range(max_retries):
        try:
            es.info()
            print("    ✅ Elasticsearch est prêt !")
            return True
        except Exception:
            print(f"    En attente d'Elasticsearch... ({i + 1}/{max_retries})")
            time.sleep(2)
    print("    ❌ Elasticsearch n'est pas disponible après le délai d'attente.")
    return False


def create_index(es: Elasticsearch, index_name: str = INDEX_NAME) -> None:
    """
    Cette fonction créer l'index "movies" avec le mapping défini ci-dessus.
    On utilise la syntaxe ES 8.x : es.indices.create(index=..., mappings=...)  (cours 5.7)
    """
    # Suppression de l'index déjà existant pour repartir propre.
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
        print(f"    🗑️  Index '{index_name}' existant supprimé.")

    # Création de l'indexavec le mapping défini au dessous (syntaxe ES 8.x, paramètres nommés).
    es.indices.create(index=index_name, mappings=MOVIES_MAPPING)
    print(f"    ✅ Index '{index_name}' créé avec succès !")

    # Vérification du mappingvia l'API _mapping.
    mapping_result = es.indices.get_mapping(index=index_name)
    props = mapping_result[index_name]["mappings"]["properties"]
    print(f"\n📋 Mapping appliqué ({len(props)} champs) :")
    for field, config in props.items():     # Afficher un résumé visuel du mapping.
        ftype = config.get("type", "object")
        subfields = list(config.get("fields", {}).keys())
        not_indexed = " [non indexé]" if config.get("index") is False else ""
        suffix = f" + {subfields}" if subfields else ""
        print(f"   {field:25s} → {ftype}{suffix}{not_indexed}")


# ── Point d'entrée autonome ────────────────────────────────────────────────────
if __name__ == "__main__":
    es = get_es_client()
    if wait_for_elasticsearch(es):
        create_index(es)


# ── Commandes ──────────────────────────────────────────────────────────────────
#
#   Installer la bonne version du client (ES 8.x) :
#       --> pip install "elasticsearch>=8.0.0,<9.0.0"
#
#   Créer l'index avec le mapping :
#       --> python src/config.py
#
#   Vérifier que l'index existe (dans Kibana Dev Tools) :
#       --> GET /movies/_mapping
#
#   Supprimer l'index si besoin de recommencer (dans Kibana Dev Tools) :
#       --> DELETE /movies
#
#   (Les commandes Kibana s'exécutent dans http://localhost:5601 > Dev Tools)
# ───────────────────────────────────────────────────────────────────────────────