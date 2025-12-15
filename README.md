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

## 🚀 Installation

### Prérequis
- Python 3.8 ou supérieur
- Compte Groq (pour l'API Groq)
- Compte Notion (pour l'intégration Notion)

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
   
   # Notion API (requis pour l'intégration)
   NOTION_API_KEY=your_notion_api_key
   NOTION_DATABASE_ID=your_notion_database_id
   ```

### Obtenir les clés API

#### Groq API
1. Aller sur [Groq Console](https://console.groq.com/)
2. Créer un compte ou se connecter
3. Générer une clé API dans la section "API Keys"
4. Copier la clé dans votre fichier `.env`

#### Notion API
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

L'application propose 4 vues principales accessibles via la barre latérale :

1. **Analyze Meeting** : Analyse de nouvelles réunions
2. **History** : Consultation de l'historique des réunions
3. **All TODOs** : Gestion de tous les TODOs
4. **Kanban Sync** : Synchronisation avec Notion Kanban

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
   - Voir tous les TODOs de toutes les réunions dans un tableau
   - Sélectionner un TODO pour :
     - Marquer comme "acknowledged" (en cours)
     - Marquer comme "done" (terminé)
     - Créer une page Notion (si non lié)
   - Utiliser les boutons de synchronisation pour synchroniser avec Notion

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

## 📁 Structure du Projet

```
PSTB_Project/
├── app.py                      # Application principale Streamlit
├── database.py                 # Modèles SQLAlchemy et helpers
├── requirements.txt            # Dépendances Python
├── .env                        # Variables d'environnement (à créer)
├── meeting_brain.db            # Base de données SQLite (générée automatiquement)
├── data/                       # Exemples de notes de réunion
│   ├── meeting_1.txt
│   ├── meeting_2.txt
│   └── ...
├── views/                      # Vues Streamlit
│   ├── history.py              # Vue historique des réunions
│   ├── todos.py                # Vue gestion des TODOs
│   └── kanban.py               # Vue synchronisation Kanban Notion
└── integrations/               # Intégrations externes
    └── notion_client.py        # Client Notion API (avec sync bidirectionnelle)
```

## 🛠️ Technologies Utilisées

- **Streamlit** : Framework web pour l'interface utilisateur
- **Groq** : Modèle de langage pour l'extraction d'informations
- **NLTK** : Bibliothèque de traitement du langage naturel
- **SQLAlchemy** : ORM pour la gestion de la base de données
- **Pandas** : Manipulation et analyse de données
- **NumPy** : Calculs numériques
- **Notion Client** : Client Python pour l'API Notion
- **Requests** : Client HTTP pour les appels API
- **Python-dotenv** : Gestion des variables d'environnement

## 📊 Modèles de Données

### Meeting
- `id` : Identifiant unique
- `date` : Date de la réunion
- `title` : Titre de la réunion (optionnel)
- `summary` : Résumé généré par l'IA
- `raw_text` : Texte brut des notes

### Todo
- `id` : Identifiant unique
- `meeting_id` : Référence à la réunion
- `task` : Description de la tâche
- `owner` : Propriétaire de la tâche
- `due_date` : Date d'échéance
- `status` : Statut (pending, in_progress, completed)
- `notion_page_id` : ID de la page Notion liée (optionnel)
- `created_at`, `acknowledged_at`, `completed_at` : Timestamps

### Decision
- `id` : Identifiant unique
- `meeting_id` : Référence à la réunion
- `text` : Texte de la décision

### Participant
- `id` : Identifiant unique
- `meeting_id` : Référence à la réunion
- `name` : Nom du participant

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

La base de données SQLite est créée automatiquement au premier lancement. Pour réinitialiser :
```bash
# Supprimer le fichier de base de données
rm meeting_brain.db
# Relancer l'application pour recréer les tables
```

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

**Meeting Brain** - Transformez vos notes de réunion en actions concrètes avec Notion ! 🚀
