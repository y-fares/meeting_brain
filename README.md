# Meeting Brain 🧠

**Meeting Brain** est une application web intelligente qui analyse automatiquement les notes de réunion en utilisant le traitement du langage naturel (NLP) et l'intelligence artificielle (Groq) pour extraire les informations clés : résumés, décisions et actions (TODOs).

## ✨ Fonctionnalités

### 🎯 Analyse Automatique des Réunions
- **Préprocessing NLP** : Nettoyage et analyse statistique du texte
- **Extraction par IA** : Utilisation de Groq pour extraire :
  - Résumés de réunion
  - Décisions prises
  - Actions/TODOs avec propriétaires et dates d'échéance
- **Sauvegarde automatique** : Enregistrement des réunions analysées dans la base de données

### 📊 Gestion des Données
- **Base de données SQLite** : Stockage persistant de toutes les réunions
- **Historique complet** : Consultation de toutes les réunions passées avec détails
- **Gestion des TODOs** : Suivi des actions avec statuts (pending, in_progress, completed)
- **Gestion des participants** : Suivi automatique des participants aux réunions

### 🔗 Intégration Notion

L'application s'intègre nativement avec **Notion** pour une gestion complète des TODOs :

- **Création automatique de pages** : Conversion des TODOs en pages Notion
- **Mapping dynamique** : Adaptation automatique aux propriétés de votre base de données Notion
- **Support multi-langue** : Compatible avec les bases de données en français et en anglais
- **Liaison bidirectionnelle** : Chaque TODO peut être lié à une page Notion
- **Synchronisation bidirectionnelle** :
  - **Sync Notion → DB** : Mise à jour des statuts des TODOs depuis Notion
  - **Sync DB → Notion** : Mise à jour des statuts Notion depuis la base de données
  - **Vue Kanban Sync** : Interface dédiée pour visualiser et synchroniser le Kanban Notion avec la DB
- **Détection automatique** : Identification automatique des propriétés Kanban (Status/Select) dans votre base Notion

### 💬 Q&A Engine

- **Questions sur les réunions** : Posez des questions en langage naturel sur vos réunions, décisions et TODOs
- **Réponses basées sur les données** : Les réponses sont générées uniquement à partir des données stockées dans la base
- **Support multi-LLM** : Compatible avec Groq et Google Gemini
- **Contexte intelligent** : Le moteur construit automatiquement un contexte à partir des réunions pertinentes

### 📈 Analytics & Exports

- **KPIs en temps réel** : Visualisation des métriques clés (nombre de réunions, TODOs, décisions)
- **Tableaux récapitulatifs** : Vue d'ensemble des réunions, TODOs et décisions
- **Exports CSV** : Export des données pour analyse dans des outils BI (Excel, Tableau, etc.)
- **Filtres avancés** : Filtrage par date, statut, propriétaire, etc.

### 🧠 Insights Engine

- **Questions sur l'état du projet** : Posez des questions sur les tâches en retard, goulots d'étranglement, charge de travail
- **Détection d'intention** : Reconnaissance automatique du type de question (overdue, bottlenecks, workload, etc.)
- **Réponses structurées** : Réponses avec KPIs, preuves et actions recommandées
- **Mode LLM optionnel** : Amélioration des réponses avec LLM si nécessaire
- **Statistiques de charge** : Visualisation de la charge de travail par propriétaire
- **Détection de goulots d'étranglement** : Identification automatique des blocages

### 📅 Todo Events

- **Historique des événements** : Suivi complet de tous les changements de statut des TODOs
- **Timestamps détaillés** : Enregistrement de la création, reconnaissance et complétion
- **Audit trail** : Traçabilité complète des actions sur les TODOs

### 🚀 API REST (FastAPI)

- **API REST complète** : Endpoints pour accéder à toutes les données (meetings, todos, decisions, analytics)
- **Authentification configurable** : mode dev ouvert, token de service, ou comptes utilisateurs avec tokens Bearer
- **Multi-utilisateur** : rôles `admin`, `member`, `viewer`, ownership des réunions et assignation des TODOs
- **Documentation interactive** : Swagger UI disponible sur `/docs`
- **Health check** : Endpoint de santé publique
- **Gestion d'erreurs standardisée** : Réponses d'erreur cohérentes

### 💬 Intégration Slack

- **Slash Command `/insights`** : Interrogez l'Insights Engine directement depuis Slack
- **Réponses formatées** : Messages Slack structurés avec blocks (KPIs, actions recommandées, preuves)
- **Sécurité** : Vérification des signatures Slack (HMAC SHA256)
- **Mode développement** : Fonctionne sans signature en dev (avec avertissement)
- **Support LLM** : Option `--llm` pour améliorer les réponses

## 🚀 Installation

### Prérequis
- Python 3.8 ou supérieur
- Compte Groq (pour l'API Groq)
- Compte Notion (pour l'intégration Notion, optionnel)
- Compte Slack (pour l'intégration Slack, optionnel)

### Étapes d'installation

1. **Cloner le dépôt**
   ```bash
   git clone <repository-url>
   cd PSTB_Project
   ```

2. **Créer un environnement virtuel** (recommandé)
   ```bash
   python -m venv venv
   
   # Sur Windows
   venv\Scripts\activate
   
   # Sur Linux/Mac
   source venv/bin/activate
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer les variables d'environnement**
   
   Créer un fichier `.env` à la racine du projet :
   ```env
   # Groq API (requis)
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.1-8b-instant
   
   # Notion API (optionnel, pour l'intégration Notion)
   NOTION_API_KEY=your_notion_api_key
   NOTION_DATABASE_ID=your_notion_database_id
   
   # API Authentication (optionnel, pour protéger l'API)
   API_AUTH_TOKEN=your_api_auth_token
   AUTH_REQUIRE_LOGIN=false
   MEETING_BRAIN_DB_URL=
   MEETING_BRAIN_API_URL=http://localhost:8000
   MEETING_BRAIN_API_TOKEN=
   
   # Slack Integration (optionnel, pour l'intégration Slack)
   SLACK_SIGNING_SECRET=your_slack_signing_secret
   ```

### Obtenir les clés API

#### Groq API
1. Aller sur [Groq Console](https://console.groq.com/)
2. Créer un compte ou se connecter
3. Générer une clé API dans la section "API Keys"
4. Copier la clé dans votre fichier `.env`

#### Notion API (optionnel)
1. Aller sur [Notion Integrations](https://www.notion.so/my-integrations)
2. Créer une nouvelle intégration (ou utiliser une existante)
3. Copier le "Internal Integration Token" (commence par `ntn_`)
4. Créer ou sélectionner une base de données dans Notion
5. Partager la base de données avec votre intégration :
   - Ouvrir la base de données dans Notion
   - Cliquer sur "..." (trois points) → "Connexions" ou "Add connections"
   - Sélectionner votre intégration
6. Obtenir l'ID de la base de données :
   - L'ID est la chaîne de 32 caractères hexadécimaux dans l'URL
   - Format : `https://www.notion.so/[workspace]/[32-char-id]?v=...`
7. Ajouter `NOTION_API_KEY` et `NOTION_DATABASE_ID` dans votre fichier `.env`

#### Slack API (optionnel)
1. Aller sur [Slack API](https://api.slack.com/apps)
2. Créer une nouvelle app ou sélectionner une app existante
3. Aller dans "Basic Information" → "App Credentials"
4. Copier le "Signing Secret" (commence par un long hash)
5. Ajouter `SLACK_SIGNING_SECRET` dans votre fichier `.env`
6. Configurer un Slash Command :
   - Aller dans "Slash Commands" → "Create New Command"
   - Command: `/insights`
   - Request URL: `https://votre-domaine.com/slack/commands` (ou votre URL ngrok pour les tests)
   - Short Description: `Query project insights`
   - Usage Hint: `question (ex: Quelles tâches sont en retard ?)`
   - Sauvegarder

## 📖 Utilisation

### Démarrer l'application

```bash
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse `http://localhost:8501`.

### Tests

Pour exécuter la suite de tests :

```bash
# Installer les dépendances de développement
pip install -r requirements-dev.txt

# Exécuter les tests
pytest -q
```

### Navigation

L'application propose 9 vues principales accessibles via la barre latérale :

1. **Analyze Meeting** : Analyse de nouvelles réunions
2. **History** : Consultation de l'historique des réunions
3. **All TODOs** : Gestion de tous les TODOs
4. **Kanban Sync** : Synchronisation avec Notion Kanban
5. **Q&A** : Posez des questions sur vos réunions et TODOs
6. **Analytics** : KPIs et exports CSV pour analyse BI
7. **Todo Events** : Historique des événements sur les TODOs
8. **Insights** : Questions sur l'état du projet (tâches en retard, goulots d'étranglement, etc.)
9. **Demo** : Chargement de données de démonstration

### Workflow principal

1. **Analyser une réunion**
   - Naviguer vers "Analyze Meeting"
   - Coller les notes de réunion dans la zone de texte
   - Cliquer sur "Analyze meeting"
   - L'application va :
     - Préprocesser le texte (statistiques NLP)
     - Extraire le résumé, les décisions et les TODOs via Groq
     - Afficher les résultats
     - Sauvegarder automatiquement dans la base de données

2. **Consulter l'historique**
   - Naviguer vers la page "History"
   - Parcourir toutes les réunions enregistrées
   - Voir le résumé, les décisions, les TODOs et les participants pour chaque réunion

3. **Gérer les TODOs**
   - Naviguer vers la page "All TODOs"
   - Voir les TODOs autorisés par l'API dans un tableau
   - Sélectionner un TODO pour :
     - Marquer comme "acknowledged" (en cours)
     - Marquer comme "done" (terminé)
     - Modifier l'utilisateur assigné si vos permissions le permettent
   - La page consomme FastAPI via `MEETING_BRAIN_API_URL` et applique donc les règles d'auth/ownership

4. **Synchroniser avec Notion Kanban**
   - Naviguer vers la page "Kanban Sync"
   - Visualiser côte à côte :
     - Le Kanban Notion (colonnes et cartes)
     - Les TODOs de la base de données liés à Notion
   - Utiliser les boutons de synchronisation :
     - **Sync from Notion → DB** : Mettre à jour les statuts DB depuis Notion
     - **Sync from DB → Notion** : Mettre à jour les statuts Notion depuis la DB
     - **Full Sync** : Synchronisation complète bidirectionnelle

5. **Intégration Notion**
   - Sélectionner un TODO et cliquer sur "Push to Notion" pour créer une page
   - Les TODOs seront automatiquement liés aux pages Notion créées
   - Le mapping des propriétés s'adapte automatiquement à votre base de données Notion
   - Les statuts sont synchronisés automatiquement entre la DB et Notion

6. **Q&A sur les réunions**
   - Naviguer vers la page "Q&A"
   - Poser des questions en langage naturel sur vos réunions, décisions et TODOs
   - Les réponses sont générées uniquement à partir des données de la base

7. **Analytics et Exports**
   - Naviguer vers la page "Analytics"
   - Consulter les KPIs (nombre de réunions, TODOs, décisions)
   - Exporter les données en CSV pour analyse dans des outils BI

8. **Insights sur le projet**
   - Naviguer vers la page "Insights"
   - Poser des questions sur l'état du projet (tâches en retard, goulots d'étranglement, charge de travail)
   - Consulter les statistiques de charge par propriétaire
   - Visualiser les goulots d'étranglement détectés

9. **Utiliser l'API REST**
   - Lancer l'API avec `uvicorn api.main:app --reload`
   - Accéder à la documentation interactive sur `http://localhost:8000/docs`
   - Utiliser les endpoints pour intégrer avec d'autres outils
   - Activer `AUTH_REQUIRE_LOGIN=true` pour utiliser les comptes utilisateurs
   - Créer le premier admin avec `POST /auth/bootstrap`
   - Utiliser `PATCH /todos/{id}/status` et `PATCH /todos/{id}/assignee` pour modifier les TODOs via l'API

10. **Intégration Slack**
    - Configurer le Slash Command `/insights` dans Slack
    - Utiliser `/insights <question>` dans Slack pour interroger l'Insights Engine
    - Ajouter `--llm` pour améliorer les réponses avec LLM

## 📁 Structure du Projet

```
PSTB_Project/
├── app.py                      # Application principale Streamlit
├── database.py                 # Modèles SQLAlchemy et helpers
├── qa_engine.py                # Moteur Q&A pour questions sur les réunions
├── schemas.py                  # Schémas Pydantic pour validation
├── utils_json.py               # Utilitaires JSON
├── llm_providers.py            # Abstraction des fournisseurs LLM (Groq, Gemini)
├── requirements.txt            # Dépendances Python
├── requirements-dev.txt        # Dépendances de développement
├── .env                        # Variables d'environnement (à créer)
├── meeting_brain.db            # Base de données SQLite (générée automatiquement)
├── api/                        # API REST FastAPI
│   ├── main.py                 # Point d'entrée FastAPI
│   ├── deps.py                 # Dépendances (DB, auth)
│   ├── auth_service.py         # Hash de mots de passe, tokens utilisateurs
│   ├── security.py             # Authentification API
│   ├── slack_security.py       # Vérification signatures Slack
│   ├── errors.py               # Gestion d'erreurs standardisée
│   ├── dtos.py                 # Data Transfer Objects
│   ├── repositories.py         # Couche d'accès aux données
│   └── routes/                 # Routes API
│       ├── health.py           # Health check
│       ├── auth.py             # Bootstrap, login, utilisateurs
│       ├── meetings.py         # Endpoints réunions
│       ├── todos.py            # Endpoints TODOs
│       ├── decisions.py        # Endpoints décisions
│       ├── analytics.py        # Endpoints analytics
│       ├── exports.py          # Endpoints exports CSV
│       ├── insights.py         # Endpoints Insights Engine
│       └── slack.py            # Endpoints Slack
├── services/                   # Services métier
│   ├── insights_engine.py      # Moteur Insights (Feature 21)
│   ├── api_client.py           # Client HTTP Streamlit -> FastAPI
│   ├── text_pipeline.py        # Pipeline de traitement de texte
│   └── demo_loader.py          # Chargement données de démo
├── views/                      # Vues Streamlit
│   ├── history.py              # Vue historique des réunions
│   ├── todos.py                # Vue gestion des TODOs
│   ├── kanban.py               # Vue synchronisation Kanban Notion
│   ├── qa.py                   # Vue Q&A
│   ├── analytics.py            # Vue Analytics
│   ├── todo_events.py          # Vue événements TODOs
│   ├── insights.py             # Vue Insights
│   └── demo.py                 # Vue démonstration
├── integrations/               # Intégrations externes
│   ├── notion_client.py        # Client Notion API (avec sync bidirectionnelle)
│   └── trello_client.py        # Client Trello API (optionnel)
├── tests/                      # Tests unitaires et d'intégration
│   ├── conftest.py             # Configuration pytest
│   ├── test_api_*.py           # Tests API
│   ├── test_insights_engine.py  # Tests Insights Engine
│   ├── test_qa_engine.py       # Tests Q&A Engine
│   ├── test_slack_*.py         # Tests Slack
│   └── ...
├── data/                       # Exemples de notes de réunion
│   ├── meeting_1.txt
│   ├── meeting_2.txt
│   └── ...
└── sample_data/                # Données de démonstration
    └── ...
```

## 🛠️ Technologies Utilisées

- **Streamlit** : Framework web pour l'interface utilisateur
- **FastAPI** : Framework moderne pour l'API REST
- **Groq** : Modèle de langage pour l'extraction d'informations
- **Google Gemini** : Alternative LLM (optionnel)
- **NLTK** : Bibliothèque de traitement du langage naturel
- **SQLAlchemy** : ORM pour la gestion de la base de données
- **PostgreSQL / psycopg** : Base recommandée pour le multi-utilisateur en production
- **Pydantic** : Validation de données et schémas
- **Pandas** : Manipulation et analyse de données
- **NumPy** : Calculs numériques
- **Notion Client** : Client Python pour l'API Notion
- **Requests** : Client HTTP pour les appels API
- **Python-dotenv** : Gestion des variables d'environnement
- **HMAC/SHA256** : Vérification des signatures Slack
- **Pytest** : Framework de tests

## 📊 Modèles de Données

### Meeting
- `id` : Identifiant unique
- `date` : Date de la réunion
- `title` : Titre de la réunion (optionnel)
- `summary` : Résumé généré par l'IA
- `raw_text` : Texte brut des notes
- `created_by_user_id` : Utilisateur créateur de la réunion (optionnel)

### Todo
- `id` : Identifiant unique
- `meeting_id` : Référence à la réunion
- `task` : Description de la tâche
- `owner` : Propriétaire de la tâche
- `due_date` : Date d'échéance
- `status` : Statut (pending, in_progress, completed)
- `notion_page_id` : ID de la page Notion liée (optionnel)
- `assigned_user_id` : Utilisateur assigné au TODO (optionnel)
- `created_at`, `acknowledged_at`, `completed_at` : Timestamps

### User
- `id` : Identifiant unique
- `email` : Email de connexion
- `display_name` : Nom affiché
- `role` : Rôle (`admin`, `member`, `viewer`)
- `password_hash` : Hash PBKDF2 du mot de passe
- `api_token_hash` : Hash du token Bearer actif
- `created_at`, `disabled_at` : Timestamps de cycle de vie

### Decision
- `id` : Identifiant unique
- `meeting_id` : Référence à la réunion
- `text` : Texte de la décision

### Participant
- `id` : Identifiant unique
- `meeting_id` : Référence à la réunion
- `name` : Nom du participant

### TodoEvent
- `id` : Identifiant unique
- `todo_id` : Référence au TODO
- `event_type` : Type d'événement (created, acknowledged, completed)
- `timestamp` : Date et heure de l'événement

## 🔧 Configuration Avancée

### Personnaliser le modèle Groq

Dans votre fichier `.env`, vous pouvez spécifier un modèle différent :
```env
GROQ_MODEL=llama-3.1-8b-instant
# Autres modèles disponibles :
# GROQ_MODEL=llama-3-70b-8192
# GROQ_MODEL=mixtral-8x7b-32768
# GROQ_MODEL=llama-3-8b-8192
```

### Base de données

La base de données SQLite est créée automatiquement au premier lancement. Elle convient au développement local.

Pour un usage multi-utilisateur, utilisez PostgreSQL via `MEETING_BRAIN_DB_URL` :
```env
MEETING_BRAIN_DB_URL=postgresql+psycopg://user:password@host:5432/meeting_brain
```

Pour réinitialiser la base SQLite locale :
```bash
# Supprimer le fichier de base de données
rm meeting_brain.db
# Relancer l'application pour recréer les tables
```

### Authentification API

Trois modes sont disponibles :

1. **Mode développement** : si `API_AUTH_TOKEN` est vide et `AUTH_REQUIRE_LOGIN=false`, les endpoints protégés restent accessibles localement.
2. **Token de service** : si `API_AUTH_TOKEN` est défini, les endpoints utilisent `Authorization: Bearer <token>`.
3. **Comptes utilisateurs** : si `AUTH_REQUIRE_LOGIN=true`, utilisez `/auth/bootstrap`, `/auth/login`, `/auth/me` et `/auth/users`.

Créer le premier admin :
```bash
curl -X POST http://localhost:8000/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"change-this-password","display_name":"Admin"}'
```

Se connecter :
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"change-this-password"}'
```

Rôles disponibles :
- `admin` : voit tout, crée des utilisateurs, assigne les TODOs
- `member` : voit ses réunions créées et ses TODOs assignés, peut les mettre à jour
- `viewer` : lecture seule dans son périmètre

## 🐛 Dépannage

### Erreur "GROQ_API_KEY not set"
- Vérifiez que votre fichier `.env` existe et contient `GROQ_API_KEY`
- Assurez-vous que le fichier `.env` est à la racine du projet
- Obtenez votre clé API sur [Groq Console](https://console.groq.com/)

### Erreur lors de la création de page Notion
- Vérifiez que `NOTION_API_KEY` et `NOTION_DATABASE_ID` sont configurés dans `.env`
- Vérifiez que la base de données Notion est partagée avec votre intégration
- Vérifiez que votre intégration a les permissions "Read content", "Insert content" et "Update content"
- Utilisez le script `test_notion_connection.py` pour tester la connexion :
  ```bash
  python test_notion_connection.py
  ```
- Consultez les logs pour plus de détails

### Erreur de synchronisation Notion
- Vérifiez que les TODOs ont un `notion_page_id` (utilisez "Push to Notion" d'abord)
- Vérifiez que la propriété Kanban dans Notion est de type "Status" ou "Select"
- Les statuts sont mappés automatiquement entre DB et Notion :
  - `pending` → "To Do" / "En attente" / "À faire"
  - `in_progress` → "In Progress" / "En cours" / "En progression"
  - `completed` → "Done" / "Terminé" / "Fait"
- Le mapping est insensible à la casse et gère les accents
- Consultez les logs pour plus de détails

### Erreur "dispatch_failed" dans Slack
- Vérifiez que l'URL dans la configuration Slack est correcte : `https://votre-domaine.com/slack/commands`
- Vérifiez que votre serveur FastAPI est accessible (testez avec `curl`)
- Vérifiez que `SLACK_SIGNING_SECRET` est correctement configuré dans `.env`
- En mode dev (sans `SLACK_SIGNING_SECRET`), l'API accepte les requêtes mais log un avertissement
- Vérifiez les logs du serveur pour voir les erreurs détaillées

### Erreur API "Not Found"
- Vérifiez que vous utilisez les bons préfixes d'URL :
  - `/insights/answer` (pas `/insights/insights/answer`)
  - `/slack/commands` (pas `/slack/slack/commands`)
- Consultez la documentation interactive sur `http://localhost:8000/docs` pour voir tous les endpoints disponibles

### Problèmes avec NLTK
- Les ressources NLTK sont téléchargées automatiquement au premier lancement
- Si cela échoue, téléchargez manuellement :
  ```python
  import nltk
  nltk.download('punkt')
  nltk.download('stopwords')
  ```

## 📝 Notes de Développement

- L'application utilise SQLite par défaut pour la simplicité
- Les données sont persistantes entre les sessions
- Les logs sont affichés dans la console où Streamlit est lancé
- La synchronisation Notion est bidirectionnelle et gère automatiquement le mapping des statuts
- Les modèles Groq sont rapides et efficaces pour l'extraction d'informations
- Le mapping des propriétés Notion est dynamique et s'adapte à votre schéma de base de données

## 🎯 Fonctionnalités par Sprint

### Sprint 1
- ✅ Analyse de réunions avec NLP preprocessing
- ✅ Extraction de résumés, décisions et TODOs via LLM
- ✅ Interface Streamlit de base

### Sprint 2
- ✅ Base de données SQLite avec SQLAlchemy
- ✅ Historique des réunions
- ✅ Gestion des TODOs avec statuts

### Sprint 3
- ✅ Intégration Notion complète
- ✅ Synchronisation bidirectionnelle Notion ↔ DB
- ✅ Vue Kanban Sync pour visualisation et synchronisation
- ✅ Migration de Google Gemini vers Groq
- ✅ Mapping dynamique des propriétés Notion
- ✅ Support multi-langue pour les statuts Notion

### Sprint 4-5
- ✅ API REST FastAPI complète
- ✅ Endpoints pour meetings, todos, decisions
- ✅ Authentification optionnelle par token Bearer
- ✅ Documentation interactive (Swagger UI)
- ✅ Gestion d'erreurs standardisée
- ✅ Health check endpoint

### Sprint 6-7
- ✅ Q&A Engine pour questions sur les réunions
- ✅ Support multi-LLM (Groq, Gemini)
- ✅ Construction automatique de contexte
- ✅ Vue Q&A dans Streamlit

### Sprint 8-9
- ✅ Analytics & Exports
- ✅ KPIs en temps réel
- ✅ Exports CSV pour outils BI
- ✅ Vue Analytics dans Streamlit
- ✅ Endpoints API pour exports

### Sprint 10-11
- ✅ Todo Events tracking
- ✅ Historique complet des changements de statut
- ✅ Timestamps détaillés (created, acknowledged, completed)
- ✅ Vue Todo Events dans Streamlit

### Sprint 12
- ✅ Insights Engine (Feature 21)
  - Détection d'intention automatique
  - Réponses structurées avec KPIs et preuves
  - Mode LLM optionnel
  - Statistiques de charge par propriétaire
  - Détection de goulots d'étranglement
  - Vue Insights dans Streamlit
  - Endpoints API `/insights/*`
- ✅ Intégration Slack (Feature 22)
  - Slash Command `/insights`
  - Vérification des signatures Slack (HMAC SHA256)
  - Messages Slack formatés avec blocks
  - Support du flag `--llm`
  - Endpoints `/slack/commands` et `/slack/events`

### Sprint 13
- ✅ Authentification multi-utilisateur
  - Bootstrap du premier admin
  - Login utilisateur avec tokens Bearer hashés
  - Rôles `admin`, `member`, `viewer`
  - Ownership des réunions (`created_by_user_id`)
  - Assignation des TODOs (`assigned_user_id`)
  - Filtrage automatique des endpoints lecture selon le périmètre utilisateur
  - Endpoints `PATCH /todos/{id}/status` et `PATCH /todos/{id}/assignee`
  - Support PostgreSQL via `MEETING_BRAIN_DB_URL`

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Ouvrir une issue pour signaler un bug
- Proposer de nouvelles fonctionnalités
- Soumettre une pull request

## 📄 Licence

Ce projet est sous licence MIT.

## 👤 Auteur

Développé dans le cadre du projet PSTB.

---

## 📖 Runbook

### Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Installer les dépendances de développement (optionnel)
pip install -r requirements-dev.txt
```

### Configuration

1. Créer un fichier `.env` à la racine du projet
2. Configurer les variables d'environnement dans `.env`:
   - `GROQ_API_KEY`: Clé API Groq pour l'extraction LLM (requis)
   - `GROQ_MODEL`: Modèle Groq à utiliser (défaut: `llama-3.1-8b-instant`)
   - `NOTION_API_KEY` et `NOTION_DATABASE_ID`: Pour l'intégration Notion (optionnel)
   - `API_AUTH_TOKEN`: Token d'authentification pour l'API (optionnel en dev)
   - `AUTH_REQUIRE_LOGIN`: Active l'authentification par comptes utilisateurs (`true` en production)
   - `MEETING_BRAIN_DB_URL`: URL SQLAlchemy de la base, PostgreSQL recommandé en multi-utilisateur
   - `MEETING_BRAIN_API_URL`: URL FastAPI utilisée par les vues Streamlit migrées vers l'API
   - `MEETING_BRAIN_API_TOKEN`: Token Bearer utilisé par Streamlit en mode token de service
   - `SLACK_SIGNING_SECRET`: Secret de signature Slack (optionnel, pour l'intégration Slack)
   - `GOOGLE_API_KEY`: Clé API Google pour Gemini (optionnel, pour Q&A avec Gemini)

### Lancer l'application Streamlit

```bash
streamlit run app.py
```

L'application sera accessible sur `http://localhost:8501`

### Lancer l'API FastAPI

```bash
uvicorn api.main:app --reload
```

L'API sera accessible sur `http://localhost:8000`
- Documentation interactive: `http://localhost:8000/docs`
- Health check (public): `http://localhost:8000/health`

### Utilisation de l'API avec authentification

Si `API_AUTH_TOKEN` est défini dans `.env`, tous les endpoints (sauf `/health` et `/slack/*`) nécessitent un token Bearer:

```bash
# Exemple avec curl
curl -H "Authorization: Bearer votre-token-ici" http://localhost:8000/meetings

# Exemple avec Python requests
import requests
headers = {"Authorization": "Bearer votre-token-ici"}
response = requests.get("http://localhost:8000/meetings", headers=headers)
```

Si `API_AUTH_TOKEN` n'est pas défini, l'API fonctionne en mode développement (pas d'authentification requise).

**Note** : Les endpoints `/slack/*` sont protégés par la vérification des signatures Slack et ne nécessitent pas `API_AUTH_TOKEN`.

### Endpoints API disponibles

- **Health** : `GET /health` (public, pas d'auth)
- **Meetings** : `GET /meetings`, `GET /meetings/{id}`
- **TODOs** : `GET /todos`, `GET /todos/{id}`
- **Decisions** : `GET /decisions`, `GET /decisions/{id}`
- **Analytics** : `GET /analytics/kpis`, `GET /analytics/summary`
- **Exports** : `GET /exports/meetings`, `GET /exports/todos`, `GET /exports/decisions`
- **Insights** : 
  - `GET /insights/answer?q=<question>&use_llm=<bool>`
  - `GET /insights/owner_load`
  - `GET /insights/bottlenecks`
- **Slack** :
  - `POST /slack/commands` (Slash Command handler)
  - `POST /slack/events` (Events API handler)

Consultez la documentation interactive sur `http://localhost:8000/docs` pour plus de détails.

### Auth multi-utilisateur et ownership

Variables utiles:

```env
AUTH_REQUIRE_LOGIN=true
API_AUTH_TOKEN=
MEETING_BRAIN_DB_URL=postgresql+psycopg://user:password@host:5432/meeting_brain
MEETING_BRAIN_API_URL=http://localhost:8000
MEETING_BRAIN_API_TOKEN=
```

Modes supportés:

- `API_AUTH_TOKEN` défini: token de service unique via `Authorization: Bearer <token>`.
- `AUTH_REQUIRE_LOGIN=true`: comptes utilisateurs, tokens Bearer par utilisateur.
- `AUTH_REQUIRE_LOGIN=false` sans `API_AUTH_TOKEN`: mode développement sans authentification.

Endpoints auth:

- `POST /auth/bootstrap`: créer le premier admin quand aucun utilisateur n'existe.
- `POST /auth/login`: obtenir un token utilisateur.
- `GET /auth/me`: lire l'utilisateur courant.
- `POST /auth/users`: créer un utilisateur, admin requis.

Rôles:

- `admin`: voit tout, crée les utilisateurs, assigne les TODOs.
- `member`: voit ses réunions créées et ses TODOs assignés; peut mettre à jour ces TODOs.
- `viewer`: lecture seule dans son périmètre.

Les endpoints de lecture (`/meetings`, `/todos`, `/decisions`, `/analytics`, `/exports`, `/insights`) appliquent automatiquement ce périmètre en mode utilisateurs. Les nouveaux endpoints `PATCH /todos/{id}/status` et `PATCH /todos/{id}/assignee` permettent de modifier les TODOs via l'API avec contrôles de permissions.

### Utilisation de l'intégration Slack

1. **Configurer le Slash Command dans Slack** :
   - Aller dans votre app Slack → "Slash Commands" → "Create New Command"
   - Command: `/insights`
   - Request URL: `https://votre-domaine.com/slack/commands` (ou votre URL ngrok pour les tests)
   - Short Description: `Query project insights`
   - Usage Hint: `question (ex: Quelles tâches sont en retard ?)`

2. **Tester localement avec ngrok** :
   ```bash
   # Terminal 1: Lancer l'API
   uvicorn api.main:app --reload
   
   # Terminal 2: Lancer ngrok
   ngrok http 8000
   
   # Utiliser l'URL ngrok dans la configuration Slack
   # Exemple: https://ruly-noncommunicative-roxana.ngrok-free.dev/slack/commands
   ```

3. **Utiliser la commande dans Slack** :
   ```
   /insights Quelles tâches sont en retard ?
   /insights Qui est surchargé ? --llm
   /insights Qu'est-ce qui est bloqué ?
   ```

### Tests

```bash
# Lancer tous les tests
pytest

# Lancer les tests avec couverture
pytest --cov=. --cov-report=html

# Lancer uniquement les tests de l'API
pytest tests/test_api_auth.py tests/test_api_errors.py
```

---

**Meeting Brain** - Transformez vos notes de réunion en actions concrètes avec Notion ! 🚀
