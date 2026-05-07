"""
search.py — C'est le fichier comprenant les fonctions de recherche CinéSearch.
"""

from elasticsearch import Elasticsearch
from config import get_es_client, wait_for_elasticsearch, INDEX_NAME


# ── 3.1 Recherche simple par titre ────────────────────────────────────────────
def search_by_title(es: Elasticsearch, query: str, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction recherche des films par titre via une match query.
    Retourne un dict JSON avec total et la liste des hits.
    """
    results = es.search(
        index=index,
        query={"match": {"title": query}},
        size=10
    )

    total = results["hits"]["total"]["value"]
    hits = []
    for hit in results["hits"]["hits"]:
        src = hit["_source"]
        hits.append({
            "score":     round(hit["_score"], 2),
            "title":     src.get("title", "N/A"),
            "year":      src.get("year", "N/A"),
            "rating":    src.get("rating", "N/A"),
            "directors": src.get("directors", []),
        })

    return {"query": query, "type": "title", "total": total, "hits": hits}


# ── 3.2 Recherche avancée multi-critères ──────────────────────────────────────
def search_advanced(es: Elasticsearch, title: str = None, actor: str = None, director: str = None,
                    genre: str = None, min_rating: float = None, max_rating: float = None,
                    year_from: int = None, year_to: int = None, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction effectue une recherche multi-critères avec bool query.
    Retourne un dict JSON avec total et la liste des hits.
    """
    must    = []
    filters = []

    if title:
        must.append({"match": {"title": title}})
    if actor:
        must.append({"match": {"actors": actor}})
    if director:
        must.append({"match": {"directors": director}})

    if genre:
        filters.append({"term": {"genres": genre}})

    rating_range = {}
    if min_rating is not None:
        rating_range["gte"] = min_rating
    if max_rating is not None:
        rating_range["lte"] = max_rating
    if rating_range:
        filters.append({"range": {"rating": rating_range}})

    year_range = {}
    if year_from is not None:
        year_range["gte"] = year_from
    if year_to is not None:
        year_range["lte"] = year_to
    if year_range:
        filters.append({"range": {"year": year_range}})

    bool_query = {}
    if must:
        bool_query["must"] = must
    if filters:
        bool_query["filter"] = filters

    query = {"bool": bool_query} if bool_query else {"match_all": {}}

    results = es.search(index=index, query=query, size=10)

    total = results["hits"]["total"]["value"]
    hits = []
    for hit in results["hits"]["hits"]:
        src = hit["_source"]
        hits.append({
            "score":     round(hit["_score"] or 0, 2),
            "title":     src.get("title", "N/A"),
            "year":      src.get("year", "N/A"),
            "rating":    src.get("rating", "N/A"),
            "directors": src.get("directors", []),
        })

    return {
        "type":      "advanced",
        "filters":   {"title": title, "actor": actor, "director": director,
                      "genre": genre, "min_rating": min_rating, "max_rating": max_rating,
                      "year_from": year_from, "year_to": year_to},
        "total":     total,
        "hits":      hits,
    }


# ── 3.3 Recherche full-text dans le synopsis ──────────────────────────────────
def search_plot(es: Elasticsearch, keywords: str, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction effectue une recherche dans le synopsis avec mise en évidence.
    Retourne un dict JSON avec total, hits et fragments surlignés.
    """
    results = es.search(
        index=index,
        query={"match": {"plot": keywords}},
        highlight={
            "fields": {
                "plot": {
                    "pre_tags":     ["**"],
                    "post_tags":    ["**"],
                    "fragment_size": 150
                }
            }
        },
        size=10
    )

    total = results["hits"]["total"]["value"]
    hits = []
    for hit in results["hits"]["hits"]:
        src = hit["_source"]
        fragments = []
        if "highlight" in hit and "plot" in hit["highlight"]:
            fragments = hit["highlight"]["plot"]
        hits.append({
            "score":     round(hit["_score"], 2),
            "title":     src.get("title", "N/A"),
            "year":      src.get("year", "N/A"),
            "rating":    src.get("rating", "N/A"),
            "directors": src.get("directors", []),
            "fragments": fragments,
        })

    return {"keywords": keywords, "type": "plot", "total": total, "hits": hits}


# ── 3.4 Recherche floue (fuzzy) ───────────────────────────────────────────────
def search_fuzzy(es: Elasticsearch, query: str, fuzziness: int = 2, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction effectue une recherche tolérante aux fautes de frappe.
    Retourne un dict JSON avec total et la liste des hits.
    """
    results = es.search(
        index=index,
        query={
            "match": {
                "title": {
                    "query":     query,
                    "fuzziness": fuzziness
                }
            }
        },
        size=10
    )

    total = results["hits"]["total"]["value"]
    hits = []
    for hit in results["hits"]["hits"]:
        src = hit["_source"]
        hits.append({
            "score":     round(hit["_score"], 2),
            "title":     src.get("title", "N/A"),
            "year":      src.get("year", "N/A"),
            "rating":    src.get("rating", "N/A"),
            "directors": src.get("directors", []),
        })

    return {"query": query, "fuzziness": fuzziness, "type": "fuzzy", "total": total, "hits": hits}


# ── 3.5 Suggestions / Auto-complétion ─────────────────────────────────────────
def suggest_titles(es: Elasticsearch, prefix: str, index: str = INDEX_NAME) -> dict:
    """
    Cette fonction propose des suggestions de titres basées sur un préfixe.
    Utilise match_phrase_prefix sur title (insensible à la casse).
    """
    results = es.search(
        index=index,
        query={
            "match_phrase_prefix": {
                "title": {
                    "query":            prefix,
                    "max_expansions":   20
                }
            }
        },
        size=10
    )

    total = results["hits"]["total"]["value"]
    hits = []
    for hit in results["hits"]["hits"]:
        src = hit["_source"]
        hits.append({
            "score":     round(hit["_score"] or 0, 2),
            "title":     src.get("title", "N/A"),
            "year":      src.get("year", "N/A"),
            "rating":    src.get("rating", "N/A"),
            "directors": src.get("directors", []),
        })

    return {"prefix": prefix, "type": "suggest", "total": total, "hits": hits}


# ── Point d'entrée (affichage terminal conservé pour tests CLI) ────────────────
if __name__ == "__main__":

    es = get_es_client()
    if not wait_for_elasticsearch(es):
        exit(1)

    import json

    print(json.dumps(search_by_title(es, "Rush"),               indent=2, ensure_ascii=False))
    print(json.dumps(search_by_title(es, "Star Wars"),          indent=2, ensure_ascii=False))
    print(json.dumps(search_advanced(es, director="Christopher Nolan", min_rating=8.0),
                     indent=2, ensure_ascii=False))
    print(json.dumps(search_plot(es, "dream sharing technology"), indent=2, ensure_ascii=False))
    print(json.dumps(search_fuzzy(es, "Incepion"),              indent=2, ensure_ascii=False))
    print(json.dumps(suggest_titles(es, "Inc"),                 indent=2, ensure_ascii=False))
