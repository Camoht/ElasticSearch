"""
main.py — Interface Streamlit de CinéSearch.

Remplace l'interface CLI par une UI web moderne.
Lancer avec : streamlit run src/main.py
"""

import re
import subprocess
import sys
import streamlit as st
from config import get_es_client, wait_for_elasticsearch
from search import (
    search_by_title,
    search_advanced,
    search_plot,
    search_fuzzy,
    suggest_titles,
)
from analytics import (
    global_stats,
    top_genres,
    top_directors,
    top_actors,
    films_by_decade,
    avg_rating_by_year,
    best_rated_genres,
    best_rated_directors,
)

# ── Indexation au démarrage (exécutée une seule fois par session) ─────────────
def run_indexer() -> None:
    """
    Lance indexer.py en sous-processus au premier démarrage.
    La variable de session 'indexer_done' évite de relancer à chaque rerun Streamlit.
    """
    if st.session_state.get("indexer_done"):
        return

    indexer_path = os.path.join(os.path.dirname(__file__), "indexer.py")
    result = subprocess.run(
        [sys.executable, indexer_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        st.warning(f"⚠️ Indexeur terminé avec des erreurs :\n{result.stderr}")
    st.session_state["indexer_done"] = True


import os  # noqa: E402 (import déplacé ici pour grouper avec subprocess/sys)

# ── Configuration de la page ───────────────────────────────────────────────────
st.set_page_config(
    page_title="CinéSearch",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personnalisé : thème cinématographique sombre ─────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500&display=swap');

  html, body, [data-testid="stApp"] {
    background-color: #0a0a0f;
    color: #e8e0d0;
    font-family: 'DM Sans', sans-serif;
  }
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f1a 0%, #0a0a0f 100%);
    border-right: 1px solid #2a2a3a;
  }
  [data-testid="stSidebar"] * { color: #e8e0d0 !important; }
  .cine-title {
    font-family: 'Playfair Display', serif;
    font-size: 3.2rem;
    font-weight: 900;
    background: linear-gradient(135deg, #e8c87a 0%, #f5a623 50%, #e8c87a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-bottom: 0;
  }
  .cine-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    letter-spacing: 0.25em;
    color: #8080a0;
    text-transform: uppercase;
    margin-top: 0.3rem;
  }
  .cine-divider {
    border: none;
    border-top: 1px solid #2a2a3a;
    margin: 1.5rem 0;
  }
  .section-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #f5a623;
    margin-bottom: 0.5rem;
    font-weight: 500;
  }
  [data-testid="stTextInput"] input,
  [data-testid="stNumberInput"] input {
    background-color: #14141f !important;
    border: 1px solid #2a2a3a !important;
    border-radius: 6px !important;
    color: #e8e0d0 !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: border-color 0.2s;
  }
  [data-testid="stTextInput"] input:focus,
  [data-testid="stNumberInput"] input:focus {
    border-color: #f5a623 !important;
    box-shadow: 0 0 0 2px rgba(245,166,35,0.15) !important;
  }
  [data-testid="stButton"] button {
    background: linear-gradient(135deg, #f5a623, #e8922a) !important;
    color: #0a0a0f !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.05em !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s !important;
  }
  [data-testid="stButton"] button:hover {
    background: linear-gradient(135deg, #e8c87a, #f5a623) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(245,166,35,0.3) !important;
  }
  .result-card {
    background: #14141f;
    border: 1px solid #2a2a3a;
    border-left: 3px solid #f5a623;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    transition: border-color 0.2s, transform 0.2s;
  }
  .result-card:hover {
    border-left-color: #e8c87a;
    transform: translateX(3px);
  }
  .result-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: #f5a623;
  }
  .result-meta {
    font-size: 0.8rem;
    color: #8080a0;
    margin-top: 0.25rem;
  }
  .stAlert { border-radius: 8px !important; }
  [data-testid="stRadio"] label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
  }
  [data-testid="stSelectbox"] select {
    background-color: #14141f !important;
    border: 1px solid #2a2a3a !important;
    color: #e8e0d0 !important;
  }
  .stSpinner { color: #f5a623 !important; }
  footer { visibility: hidden; }
  [data-testid="stSlider"] [class*="thumb"] {
    background: #f5a623 !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Connexion Elasticsearch (mise en cache) ────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_client():
    es = get_es_client()
    return es if wait_for_elasticsearch(es) else None


# ── Helpers validation ─────────────────────────────────────────────────────────
def validate_text(value: str, field_name: str, min_len: int = 1, max_len: int = 200) -> str | None:
    if len(value) < min_len:
        return f"⚠️ Le champ « {field_name} » ne peut pas être vide."
    if len(value) > max_len:
        return f"⚠️ Le champ « {field_name} » est trop long ({max_len} caractères max)."
    if re.search(r'[<>{}\[\]\\]', value):
        return f"⚠️ Le champ « {field_name} » contient des caractères non autorisés."
    return None


def validate_rating(value: float | None, field_name: str) -> str | None:
    if value is not None and not (0.0 <= value <= 10.0):
        return f"⚠️ {field_name} doit être compris entre 0 et 10."
    return None


def validate_year(value: int | None, field_name: str) -> str | None:
    if value is not None and not (1888 <= value <= 2100):
        return f"⚠️ {field_name} doit être une année valide (1888–2100)."
    return None


def validate_year_range(year_from: int | None, year_to: int | None) -> str | None:
    if year_from and year_to and year_from > year_to:
        return "⚠️ L'année de début doit être inférieure ou égale à l'année de fin."
    return None


def validate_rating_range(min_r: float | None, max_r: float | None) -> str | None:
    if min_r is not None and max_r is not None and min_r > max_r:
        return "⚠️ La note minimum doit être inférieure ou égale à la note maximum."
    return None


def show_errors(errors: list[str]) -> None:
    for e in errors:
        st.error(e)


# ── Rendu des résultats de recherche (commun à toutes les pages de recherche) ──
def render_hits(data: dict) -> None:
    """
    Affiche les résultats (hits) d'un dict JSON retourné par search.py.
    Gère l'affichage des fragments surlignés pour search_plot.
    """
    total = data.get("total", 0)
    hits  = data.get("hits", [])

    st.markdown(f"**{total} résultat(s) trouvé(s)**")

    if total == 0:
        st.info("Aucun film trouvé.")
        return

    for hit in hits:
        directors = hit.get("directors", [])
        dir_str   = ", ".join(directors) if isinstance(directors, list) else str(directors)
        fragments = hit.get("fragments", [])

        card_html = f"""
        <div class="result-card">
          <div class="result-title">🎬 {hit['title']} ({hit['year']})</div>
          <div class="result-meta">
            ⭐ {hit['rating']} &nbsp;|&nbsp; 🎥 {dir_str} &nbsp;|&nbsp; Score : {hit['score']}
          </div>
        """
        if fragments:
            card_html += "<div style='margin-top:0.5rem;font-size:0.82rem;color:#b0a898;'>"
            for frag in fragments:
                # Convertit **mot** en <strong>mot</strong> pour le rendu HTML
                frag_html = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#f5a623">\1</strong>', frag)
                card_html += f"<p style='margin:0.2rem 0'>…{frag_html}…</p>"
            card_html += "</div>"

        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)


# ── En-tête ────────────────────────────────────────────────────────────────────
def render_header():
    st.markdown('<div class="cine-title">CinéSearch</div>', unsafe_allow_html=True)
    st.markdown('<div class="cine-subtitle">Moteur de recherche cinématographique</div>', unsafe_allow_html=True)
    st.markdown('<hr class="cine-divider">', unsafe_allow_html=True)


# ── Sidebar navigation ─────────────────────────────────────────────────────────
def render_sidebar() -> str:
    with st.sidebar:
        st.markdown('<div class="cine-title" style="font-size:1.6rem">🎬</div>', unsafe_allow_html=True)
        st.markdown('<div class="cine-subtitle" style="font-size:0.7rem">Navigation</div>', unsafe_allow_html=True)
        st.markdown('<hr class="cine-divider">', unsafe_allow_html=True)

        choix = st.radio(
            "Mode",
            [
                "🔤 Recherche par titre",
                "🎛️ Recherche avancée",
                "📖 Recherche dans le synopsis",
                "〰️ Recherche floue",
                "✨ Auto-complétion",
                "📊 Statistiques & Analytiques",
            ],
            label_visibility="collapsed",
        )
        st.markdown('<hr class="cine-divider">', unsafe_allow_html=True)
        st.markdown('<div class="result-meta">Propulsé par Elasticsearch 8</div>', unsafe_allow_html=True)

    return choix


# ── Page 1 : Recherche par titre ───────────────────────────────────────────────
def page_search_by_title(es):
    st.markdown('<div class="section-label">Recherche par titre</div>', unsafe_allow_html=True)
    st.markdown("Recherchez un film par son titre exact ou partiel.")

    with st.form("form_title"):
        query     = st.text_input("Titre du film", placeholder="Ex : Inception, Le Parrain…", max_chars=200)
        submitted = st.form_submit_button("🔍 Rechercher")

    if submitted:
        errors = []
        err = validate_text(query, "Titre")
        if err:
            errors.append(err)

        if errors:
            show_errors(errors)
        else:
            with st.spinner("Recherche en cours…"):
                data = search_by_title(es, query.strip())
            render_hits(data)


# ── Page 2 : Recherche avancée ────────────────────────────────────────────────
def page_search_advanced(es):
    st.markdown('<div class="section-label">Recherche avancée</div>', unsafe_allow_html=True)
    st.markdown("Combinez plusieurs critères. Laissez vide pour ignorer.")

    col1, col2 = st.columns(2)

    with col1:
        with st.form("form_advanced"):
            title    = st.text_input("Titre",       max_chars=200)
            actor    = st.text_input("Acteur",       max_chars=200)
            director = st.text_input("Réalisateur",  max_chars=200)
            genre    = st.text_input("Genre",        max_chars=100)
            submitted = st.form_submit_button("🎛️ Lancer la recherche")

    with col2:
        # Les checkboxes + inputs conditionnels HORS du form pour réactivité immédiate
        use_rating = st.checkbox("Filtrer par note")
        if use_rating:
            min_rating = st.number_input("Note minimum (0–10)", min_value=0.0, max_value=10.0,
                                          value=0.0, step=0.1)
            max_rating = st.number_input("Note maximum (0–10)", min_value=0.0, max_value=10.0,
                                          value=10.0, step=0.1)
        else:
            min_rating, max_rating = None, None

        st.markdown("")
        use_year = st.checkbox("Filtrer par année")
        if use_year:
            year_from = st.number_input("Année depuis", min_value=1888, max_value=2100,
                                         value=1980, step=1)
            year_to   = st.number_input("Année jusqu'à", min_value=1888, max_value=2100,
                                         value=2024, step=1)
        else:
            year_from, year_to = None, None

    if submitted:
        errors = []
        for val, name in [(title, "Titre"), (actor, "Acteur"),
                          (director, "Réalisateur"), (genre, "Genre")]:
            if val.strip():
                err = validate_text(val.strip(), name)
                if err:
                    errors.append(err)

        if use_rating:
            errors += [e for e in [
                validate_rating(min_rating, "Note minimum"),
                validate_rating(max_rating, "Note maximum"),
                validate_rating_range(min_rating, max_rating),
            ] if e]

        if use_year:
            errors += [e for e in [
                validate_year(year_from, "Année depuis"),
                validate_year(year_to,   "Année jusqu'à"),
                validate_year_range(year_from, year_to),
            ] if e]

        if not any([title.strip(), actor.strip(), director.strip(),
                    genre.strip(), use_rating, use_year]):
            errors.append("⚠️ Veuillez renseigner au moins un critère de recherche.")

        if errors:
            show_errors(errors)
        else:
            with st.spinner("Recherche en cours…"):
                data = search_advanced(
                    es,
                    title=title.strip() or None,
                    actor=actor.strip() or None,
                    director=director.strip() or None,
                    genre=genre.strip() or None,
                    min_rating=min_rating,
                    max_rating=max_rating,
                    year_from=int(year_from) if year_from else None,
                    year_to=int(year_to) if year_to else None,
                )
            render_hits(data)


# ── Page 3 : Recherche dans le synopsis ───────────────────────────────────────
def page_search_plot(es):
    st.markdown('<div class="section-label">Recherche dans le synopsis</div>', unsafe_allow_html=True)
    st.markdown("Trouvez des films par mots-clés présents dans leur synopsis.")

    with st.form("form_plot"):
        keywords  = st.text_input("Mots-clés", placeholder="Ex : espion espace dystopie…", max_chars=300)
        submitted = st.form_submit_button("📖 Rechercher")

    if submitted:
        errors = []
        err = validate_text(keywords, "Mots-clés", min_len=2, max_len=300)
        if err:
            errors.append(err)
        if len(keywords.strip().split()) > 20:
            errors.append("⚠️ Maximum 20 mots-clés autorisés.")

        if errors:
            show_errors(errors)
        else:
            with st.spinner("Analyse du synopsis…"):
                data = search_plot(es, keywords.strip())
            render_hits(data)


# ── Page 4 : Recherche floue ──────────────────────────────────────────────────
def page_search_fuzzy(es):
    st.markdown('<div class="section-label">Recherche floue</div>', unsafe_allow_html=True)
    st.markdown("Trouvez un film même avec des fautes de frappe ou d'orthographe.")

    with st.form("form_fuzzy"):
        query = st.text_input("Titre approximatif",
                              placeholder="Ex : Incepcion, Matricks…", max_chars=200)
        fuzziness = st.select_slider(
            "Tolérance aux erreurs",
            options=[0, 1, 2, 3],
            value=2,
            format_func=lambda x: {0: "0 — Exact", 1: "1 — Faible",
                                    2: "2 — Modérée", 3: "3 — Élevée"}[x],
        )
        submitted = st.form_submit_button("〰️ Rechercher")

    if submitted:
        errors = []
        err = validate_text(query, "Titre", min_len=2)
        if err:
            errors.append(err)
        if not (0 <= fuzziness <= 3):
            errors.append("⚠️ La tolérance doit être entre 0 et 3.")

        if errors:
            show_errors(errors)
        else:
            with st.spinner("Recherche floue…"):
                data = search_fuzzy(es, query.strip(), fuzziness=fuzziness)
            render_hits(data)


# ── Page 5 : Auto-complétion ──────────────────────────────────────────────────
def page_suggest_titles(es):
    st.markdown('<div class="section-label">Auto-complétion</div>', unsafe_allow_html=True)
    st.markdown("Commencez à taper un titre pour obtenir des suggestions.")

    with st.form("form_suggest"):
        prefix    = st.text_input("Début du titre", placeholder="Ex : Le, Bat, Star…", max_chars=100)
        submitted = st.form_submit_button("✨ Suggérer")

    if submitted:
        errors = []
        err = validate_text(prefix, "Début du titre", min_len=1, max_len=100)
        if err:
            errors.append(err)
        if re.search(r'\d{5,}', prefix):
            errors.append("⚠️ La saisie ne peut pas contenir de longues séquences de chiffres.")

        if errors:
            show_errors(errors)
        else:
            with st.spinner("Suggestions…"):
                data = suggest_titles(es, prefix.strip())
            render_hits(data)


# ── Page 6 : Statistiques & Analytiques ───────────────────────────────────────
def page_analytics(es):
    import pandas as pd

    st.markdown('<div class="section-label">Statistiques & Analytiques</div>', unsafe_allow_html=True)
    st.markdown("Vue d'ensemble du dataset CinéSearch.")

    with st.spinner("Chargement des statistiques…"):
        stats    = global_stats(es)
        genres   = top_genres(es)
        dirs     = top_directors(es)
        actors   = top_actors(es)
        decades  = films_by_decade(es)
        by_year  = avg_rating_by_year(es)
        g_rated  = best_rated_genres(es)
        d_rated  = best_rated_directors(es)

    # ── Métriques globales ────────────────────────────────────────────────────
    st.subheader("📊 Statistiques globales")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total films",   stats["total"])
    c2.metric("Note moyenne",  stats["avg_rating"])
    c3.metric("Note maximale", stats["max_rating"])
    c4.metric("Note minimale", stats["min_rating"])

    c5, c6 = st.columns(2)
    c5.success(f"🏆 Meilleur film : **{stats['best_movie']['title']}** ({stats['best_movie']['rating']})")
    c6.error(  f"💀 Pire film : **{stats['worst_movie']['title']}** ({stats['worst_movie']['rating']})")

    q = stats["quartiles"]
    st.caption(f"Quartiles — Q1 : {q['q1']} | Q2 (médiane) : {q['q2']} | Q3 : {q['q3']}")

    st.markdown("---")

    # ── Tableaux côte à côte ──────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.subheader("🎭 Top Genres")
        df_genres = pd.DataFrame(genres["buckets"]).rename(
            columns={"genre": "Genre", "count": "Nb films"}
        )
        df_genres.index += 1
        st.dataframe(df_genres, use_container_width=True)

    with col_b:
        st.subheader("🎬 Top Réalisateurs")
        df_dirs = pd.DataFrame(dirs["buckets"]).rename(
            columns={"director": "Réalisateur", "count": "Nb films"}
        )
        df_dirs.index += 1
        st.dataframe(df_dirs, use_container_width=True)

    with col_c:
        st.subheader("🌟 Top Acteurs")
        df_actors = pd.DataFrame(actors["buckets"]).rename(
            columns={"actor": "Acteur", "count": "Nb films"}
        )
        df_actors.index += 1
        st.dataframe(df_actors, use_container_width=True)

    st.markdown("---")

    # ── Distribution par décennie (bar chart horizontal) ─────────────────────
    st.subheader("📅 Films par décennie")
    if decades["buckets"]:
        df_dec = pd.DataFrame(decades["buckets"])
        df_dec["Décennie"] = df_dec["decade"].astype(str) + "s"
        df_dec = df_dec.set_index("Décennie")[["count"]].rename(columns={"count": "Nb films"})
        st.bar_chart(df_dec, horizontal=True)

    st.markdown("---")

    # ── Notes par année ───────────────────────────────────────────────────────
    st.subheader("📈 Note moyenne par année")
    if by_year["buckets"]:
        df_year = pd.DataFrame(by_year["buckets"]).set_index("year")
        st.line_chart(df_year["avg_rating"])

    st.markdown("---")

    # ── Genres & réalisateurs les mieux notés ─────────────────────────────────
    col_d, col_e = st.columns(2)

    with col_d:
        st.subheader("🏆 Genres les mieux notés")
        df_grated = pd.DataFrame(g_rated["buckets"]).rename(
            columns={"genre": "Genre", "avg_rating": "Note moy. ⭐", "count": "Nb films"}
        )
        df_grated.index += 1
        st.dataframe(df_grated, use_container_width=True)

    with col_e:
        st.subheader(f"🎖️ Réalisateurs (min {d_rated['min_films']} films)")
        df_drated = pd.DataFrame(d_rated["buckets"]).rename(
            columns={"director": "Réalisateur", "avg_rating": "Note moy. ⭐", "count": "Nb films"}
        )
        df_drated.index += 1
        st.dataframe(df_drated, use_container_width=True)


# ── Point d'entrée ─────────────────────────────────────────────────────────────
def main():
    run_indexer()
    render_header()

    es = get_client()
    if not es:
        st.error("❌ Impossible de se connecter à Elasticsearch.")
        st.info("Vérifiez que Docker est lancé : `docker compose up -d`")
        st.stop()

    choix = render_sidebar()

    if "titre" in choix:
        page_search_by_title(es)
    elif "avancée" in choix:
        page_search_advanced(es)
    elif "synopsis" in choix:
        page_search_plot(es)
    elif "floue" in choix:
        page_search_fuzzy(es)
    elif "complétion" in choix:
        page_suggest_titles(es)
    elif "Analytiques" in choix:
        page_analytics(es)


if __name__ == "__main__":
    main()


# ── Commandes ──────────────────────────────────────────────────────────────────
#
#   Lancer l'interface web :
#     --> streamlit run src/main.py
#
#   Dans Docker :
#     --> docker compose up -d --build
# ──────────────────────────────────────────────────────────────────────────────
