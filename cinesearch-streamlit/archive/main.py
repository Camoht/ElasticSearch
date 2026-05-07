"""
main.py — Interface Streamlit de CinéSearch.

Remplace l'interface CLI par une UI web moderne.
Lancer avec : streamlit run src/main.py
"""

import re
import streamlit as st
from config import get_es_client, wait_for_elasticsearch
from search import (
    search_by_title,
    search_advanced,
    search_plot,
    search_fuzzy,
    suggest_titles,
)

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

  /* Fond général */
  html, body, [data-testid="stApp"] {
    background-color: #0a0a0f;
    color: #e8e0d0;
    font-family: 'DM Sans', sans-serif;
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f1a 0%, #0a0a0f 100%);
    border-right: 1px solid #2a2a3a;
  }
  [data-testid="stSidebar"] * { color: #e8e0d0 !important; }

  /* Titre principal */
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

  /* Section labels */
  .section-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #f5a623;
    margin-bottom: 0.5rem;
    font-weight: 500;
  }

  /* Inputs Streamlit */
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

  /* Boutons */
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

  /* Cards résultats */
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

  /* Alertes */
  .stAlert { border-radius: 8px !important; }

  /* Radio sidebar */
  [data-testid="stRadio"] label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
  }

  /* Selectbox */
  [data-testid="stSelectbox"] select {
    background-color: #14141f !important;
    border: 1px solid #2a2a3a !important;
    color: #e8e0d0 !important;
  }

  /* Spinners */
  .stSpinner { color: #f5a623 !important; }

  /* Masquer le footer Streamlit */
  footer { visibility: hidden; }

  /* Slider */
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
    """Valide une saisie texte. Retourne un message d'erreur ou None si OK."""
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


# ── En-tête ────────────────────────────────────────────────────────────────────
def render_header():
    col1, col2 = st.columns([3, 1])
    with col1:
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
            "",
            options=[
                "🔍  Recherche par titre",
                "🎛️  Recherche avancée",
                "📖  Recherche dans le synopsis",
                "〰️  Recherche floue",
                "✨  Auto-complétion",
            ],
            label_visibility="collapsed",
        )

        st.markdown('<hr class="cine-divider">', unsafe_allow_html=True)

        # Statut Elasticsearch
        es = get_client()
        if es:
            st.success("● Elasticsearch connecté", icon=None)
        else:
            st.error("● Elasticsearch déconnecté")
            st.caption("Lancez : `docker compose up -d`")

    return choix


# ── Page 1 : Recherche par titre ───────────────────────────────────────────────
def page_search_by_title(es):
    st.markdown('<div class="section-label">Recherche par titre</div>', unsafe_allow_html=True)
    st.markdown("Recherchez un film par son titre exact ou partiel.")

    with st.form("form_title"):
        query = st.text_input("Titre du film", placeholder="Ex : Inception, Le Parrain…", max_chars=200)
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
                search_by_title(es, query.strip())


# ── Page 2 : Recherche avancée ────────────────────────────────────────────────
def page_search_advanced(es):
    st.markdown('<div class="section-label">Recherche avancée</div>', unsafe_allow_html=True)
    st.markdown("Combinez plusieurs critères. Laissez vide pour ignorer.")

    with st.form("form_advanced"):
        col1, col2 = st.columns(2)
        with col1:
            title    = st.text_input("Titre",        max_chars=200)
            actor    = st.text_input("Acteur",        max_chars=200)
            director = st.text_input("Réalisateur",   max_chars=200)
            genre    = st.text_input("Genre",         max_chars=100)
        with col2:
            use_rating = st.checkbox("Filtrer par note")
            min_rating = st.number_input("Note minimum (0–10)", min_value=0.0, max_value=10.0,
                                          value=0.0, step=0.1, disabled=not use_rating)
            max_rating = st.number_input("Note maximum (0–10)", min_value=0.0, max_value=10.0,
                                          value=10.0, step=0.1, disabled=not use_rating)
            st.markdown("")
            use_year = st.checkbox("Filtrer par année")
            year_from = st.number_input("Année depuis", min_value=1888, max_value=2100,
                                         value=1980, step=1, disabled=not use_year)
            year_to   = st.number_input("Année jusqu'à", min_value=1888, max_value=2100,
                                         value=2024, step=1, disabled=not use_year)

        submitted = st.form_submit_button("🎛️ Lancer la recherche")

    if submitted:
        errors = []

        # Validation textes (seulement si remplis)
        for val, name in [(title, "Titre"), (actor, "Acteur"),
                          (director, "Réalisateur"), (genre, "Genre")]:
            if val.strip():
                err = validate_text(val.strip(), name)
                if err:
                    errors.append(err)

        # Validation notes
        if use_rating:
            errors += [e for e in [
                validate_rating(min_rating, "Note minimum"),
                validate_rating(max_rating, "Note maximum"),
                validate_rating_range(min_rating, max_rating),
            ] if e]

        # Validation années
        if use_year:
            errors += [e for e in [
                validate_year(year_from, "Année depuis"),
                validate_year(year_to,   "Année jusqu'à"),
                validate_year_range(year_from, year_to),
            ] if e]

        # Au moins un critère
        if not any([title.strip(), actor.strip(), director.strip(),
                    genre.strip(), use_rating, use_year]):
            errors.append("⚠️ Veuillez renseigner au moins un critère de recherche.")

        if errors:
            show_errors(errors)
        else:
            with st.spinner("Recherche en cours…"):
                search_advanced(
                    es,
                    title=title.strip() or None,
                    actor=actor.strip() or None,
                    director=director.strip() or None,
                    genre=genre.strip() or None,
                    min_rating=min_rating if use_rating else None,
                    max_rating=max_rating if use_rating else None,
                    year_from=int(year_from) if use_year else None,
                    year_to=int(year_to) if use_year else None,
                )


# ── Page 3 : Recherche dans le synopsis ───────────────────────────────────────
def page_search_plot(es):
    st.markdown('<div class="section-label">Recherche dans le synopsis</div>', unsafe_allow_html=True)
    st.markdown("Trouvez des films par mots-clés présents dans leur synopsis.")

    with st.form("form_plot"):
        keywords = st.text_input(
            "Mots-clés",
            placeholder="Ex : espion espace dystopie amour interdit…",
            max_chars=300,
        )
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
                search_plot(es, keywords.strip())


# ── Page 4 : Recherche floue ──────────────────────────────────────────────────
def page_search_fuzzy(es):
    st.markdown('<div class="section-label">Recherche floue</div>', unsafe_allow_html=True)
    st.markdown("Trouvez un film même avec des fautes de frappe ou d'orthographe.")

    with st.form("form_fuzzy"):
        query = st.text_input(
            "Titre approximatif",
            placeholder="Ex : Incepcion, Matricks, Le Parrein…",
            max_chars=200,
        )
        fuzziness = st.select_slider(
            "Tolérance aux erreurs",
            options=[0, 1, 2, 3],
            value=2,
            format_func=lambda x: {0: "0 — Exact", 1: "1 — Faible", 2: "2 — Modérée", 3: "3 — Élevée"}[x],
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
                search_fuzzy(es, query.strip(), fuzziness=fuzziness)


# ── Page 5 : Auto-complétion ──────────────────────────────────────────────────
def page_suggest_titles(es):
    st.markdown('<div class="section-label">Auto-complétion</div>', unsafe_allow_html=True)
    st.markdown("Commencez à taper un titre pour obtenir des suggestions.")

    with st.form("form_suggest"):
        prefix = st.text_input(
            "Début du titre",
            placeholder="Ex : Le, Bat, Star…",
            max_chars=100,
        )
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
                suggest_titles(es, prefix.strip())


# ── Point d'entrée ─────────────────────────────────────────────────────────────
def main():
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


if __name__ == "__main__":
    main()


# ── Commandes ──────────────────────────────────────────────────────────────────
#
#   Installer Streamlit :
#     --> pip install streamlit
#
#   Lancer l'interface web :
#     --> streamlit run src/main.py
#
#   Prérequis : Elasticsearch doit tourner.
#     --> docker compose up -d
#
#   Dans Docker, exposer le port Streamlit dans docker-compose.yml :
#     ports:
#       - "8501:8501"
#   Et lancer avec :
#     --> CMD ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
# ──────────────────────────────────────────────────────────────────────────────
