# ComicCraft 🎨✨

**ComicCraft** is an AI-powered comic story creator. It transforms your ideas into structured 5-panel illustrated comic books with consistent characters, narrations, dialogues, and downloadable PDF exports.

---

## 🚀 Features

- **AI-Powered Story Generation**: Generates 5-panel comic storylines using Google Gemini AI with narrations and character dialogue.
- **Character Consistency**: Maintains consistent visual identity and descriptions across every panel.
- **AI Art Illustration**: Generates styled panel illustrations across styles (Anime, Comic Book, Watercolor, Pixel Art, etc.).
- **Per-Panel Regeneration**: Regenerate individual panels without altering the rest of your story.
- **Story Continuation**: Continue your adventure across multiple chapters.
- **PDF Export**: Export your comics to styled, publication-ready PDF documents with automatic emoji & symbol formatting.
- **Comic Library**: Save, favorite, search, and manage your comics.
- **User Authentication**: Secure user login and registration with bcrypt & JWT session cookies.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: SQLite (SQLAlchemy ORM) / MongoDB Atlas
- **AI Providers**: Google Gemini API (`gemini-2.0-flash` / `gemini-1.5-pro`)
- **PDF Generation**: FPDF2 with Latin-1 safety and emoji conversion
- **Frontend**: Vanilla JS, Jinja2 Templates, HTML5/CSS3, FontAwesome Icons

---

## 📦 Project Structure

```text
NM3/
├── app/
│   ├── ai/            # Gemini & Image generation providers
│   ├── database/      # Database session & models
│   ├── models/        # SQLAlchemy models (User, Comic, Panel, Job)
│   ├── routes/        # FastAPI endpoints (web, auth, comics)
│   ├── schemas/       # Pydantic validation schemas
│   ├── services/      # Business logic & PDF generation
│   ├── static/        # CSS, JavaScript, and asset files
│   ├── templates/     # Jinja2 HTML templates
│   └── utils/         # Helper functions & security
├── storage/           # Generated comic assets & PDF exports
├── tests/             # Unit and integration test suite
├── .env.example       # Template for environment variables
├── .gitignore         # Git ignore configuration
├── requirements.txt   # Python dependencies
└── run.py             # Server launcher
```

---

## ⚡ Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and fill in your settings:
```bash
cp .env.example .env
```

Key environment variables:
```env
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_secure_random_secret_key
DEMO_MODE=false
```

### 5. Run the application
```bash
python run.py
```

Open your browser and visit: **[http://localhost:8000](http://localhost:8000)**

---

## 🧪 Running Tests

```bash
pytest
```

---

## 📄 License

MIT License. See `LICENSE` for details.
