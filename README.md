# Meeting Brain 🧠

An intelligent **Streamlit web application** that analyzes meeting notes automatically using NLP and LLM to extract summaries, decisions, and action items.

**[Live Demo](https://meetingbrain-b8pfnh9ququdapg5acp745.streamlit.app/)**

---

## ✨ Features

### 📝 **Analyze Meeting**
- Paste meeting notes → AI extracts:
  - **Summary** (5-10 lines)
  - **Decisions** (key decisions made)
  - **Action Items/TODOs** (with owner & due date)
- Automatic NLP preprocessing
- Supports 3 LLM providers: Groq, Mistral, Google Gemini
- Auto-saves to database

### 📋 **All TODOs**
- View all action items from meetings
- Update status: Pending → In Progress → Completed
- Filter by owner, status, or date
- Track completion timestamps
- Local database mode (works without API)

### 🔍 **Q&A**
- Ask questions about your meetings in natural language
- Example: *"What tasks are pending?"*, *"Who is overloaded?"*
- Answers grounded in actual meeting data
- Multi-LLM support (auto-fallback if one fails)

### 📊 **Analytics**
- Real-time KPIs: meetings, TODOs, decisions
- Summary tables with full details
- CSV export for BI tools (Excel, Tableau)

### 💡 **Insights**
- Get smart answers about project health
- Detect overdue tasks, bottlenecks, workload distribution
- Auto-detect question intent

### 📅 **History**
- Browse all analyzed meetings
- View details: summary, decisions, participants, TODOs

### 📌 **Todo Events**
- Complete audit trail of all status changes
- Timestamps: created, acknowledged, completed
- Full change history

### 🎮 **Demo**
- Load sample meeting data instantly
- Try features without analyzing real meetings

---

## 🏗️ Architecture

### Clean, Modular Design

```
Meeting Brain (Streamlit UI)
├── views/
│   ├── analyze_meeting (app.py)
│   ├── history.py
│   ├── todos.py          ← All TODOs management
│   ├── qa.py             ← Q&A engine
│   ├── analytics.py      ← KPIs & exports
│   ├── insights.py       ← Project intelligence
│   ├── todo_events.py    ← Audit trail
│   └── demo.py           ← Sample data
│
├── services/
│   ├── llm_providers.py  ← LLM abstraction (Groq, Mistral, Gemini)
│   ├── text_pipeline.py  ← NLP preprocessing
│   ├── insights_engine.py ← Intelligence logic
│   └── demo_loader.py    ← Sample data
│
├── database.py           ← SQLAlchemy ORM (SQLite)
├── qa_engine.py          ← Question answering
├── llm_providers.py      ← Provider management
└── utils_json.py         ← Helper utilities
```

### Key Design Principles

✅ **Single Source of Truth** — Local SQLite database
✅ **No External Dependencies** — Works without API/Notion/Slack
✅ **Provider Abstraction** — Easy to swap LLM providers
✅ **Service Layer** — Business logic separated from UI
✅ **Direct DB Access** — Views access database directly
✅ **Production-Ready** — Deployed on Streamlit Cloud

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip or uv

### Installation

```bash
# Clone the repository
git clone https://github.com/y-fares/meeting_brain.git
cd meeting_brain

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
# LLM Provider (choose at least one)
GROQ_API_KEY=your_groq_key_here
# MISTRAL_API_KEY=your_mistral_key_here
# GOOGLE_API_KEY=your_gemini_key_here

# Optional: specify default model
GROQ_MODEL=llama-3.1-8b-instant
MISTRAL_MODEL=mistral-small-latest
GEMINI_MODEL=gemini-pro
```

Get your API keys:
- **Groq**: [console.groq.com](https://console.groq.com/)
- **Mistral**: [console.mistral.ai](https://console.mistral.ai/)
- **Google**: [makersuite.google.com](https://makersuite.google.com/)

### Run Locally

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

---

## 📊 How It Works

### 1. **Analyze Meeting**
```
Meeting Notes
   ↓ (NLP preprocessing)
Clean Text + Statistics
   ↓ (LLM extraction)
Summary, Decisions, TODOs
   ↓ (Auto-save)
SQLite Database
```

### 2. **LLM Provider Selection**
```
App checks: GROQ_API_KEY? → MISTRAL_API_KEY? → GOOGLE_API_KEY?
Uses first available (Groq fastest, Mistral reliable, Gemini accurate)
Auto-fallback if selected provider fails
```

### 3. **Data Access**
```
Views → database.py (SQLAlchemy ORM) → SQLite
Services → database.py (business logic)
No API, no external calls - all local
```

---

## 📁 Data

### Database Schema

```sql
-- Meetings
CREATE TABLE meetings (
  id INTEGER PRIMARY KEY,
  date DATETIME,
  title TEXT,
  summary TEXT,
  raw_text TEXT
);

-- TODOs
CREATE TABLE todos (
  id INTEGER PRIMARY KEY,
  meeting_id INTEGER,
  task TEXT,
  owner TEXT,
  due_date TEXT,
  status TEXT,  -- pending, in_progress, completed
  created_at DATETIME,
  acknowledged_at DATETIME,
  completed_at DATETIME
);

-- Decisions
CREATE TABLE decisions (
  id INTEGER PRIMARY KEY,
  meeting_id INTEGER,
  text TEXT
);

-- Participants
CREATE TABLE participants (
  id INTEGER PRIMARY KEY,
  meeting_id INTEGER,
  name TEXT
);

-- TodoEvents (audit trail)
CREATE TABLE todo_events (
  id INTEGER PRIMARY KEY,
  todo_id INTEGER,
  event_type TEXT,  -- created, acknowledged, completed
  timestamp DATETIME
);
```

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# With coverage
pytest --cov=.
```

---

## 🎯 v1 vs Future Versions

### v1 (Current - Production Ready) ✅
- ✅ Streamlit UI
- ✅ Local SQLite database
- ✅ Meeting analysis (Groq, Mistral, Gemini)
- ✅ Q&A engine
- ✅ Analytics & exports
- ✅ Insights engine
- ✅ Audit trail

### v2 (Planned) 🚀
- 🔔 Notion integration (sync TODOs ↔ Notion Kanban)
- 💬 Slack integration (/insights command)
- 🌐 FastAPI for team deployment
- 👥 Multi-user support (auth, roles, ownership)
- 📈 Advanced analytics dashboard
- 🔔 Email notifications

### Not in Scope
- ❌ Real-time collaboration
- ❌ Mobile app
- ❌ Video call transcription

---

## 🛠️ Tech Stack

| Component | Tech |
|-----------|------|
| **UI** | Streamlit 1.61+ |
| **Database** | SQLite + SQLAlchemy ORM |
| **NLP** | NLTK |
| **LLM** | Groq, Mistral, Google Gemini |
| **Data** | Pandas, NumPy |
| **Testing** | Pytest |
| **Deployment** | Streamlit Cloud |

---

## 📝 Example Usage

### 1. **Upload Meeting Notes**

```
Réunion Q3 Planning
Date: 5 Aug 2026
Participants: Laura, Sophie, Marc

Agenda:
- Launch Analytics module
- Fix API performance (P95 latency 800ms → 500ms)
- Integrate Slack by Aug 20

Decisions:
- Analytics is priority 1
- Budget approved for 2 devs

Actions:
- Laura: Validate design by Thursday
- Sophie: Slack demo by Monday  
- Marc: Performance benchmarks by Friday
```

### 2. **View Results**

**Summary:**
> Q3 planning meeting focused on analytics launch, API optimization, and Slack integration. Budget approved for two additional developers. Key deadline: Slack integration by August 20th.

**Decisions:**
- Analytics module is priority 1
- Budget approved for 2 additional developers

**Actions:**
| Task | Owner | Due Date | Status |
|------|-------|----------|--------|
| Validate design | Laura | Thu | Pending |
| Slack demo | Sophie | Mon | Pending |
| Benchmarks | Marc | Fri | Pending |

### 3. **Ask Questions**

> **Q:** What tasks are pending?  
> **A:** 3 tasks pending: design validation (Laura), Slack demo (Sophie), performance benchmarks (Marc).

> **Q:** Who is overloaded?  
> **A:** No one is significantly overloaded. Tasks are evenly distributed.

---

## 🚀 Deployment

### Streamlit Cloud (Current)

Already deployed at: https://meetingbrain-b8pfnh9ququdapg5acp745.streamlit.app/

**Steps to deploy:**
1. Fork the repo
2. Connect to Streamlit Cloud
3. Set secrets (API keys) in Settings
4. App redeploys automatically on git push

### Local Development

```bash
streamlit run app.py --logger.level=info
```

---

## 📖 Contributing

This is a portfolio project showcasing clean architecture and full-stack development.

If you want to explore or extend:

1. **Set up locally** (see Installation above)
2. **Create a feature branch** (`git checkout -b feature/your-feature`)
3. **Make changes** and test locally
4. **Push and create a PR**

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👤 Author

**Yacine Fares**
- GitHub: [@y-fares](https://github.com/y-fares)
- LinkedIn: [Yacine Fares](https://linkedin.com/in/yacine-fares)

---

## 🙏 Acknowledgments

Built with:
- Streamlit for amazing UI framework
- Groq for blazing-fast LLM inference
- SQLAlchemy for elegant ORM
- NLTK for NLP preprocessing

---

## 📮 Support

Found a bug? Have a suggestion?

Open an issue on GitHub: [y-fares/meeting_brain/issues](https://github.com/y-fares/meeting_brain/issues)

---

**Last Updated**: August 6, 2026  
**Version**: 1.0.0  
**Status**: Production Ready ✅
