# CG-Matrix Gen System — Streamlit Edition

AI-powered assessment question generation with CG Matrix, multi-agent pipeline, and 5 question types.

## Setup

```bash
pip install -r requirements.txt
```

## Configure API Keys

Create `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "AIzaSy..."
GEMINI_API_KEY_1 = "AIzaSy..."
APP_SECRET = "your-password"
```

## Run

```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Add secrets in the dashboard
5. Deploy

## Features

- **Quick Generate**: Input → Questions in one click
- **Full Pipeline**: 4-gate SME review (Subskills → Content Scope → Hess Matrix → Questions)
- **5 Question Types**: MCQ, Fill Blank, Error Analysis, Match, Arrange
- **UK English**: Enforced in all generation
- **Exemplar Search**: Searches NCERT, CBSE, DIKSHA before generating
- **Feedback & Refine**: Iterate on generated questions
- **Excel Export**: Download complete question bank
