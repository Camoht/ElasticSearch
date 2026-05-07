"""
analytics.py — C'est le fichier des agrégations et statistiques CinéSearch.
"""

from elasticsearch import Elasticsearch
from config import get_es_client, wait_for_elasticsearch, INDEX_NAME


# ── 4.1 Statistiques globales ──────────────────────────────────────────────────
def global_stats(es: Elasticsearch, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction calcule les statistiques globales du dataset.
    Retourne un dict JSON avec les métriques clés.
    """
    aggs = {
        "avg_rating":  {"avg":         {"field": "rating"}},
        "min_rating":  {"min":         {"field": "rating"}},
        "max_rating":  {"max":         {"field": "rating"}},
        "quartiles":   {"percentiles": {"field": "rating", "percents": [25, 50, 75]}},
        "best_movie":  {"top_hits":    {"sort": [{"rating": {"order": "desc"}}], "_source": ["title", "rating"], "size": 1}},
        "worst_movie": {"top_hits":    {"sort": [{"rating": {"order": "asc"}}],  "_source": ["title", "rating"], "size": 1}},
    }
    result = es.search(index=index, size=0, aggs=aggs)
    agg    = result["aggregations"]
    total  = result["hits"]["total"]["value"]

    q = agg["quartiles"]["values"]
    best  = agg["best_movie"]["hits"]["hits"][0]["_source"]
    worst = agg["worst_movie"]["hits"]["hits"][0]["_source"]

    return {
        "type":        "global_stats",
        "total":       total,
        "avg_rating":  round(agg["avg_rating"]["value"], 2),
        "min_rating":  round(agg["min_rating"]["value"], 2),
        "max_rating":  round(agg["max_rating"]["value"], 2),
        "quartiles": {
            "q1": round(q["25.0"], 2),
            "q2": round(q["50.0"], 2),
            "q3": round(q["75.0"], 2),
        },
        "best_movie":  {"title": best["title"],  "rating": best["rating"]},
        "worst_movie": {"title": worst["title"], "rating": worst["rating"]},
    }


# ── 4.2 Top genres ────────────────────────────────────────────────────────────
def top_genres(es: Elasticsearch, index: str = INDEX_NAME, size: int = 10) -> dict:
    """
    Cette fonction calcule les genres les plus représentés.
    Retourne un dict JSON avec la liste des genres et leur nombre de films.
    """
    aggs = {"genres": {"terms": {"field": "genres", "size": size}}}
    result = es.search(index=index, size=0, aggs=aggs)

    buckets = [
        {"genre": b["key"], "count": b["doc_count"]}
        for b in result["aggregations"]["genres"]["buckets"]
    ]
    return {"type": "top_genres", "size": size, "buckets": buckets}


# ── 4.2 Top réalisateurs ──────────────────────────────────────────────────────
def top_directors(es: Elasticsearch, index: str = INDEX_NAME, size: int = 10) -> dict:
    """
    Cette fonction calcule les réalisateurs les plus prolifiques.
    Retourne un dict JSON avec la liste des réalisateurs et leur nombre de films.
    """
    aggs = {"directors": {"terms": {"field": "directors.keyword", "size": size}}}
    result = es.search(index=index, size=0, aggs=aggs)

    buckets = [
        {"director": b["key"], "count": b["doc_count"]}
        for b in result["aggregations"]["directors"]["buckets"]
    ]
    return {"type": "top_directors", "size": size, "buckets": buckets}


# ── 4.2 Top acteurs ───────────────────────────────────────────────────────────
def top_actors(es: Elasticsearch, index: str = INDEX_NAME, size: int = 10) -> dict:
    """
    Cette fonction calcule les acteurs ayant joué dans le plus de films.
    Retourne un dict JSON avec la liste des acteurs et leur nombre de films.
    """
    aggs = {"actors": {"terms": {"field": "actors.keyword", "size": size}}}
    result = es.search(index=index, size=0, aggs=aggs)

    buckets = [
        {"actor": b["key"], "count": b["doc_count"]}
        for b in result["aggregations"]["actors"]["buckets"]
    ]
    return {"type": "top_actors", "size": size, "buckets": buckets}


# ── 4.2 Distribution par décennie ─────────────────────────────────────────────
def films_by_decade(es: Elasticsearch, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction calcule la distribution des films par décennie.
    Retourne un dict JSON avec la liste des décennies et leur nombre de films.
    """
    aggs = {
        "by_decade": {
            "histogram": {
                "field":         "year",
                "interval":      10,
                "min_doc_count": 1
            }
        }
    }
    result = es.search(index=index, size=0, aggs=aggs)

    buckets = [
        {"decade": int(b["key"]), "count": b["doc_count"]}
        for b in result["aggregations"]["by_decade"]["buckets"]
    ]
    return {"type": "films_by_decade", "buckets": buckets}


# ── 4.3 Note moyenne par année ────────────────────────────────────────────────
def avg_rating_by_year(es: Elasticsearch, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction affiche l'évolution de la note moyenne par année.
    Retourne un dict JSON avec la liste des années et leur note moyenne.
    """
    aggs = {
        "by_year": {
            "terms": {
                "field": "year",
                "size":  100,
                "order": {"_key": "asc"}
            },
            "aggs": {
                "avg_rating": {"avg": {"field": "rating"}}
            }
        }
    }
    result  = es.search(index=index, size=0, aggs=aggs)
    buckets = [
        {
            "year":       int(b["key"]),
            "avg_rating": round(b["avg_rating"]["value"], 2) if b["avg_rating"]["value"] else None,
            "count":      b["doc_count"],
        }
        for b in result["aggregations"]["by_year"]["buckets"]
        if b["avg_rating"]["value"]
    ]
    return {"type": "avg_rating_by_year", "buckets": buckets}


# ── 4.3 Genres les mieux notés ────────────────────────────────────────────────
def best_rated_genres(es: Elasticsearch, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction affiche les genres triés par note moyenne décroissante.
    Retourne un dict JSON avec la liste des genres et leur note moyenne.
    """
    aggs = {
        "genres": {
            "terms": {
                "field": "genres",
                "size":  20,
                "order": {"avg_rating": "desc"}
            },
            "aggs": {
                "avg_rating": {"avg": {"field": "rating"}}
            }
        }
    }
    result  = es.search(index=index, size=0, aggs=aggs)
    buckets = [
        {
            "genre":      b["key"],
            "avg_rating": round(b["avg_rating"]["value"], 2) if b["avg_rating"]["value"] else None,
            "count":      b["doc_count"],
        }
        for b in result["aggregations"]["genres"]["buckets"]
        if b["avg_rating"]["value"]
    ]
    return {"type": "best_rated_genres", "buckets": buckets}


# ── 4.3 Réalisateurs les mieux notés ─────────────────────────────────────────
def best_rated_directors(es: Elasticsearch, min_films: int = 3, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction affiche les réalisateurs avec la meilleure note moyenne.
    Retourne un dict JSON avec le top 10 des réalisateurs.
    """
    aggs = {
        "directors": {
            "terms": {
                "field": "directors.keyword",
                "size":  200
            },
            "aggs": {
                "avg_rating": {"avg": {"field": "rating"}},
                "min_films_filter": {
                    "bucket_selector": {
                        "buckets_path": {"count": "_count"},
                        "script":       f"params.count >= {min_films}"
                    }
                }
            }
        }
    }
    result  = es.search(index=index, size=0, aggs=aggs)
    buckets = sorted(
        result["aggregations"]["directors"]["buckets"],
        key=lambda x: x["avg_rating"]["value"] or 0,
        reverse=True
    )[:10]

    return {
        "type":      "best_rated_directors",
        "min_films": min_films,
        "buckets": [
            {
                "director":   b["key"],
                "avg_rating": round(b["avg_rating"]["value"], 2) if b["avg_rating"]["value"] else None,
                "count":      b["doc_count"],
            }
            for b in buckets
            if b["avg_rating"]["value"]
        ]
    }


# ── Point d'entrée (affichage terminal conservé pour tests CLI) ────────────────
if __name__ == "__main__":

    es = get_es_client()
    if not wait_for_elasticsearch(es):
        exit(1)

    import json

    print(json.dumps(global_stats(es),              indent=2, ensure_ascii=False))
    print(json.dumps(top_genres(es),                indent=2, ensure_ascii=False))
    print(json.dumps(top_directors(es),             indent=2, ensure_ascii=False))
    print(json.dumps(top_actors(es),                indent=2, ensure_ascii=False))
    print(json.dumps(films_by_decade(es),           indent=2, ensure_ascii=False))
    print(json.dumps(avg_rating_by_year(es),        indent=2, ensure_ascii=False))
    print(json.dumps(best_rated_genres(es),         indent=2, ensure_ascii=False))
    print(json.dumps(best_rated_directors(es, 3),   indent=2, ensure_ascii=False))
