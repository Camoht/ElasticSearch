# Configuration
Il vous faut un accès à docker et savoir executer des commandes sur votre terminal.

# Démarrage
Démarrez l'outil et ses dépendances :

A. Sur Linux : ```./start.sh```

B. Sur Windows : double-cliquez sur ```start.bat```

Deux onglets se sont ouverts dans votre navigateur par défaut. Manipuler l'outil via http://localhost:8501/ (premier onglet ouvert).

## Dépannages
**Les onglets ne s'ouvrent pas**

Supprimez vos images docker non utilisées, executez dans l'ordre :
1. ```docker compose down -v```
2. ```docker compose down -v --remove-orphans``` 
3. ```docker compose up -d --build```
4. ```./start.sh```

**Messages d'erreurs dans l'outil**

Reconstrisez votre ElasticSearch, executez dans l'ordre :
1. ```docker compose exec streamlit python src/config.py```
2. ```docker compose exec streamlit python src/indexer.py```


# Bon à savoir
Un rapport présentant le projet est disponible ```/cinesearch-streamlit/doc/Rapport.pdf```
Une démo est aussi disponible ```/cinesearch-streamlit/doc/Demo.mp4```