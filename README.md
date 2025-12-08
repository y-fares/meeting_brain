# Meeting Brain 🧠

**Meeting Brain** est une application web intelligente qui analyse automatiquement les notes de réunion en utilisant le traitement du langage naturel (NLP) et l'intelligence artificielle (Google Gemini) pour extraire les informations clés : résumés, décisions et actions (TODOs).

## ✨ Fonctionnalités

### 🎯 Analyse Automatique des Réunions
- **Préprocessing NLP** : Nettoyage et analyse statistique du texte
- **Extraction par IA** : Utilisation de Google Gemini pour extraire :
  - Résumés de réunion
  - Décisions prises
  - Actions/TODOs avec propriétaires et dates d'échéance

### 📊 Gestion des Données
- **Base de données SQLite** : Stockage persistant de toutes les réunions
- **Historique complet** : Consultation de toutes les réunions passées
- **Gestion des TODOs** : Suivi des actions avec statuts (pending, in_progress, completed)

### 🔗 Intégration Trello
- **Création automatique de cartes** : Conversion des TODOs en cartes Trello
- **Liaison bidirectionnelle** : Chaque TODO peut être lié à une carte Trello
- **Gestion des statuts** : Mise à jour des statuts des TODOs directement depuis l'interface

## 🚀 Installation

### Prérequis
- Python 3.8 ou supérieur
- Compte Google (pour l'API Gemini)
- Compte Trello (optionnel, pour l'intégration)

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
   # Google Gemini API (requis)
   GOOGLE_API_KEY=your_google_api_key_here
   GEMINI_MODEL=gemini-pro
   
   # Trello API (optionnel)
   TRELLO_API_KEY=your_trello_api_key
   TRELLO_API_TOKEN=your_trello_api_token
   TRELLO_LIST_ID=your_trello_list_id
   ```

### Obtenir les clés API

#### Google Gemini API
1. Aller sur [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Créer une nouvelle clé API
3. Copier la clé dans votre fichier `.env`

#### Trello API (optionnel)
1. Aller sur [Trello Developer API Keys](https://trello.com/app-key)
2. Copier votre API Key
3. Générer un token (lien fourni sur la même page)
4. Obtenir l'ID de la liste Trello où créer les cartes
5. Ajouter ces valeurs dans votre fichier `.env`

## 📖 Utilisation

### Démarrer l'application

```bash
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse `http://localhost:8501`.

### Workflow principal

1. **Analyser une réunion**
   - Coller les notes de réunion dans la zone de texte
   - Cliquer sur "Analyze meeting"
   - L'application va :
     - Préprocesser le texte (statistiques NLP)
     - Extraire le résumé, les décisions et les TODOs via Gemini
     - Afficher les résultats

2. **Consulter l'historique**
   - Naviguer vers la page "History"
   - Sélectionner une réunion
   - Voir le résumé, les décisions, les TODOs et les participants

3. **Gérer les TODOs**
   - Naviguer vers la page "All TODOs"
   - Voir tous les TODOs de toutes les réunions
   - Mettre à jour les statuts (acknowledged, done)
   - Créer des cartes Trello pour les TODOs

4. **Intégration Trello**
   - Sélectionner un TODO dans la vue "All TODOs"
   - Cliquer sur "Push to Trello"
   - La carte sera créée dans votre liste Trello configurée
   - Le TODO sera automatiquement lié à la carte

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
│   └── todos.py                # Vue gestion des TODOs
└── integrations/               # Intégrations externes
    └── trello_client.py        # Client Trello API
```

## 🛠️ Technologies Utilisées

- **Streamlit** : Framework web pour l'interface utilisateur
- **Google Gemini AI** : Modèle de langage pour l'extraction d'informations
- **NLTK** : Bibliothèque de traitement du langage naturel
- **SQLAlchemy** : ORM pour la gestion de la base de données
- **Pandas** : Manipulation et analyse de données
- **Requests** : Client HTTP pour l'API Trello
- **Python-dotenv** : Gestion des variables d'environnement

## 📊 Modèles de Données

### Meeting
- `id` : Identifiant unique
- `date` : Date de la réunion
- `summary` : Résumé généré par l'IA
- `raw_text` : Texte brut des notes

### Todo
- `id` : Identifiant unique
- `meeting_id` : Référence à la réunion
- `task` : Description de la tâche
- `owner` : Propriétaire de la tâche
- `due_date` : Date d'échéance
- `status` : Statut (pending, in_progress, completed)
- `trello_card_id` : ID de la carte Trello liée (optionnel)
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

### Personnaliser le modèle Gemini

Dans votre fichier `.env`, vous pouvez spécifier un modèle différent :
```env
GEMINI_MODEL=gemini-pro
# ou
GEMINI_MODEL=gemini-1.5-pro
```

### Base de données

La base de données SQLite est créée automatiquement au premier lancement. Pour réinitialiser :
```bash
# Supprimer le fichier de base de données
rm meeting_brain.db
# Relancer l'application pour recréer les tables
```

## 🐛 Dépannage

### Erreur "GOOGLE_API_KEY not set"
- Vérifiez que votre fichier `.env` existe et contient `GOOGLE_API_KEY`
- Assurez-vous que le fichier `.env` est à la racine du projet

### Erreur lors de la création de carte Trello
- Vérifiez que toutes les variables Trello sont configurées dans `.env`
- Vérifiez que `TRELLO_LIST_ID` correspond à une liste existante dans votre tableau Trello
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

**Meeting Brain** - Transformez vos notes de réunion en actions concrètes ! 🚀
