#!/bin/bash
# ── Lancement automatique de CinéSearch ──────────────────────────────────────

echo "==========================================="
echo "  Démarrage de CinéSearch"
echo "==========================================="
echo

echo "[1/4] Démarrage des services Docker..."
docker compose up -d
echo

echo "[2/4] Attente d'Elasticsearch..."
until curl -s http://localhost:9200 | grep -q "cluster_name"; do
  sleep 3
done
echo "     OK - Elasticsearch est prêt !"

echo "[3/4] Attente de Streamlit..."
until curl -sf http://localhost:8501/_stcore/health > /dev/null 2>&1; do
  sleep 3
done
echo "     OK - Streamlit est prêt !"

echo "[4/4] Attente de Kibana..."
until curl -sf http://localhost:5601/api/status > /dev/null 2>&1; do
  sleep 3
done
echo "     OK - Kibana est prêt !"

echo
echo "==========================================="
echo "  Ouverture des pages dans le navigateur"
echo "==========================================="
echo

xdg-open "http://localhost:8501" 2>/dev/null
sleep 2
xdg-open "http://localhost:5601" 2>/dev/null

echo
echo "  CinéSearch : http://localhost:8501"
echo "  Kibana     : http://localhost:5601"
echo
echo "==========================================="
echo "  Tout est lancé !"
echo "==========================================="