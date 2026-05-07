@echo off
REM ── Lancement automatique de CinéSearch ──────────────────────────────────────

echo ===========================================
echo   Demarrage de CineSearch
echo ===========================================
echo.

echo [1/4] Demarrage des services Docker...
docker compose up -d
echo.

echo [2/4] Attente d'Elasticsearch...
:wait_es
curl -s http://localhost:9200 | findstr "cluster_name" > nul 2>&1
if errorlevel 1 (
  timeout /t 3 /nobreak > nul
  goto wait_es
)
echo      OK - Elasticsearch est pret !

echo [3/4] Attente de Streamlit...
:wait_streamlit
curl -sf http://localhost:8501/_stcore/health > nul 2>&1
if errorlevel 1 (
  timeout /t 3 /nobreak > nul
  goto wait_streamlit
)
echo      OK - Streamlit est pret !

echo [4/4] Attente de Kibana...
:wait_kibana
curl -sf http://localhost:5601/api/status > nul 2>&1
if errorlevel 1 (
  timeout /t 3 /nobreak > nul
  goto wait_kibana
)
echo      OK - Kibana est pret !

echo.
echo ===========================================
echo   Ouverture des pages dans le navigateur
echo ===========================================
echo.

start "" "http://localhost:8501"
timeout /t 2 /nobreak > nul
start "" "http://localhost:5601"

echo.
echo   CineSearch : http://localhost:8501
echo   Kibana     : http://localhost:5601
echo.
echo ===========================================
echo   Tout est lance ! Appuie sur une touche
echo   pour fermer cette fenetre.
echo ===========================================
pause > nul
