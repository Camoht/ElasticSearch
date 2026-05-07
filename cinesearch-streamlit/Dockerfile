# ── Image de base Python ──────────────────────────────────────────────────────
FROM python:3.12-slim

# Répertoire de travail dans le conteneur
WORKDIR /app

# ── Installation des dépendances ──────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copie du code source ──────────────────────────────────────────────────────
COPY src/ ./src/

# ── Exposition du port Streamlit ──────────────────────────────────────────────
EXPOSE 8501

# ── Lancement de l'application ────────────────────────────────────────────────
CMD ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
