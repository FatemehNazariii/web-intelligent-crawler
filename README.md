# Web Intelligent Crawler

A web-based intelligent research assistant that automatically searches the web, extracts relevant information, and generates structured research reports using Large Language Models (LLMs).

---

## Overview

Web Intelligent Crawler is an AI-powered research assistant designed to automate the research process. Instead of manually searching multiple websites and summarizing information, users simply enter a research topic. The system then:

1. Searches the web for relevant sources.
2. Crawls and extracts useful content.
3. Cleans and processes the extracted text.
4. Sends the processed information to a local Large Language Model (LLM).
5. Generates a structured research report.

---

## Features

- User registration and authentication
- Intelligent web search
- Automatic web crawling
- HTML content extraction
- Text preprocessing and cleaning
- AI-powered report generation
- Research history management
- Modular architecture
- Local LLM support via Ollama

---

## System Architecture

```
User
   │
   ▼
Next.js Frontend
   │
REST API
   │
   ▼
Django Backend
   │
   ├── Authentication
   ├── Research Service
   ├── Crawler Service
   ├── LLM Service
   └── Storage Service
           │
           ▼
        Database
           │
           ▼
       Ollama (LLM)
```

---

## Technologies

### Frontend

- Next.js
- React
- Tailwind CSS

### Backend

- Django
- Django REST Framework

### AI & NLP

- Ollama
- Large Language Models (LLMs)

### Web Crawling

- BeautifulSoup
- Requests

### Database

- SQLite (Development)

### Testing

- Pytest

---

## Project Structure

```
backend/
│
├── crawler/
│   ├── services/
│   ├── models.py
│   ├── views.py
│   └── urls.py
│
├── tests/
├── manage.py
└── requirements.txt

frontend/
│
├── app/
├── components/
├── context/
└── package.json
```

---

## Installation

### Clone the repository

```bash
git clone https://github.com/yourusername/web-intelligent-crawler.git
```

### Backend

```bash
cd backend

python -m venv venv

source venv/bin/activate
```

Windows

```bash
venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run migrations

```bash
python manage.py migrate
```

Start backend

```bash
python manage.py runserver
```

---

### Frontend

```bash
cd frontend

npm install

npm run dev
```

---

### Ollama

Install Ollama and pull your preferred model.

Example:

```bash
ollama pull llama3
```

Run:

```bash
ollama serve
```

---

## Running Tests

```bash
pytest
```

or

```bash
python -m pytest
```

---

## Future Improvements

- Retrieval-Augmented Generation (RAG)
- Vector Database Integration
- Multi-turn Conversation Memory
- Source Ranking
- Image and PDF Analysis
- Multi-language Support

---

## Author

Developed as a Bachelor's Graduation Project.

---

## License

This project is intended for educational and research purposes.
