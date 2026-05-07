"""
analytics.py — C'est le fichier des agrégations et statistiques CinéSearch.
"""
 
from elasticsearch import Elasticsearch
from config import get_es_client, wait_for_elasticsearch, INDEX_NAME
from colorama import Fore, Style


# ── 4.1 Analyses globales ──────────────────────────────────────────────────────

# ── Statistiques globales des films ────────────────────────────────────────────
def global_stats(es, index="movies"):
    """
    Cette fonction calcule les statistiques globales du dataset.
    """
    aggs = {
        "avg_rating":   {"avg":        {"field": "rating"}},
        "min_rating":   {"min":        {"field": "rating"}},
        "max_rating":   {"max":        {"field": "rating"}},
        "quartiles":    {"percentiles": {"field": "rating", "percents": [25, 50, 75]}},
        "best_movie":   {"top_hits":   {"sort": [{"rating": {"order": "desc"}}], "_source": ["title", "rating"], "size": 1}},
        "worst_movie":  {"top_hits":   {"sort": [{"rating": {"order": "asc"}}],  "_source": ["title", "rating"], "size": 1}},
    }
    result = es.search(index=index, size=0, aggs=aggs)

    agg   = result["aggregations"]
    total = result["hits"]["total"]["value"]
    avg   = result["aggregations"]["avg_rating"]["value"]
    min_r = result["aggregations"]["min_rating"]["value"]
    max_r = result["aggregations"]["max_rating"]["value"]

    # Statistiques de base.
    print(f"\nStatistiques globales :")
    print(f"🎬 Total de films : {total}")
    print(f"⭐ Note moyenne   : {avg:.2f}")
    print(f"🔼 Note minimale  : {min_r:.2f}")
    print(f"🔽 Note maximale  : {max_r:.2f}")

    # Quartiles.
    q = agg["quartiles"]["values"]
    print(f"\nQuartiles :")
    print(f"  Q1 (25%) : {q['25.0']:.2f}")
    print(f"  Q2 (50%) : {q['50.0']:.2f}")
    print(f"  Q3 (75%) : {q['75.0']:.2f}")

    # Meilleur film.
    best = agg["best_movie"]["hits"]["hits"][0]["_source"]
    print(f"\n🏆 Meilleur film : {best['title']} ({best['rating']})")

    # Pire film.
    worst = agg["worst_movie"]["hits"]["hits"][0]["_source"]
    print(f"💀 Pire film     : {worst['title']} ({worst['rating']})")
    # print(f"{'='*80}\n")


# ── 4.2 Analyses par catégorie ────────────────────────────────────────────────

# ── Statistiques des genres des films ─────────────────────────────────────────
def top_genres(es, index="movies", size=10):
    """
    Cette fonction calcule les genres les plus représentés.
    """
    aggs = {
        "genres": {"terms": {"field": "genres", "size": size}}
    }
    result = es.search(index=index, size=0, aggs=aggs)

    print(f"\nTop {size} genres les plus représentés :")
    for i, bucket in enumerate(result["aggregations"]["genres"]["buckets"], 1):
        print(f"  {i:>2}. {bucket['key']:<20} {bucket['doc_count']} films")
        
    # print(f"{'='*80}\n")


# ── Statistiques des réalisateurs des films ────────────────────────────────────
def top_directors(es, index="movies", size=10):
    """
    Cette fonction calcule les réalisateurs les plus prolifiques.
    """
    aggs = {
        "directors": {"terms": {"field": "directors.keyword", "size": size}}
    }
    result = es.search(index=index, size=0, aggs=aggs)

    print(f"\nTop {size} réalisateurs les plus prolifiques :")
    for i, bucket in enumerate(result["aggregations"]["directors"]["buckets"], 1):
        print(f"  {i:>2}. {bucket['key']:<30} {bucket['doc_count']} films")
    
    # print(f"{'='*80}\n")

# ── Statistiques des acteurs des films ─────────────────────────────────────────
def top_actors(es, index="movies", size=10):
    """
    Cette fonction calcule les acteurs ayant joué dans le plus de films.
    """
    aggs = {
        "actors": {"terms": {"field": "actors.keyword", "size": size}}
    }
    result = es.search(index=index, size=0, aggs=aggs)

    print(f"\nTop {size} acteurs les plus présents :")
    for i, bucket in enumerate(result["aggregations"]["actors"]["buckets"], 1):
        print(f"  {i:>2}. {bucket['key']:<30} {bucket['doc_count']} films")

    # print(f"{'='*80}\n")

# ── Distribution des films par décennie ─────────────────────────────────────────
def films_by_decade(es, index="movies"):
    """
    Cette fonction calcule la distribution des films par décennie.
    """
    aggs = {
        "by_decade": {
            "histogram": {
                "field": "year",
                "interval": 10,
                "min_doc_count": 1        # ignore les décennies vides.
            }
        }
    }
    result = es.search(index=index, size=0, aggs=aggs)

    print(f"\nDistribution des films par décennie :")
    for bucket in result["aggregations"]["by_decade"]["buckets"]:
        decade = int(bucket["key"])
        count  = bucket["doc_count"]
        bar    = "█" * (count // 15)      # barre proportionnelle (1 bloc = 15 films).
        print(f"  {decade}s : {Fore.BLUE}{bar}{Style.RESET_ALL} {count}")

    # print(f"{'='*80}\n")


# ── 4.3 Analyses avancées ──────────────────────────────────────────────────────

# ── Évolution de la note moyenne par année ─────────────────────────────────────
def avg_rating_by_year(es: Elasticsearch, index: str = INDEX_NAME) -> None:
    """
    Cette fonction affiche l'évolution de la note moyenne par année.
    Elle utilise une terms aggregation sur year avec une sous-agrégation avg sur rating.
    """
    # Agrégation imbriquée : terms + sub-agg avg.
    aggs = {
        "by_year": {
            "terms": {
                "field": "year",
                "size": 100,
                "order": {"_key": "asc"}   # Tri chronologique.
            },
            # Sous-agrégation avg imbriquée dans la terms.
            "aggs": {
                "avg_rating": {"avg": {"field": "rating"}}
            }
        }
    }
 
    result  = es.search(index=index, size=0, aggs=aggs)
    buckets = result["aggregations"]["by_year"]["buckets"]
 
    print("\n" + "=" * 80)
    print("📈 Note moyenne par année :")
    print("=" * 80)
    for bucket in buckets:
        year   = int(bucket["key"])
        avg    = bucket["avg_rating"]["value"]
        count  = bucket["doc_count"]
        if avg:
            print(f"  {year} : {avg:.2f} ⭐  ({count} films)")
    print("=" * 80)


# ── Genre le mieux noté ───────────────────────────────────────────────────────
def best_rated_genres(es: Elasticsearch, index: str = INDEX_NAME) -> None:
    """
    Cette fonction affiche les genres triés par note moyenne décroissante.
    Elle fait une agrégation imbriquée : terms sur genres + sous-agrégation avg sur rating.
    """
    aggs = {
        "genres": {
            "terms": {
                "field": "genres",
                "size": 20,
                # Tri par note moyenne décroissante.
                "order": {"avg_rating": "desc"}
            },
            "aggs": {
                "avg_rating": {"avg": {"field": "rating"}}
            }
        }
    }
 
    result  = es.search(index=index, size=0, aggs=aggs)
    buckets = result["aggregations"]["genres"]["buckets"]
 
    print("\n" + "=" * 80)
    print("🏆 Genre les mieux notés en moyenne :")
    print("=" * 80)
    for i, bucket in enumerate(buckets, 1):
        genre = bucket["key"]
        avg   = bucket["avg_rating"]["value"]
        count = bucket["doc_count"]
        if avg:
            print(f"  {i:2}. {genre:20s} → {avg:.2f} ⭐  ({count} films)")
    print("=" * 80)


# ── Réalisateurs avec la meilleure note moyenne ───────────────────────────────
def best_rated_directors(es: Elasticsearch, min_films: int = 3, index: str = INDEX_NAME) -> None:
    """
    Cette fonction affiche les réalisateurs avec la meilleure note moyenne.
    Elle filtre les réalisateurs avec moins de min_films films via bucket_selector.
    """
    aggs = {
        "directors": {
            "terms": {
                "field": "directors.keyword",
                "size": 200    # Large pour avoir assez de candidats avant filtrage.
            },
            "aggs": {
                # Sous-agrégation note moyenne.
                "avg_rating": {"avg": {"field": "rating"}},
 
                # bucket_selector : filtre les buckets avec moins de min_films.
                "min_films_filter": {
                    "bucket_selector": {
                        "buckets_path": {"count": "_count"},
                        "script": f"params.count >= {min_films}"
                    }
                }
            }
        }
    }
 
    result  = es.search(index=index, size=0, aggs=aggs)
    buckets = result["aggregations"]["directors"]["buckets"]
 
    # Tri côté Python par note décroissante.
    buckets_sorted = sorted(
        buckets,
        key=lambda x: x["avg_rating"]["value"] or 0,
        reverse=True
    )[:10]   # On garde que le top 10.
 
    print("\n" + "=" * 80)
    print(f"🎖️  Top réalisateurs par note moyenne (min {min_films} films) :")
    print("=" * 80)
    for i, bucket in enumerate(buckets_sorted, 1):
        name  = bucket["key"]
        avg   = bucket["avg_rating"]["value"]
        count = bucket["doc_count"]
        if avg:
            print(f"  {i:2}. {name:20s} → {avg:.2f} ⭐  ({count} films)")
    print("=" * 80)


# ── Point d'entrée ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
 
    es = get_es_client()
    if not wait_for_elasticsearch(es):
        exit(1)
 
    # 4.1 — Statistiques globales.
    global_stats(es) 

    # 4.2 — Analyses par catégorie.
    top_genres(es)
    top_directors(es)
    top_actors(es)
    films_by_decade(es)

    # 4.3 — Analyses avancées.
    avg_rating_by_year(es)
    best_rated_genres(es)
    best_rated_directors(es, min_films=3)



# ── Commandes ──────────────────────────────────────────────────────────────────
#   Lancer les statistiques globales :
#       --> python src/analytics.py
# ───────────────────────────────────────────────────────────────────────────────