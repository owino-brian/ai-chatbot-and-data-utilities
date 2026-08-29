# OBO CHATBOT

**Developer: Owino Brian Otieno**

A professional browser-based Streamlit chatbot and data workspace for
technology, computer science, programming, artificial intelligence, academic
research, software development, data, cloud, DevOps and cybersecurity.

The application is designed as a user-facing AI assistant rather than a
developer diagnostic console.

---

## Main interface

The application has a genuine browser GUI built with Streamlit.

It includes:

**OBO CHATBOT** identity
- New chat
- Recent chat history
- Persistent local conversation history
- User and assistant chat bubbles
- Natural chat input
- Live-information toggle
- File upload workspace
- Dataset preview
- Dataset cleaning
- CSV download
- Collapsible sources
- Professional welcome cards
- Developer attribution

The developer displayed by the application is:

**Owino Brian Otieno**

---


# Live information

When **Use live information** is enabled, the application can query public
sources.

Current connectors include:

- GitHub
- Stack Overflow
- Crossref
- OpenAlex
- Wikipedia

Examples of questions that can trigger live research:

```text
Find current GitHub projects for Python data engineering.
```

```text
Find recent research about large language models.
```

```text
What are current developer discussions about this error?
```

```text
Find scholarly publications about RAG evaluation.
```

The application displays sources in a collapsible section so the normal chat
does not become cluttered.

Live retrieval is evidence, not a guarantee of correctness. Users should
check source authority, date and context when information matters.

---

# Conversational behaviour

The chatbot has explicit handling for common conversational messages:

- Hello
- Hi
- Hey
- Good morning
- Good afternoon
- Good evening
- Who are you?
- What can you do?
- How are you?
- Thank you
- Thanks
- Goodbye
- I don't understand
- Simplify this

# File workspace

Supported uploads:

- CSV
- XLSX
- XLS
- JSON
- TXT
- Markdown

The workspace provides:

- row count
- column count
- missing-value count
- duplicate count
- data preview
- column-name cleaning
- duplicate removal
- cleaned CSV download

The upload limit is 50 MB in the current application.

For a production system, add authentication, file scanning, access controls,
retention policies and secure storage.

---

# Chat history

Conversation history is stored in SQLite.

The user can:

1. Click **＋ New chat**.
2. Ask questions.
3. Return to a previous conversation.
4. Continue from its stored messages.

The runtime database file is:

```text
owino_chat_history.db
```

This is an internal implementation detail and is not displayed in the normal
chat interface.

For a multi-user production deployment, a managed database with authentication
should replace local SQLite persistence.

---

# Local installation

## 1. Create the project folder

Place these files together:

```text
ai-chatbot-and-data-utilities/
├── chatbot_assistant.py
├── README.md
└── requirements.txt
```

## 2. Create a virtual environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Start the GUI

```bash
streamlit run chatbot_assistant.py
```

The command starts the browser-based interface.

---


# Dependencies

The application uses:

```text
streamlit
pandas
requests
openpyxl
```

No Tkinter dependency is required.

---

# Secrets and security

The current application does not require an AI provider key merely to start.

If model integration is added later, credentials should be stored in the
deployment platform's secrets manager rather than inside Python source code.

Never commit:

- passwords
- private API keys
- access tokens
- private database credentials
- personal secrets

For production use, consider:

- authentication
- authorisation
- rate limiting
- secure file handling
- managed databases
- audit logging
- encryption
- privacy controls
- data retention policies

---

# AI-model expansion

The current application intentionally remains useful without requiring an
external AI model.

It combines:

1. conversational responses,
2. a large internal technical and academic response catalogue,
3. live public-information retrieval,
4. file/data utilities.

This avoids showing users an error message simply because a model API key has
not been configured.

A future version can add a model provider behind the same interface. The model
implementation should remain an internal backend detail rather than becoming
part of the visible user experience.

Possible future features:
- model routing
- RAG
- embeddings
- vector search
- document processing
- PDF support
- DOCX support
- PPTX support
- OCR
- long-term memory
- tool calling
- AI agents
- evaluation
- cost monitoring
- response-quality scoring

---

# Example questions

```text
Hello
```

```text
Who are you?
```

```text
What can you do?
```

```text
What is cloud computing?
```

```text
Explain Docker and Kubernetes.
```

```text
What is the difference between Python and JavaScript?
```

```text
Explain Big O notation.
```

```text
How do I build a REST API?
```

```text
Why is my Python code producing an exception?
```

```text
Explain RAG.
```

```text
What is prompt injection?
```

```text
What is the difference between qualitative and quantitative research?
```

```text
How do I write a literature review?
```

```text
What is a research gap?
```

```text
How does IEEE referencing work?
```

```text
How do I analyse a CSV dataset?
```

```text
Find current research about large language models.
```

```text
Find current GitHub projects related to Python.
```

---

# Data workflow

```text
Upload file
    ↓
Inspect dataset
    ↓
Preview records
    ↓
Check missing values
    ↓
Check duplicates
    ↓
Clean column names
    ↓
Remove duplicates
    ↓
Download CSV
```

Future versions can add:

- descriptive statistics
- correlation matrices
- regression
- classification
- clustering
- anomaly detection
- interactive charts
- automated data-quality reports
- database connections
- SQL workspaces

---

# Academic workflow

```text
Research question
       ↓
Literature discovery
       ↓
Evidence collection
       ↓
Analysis
       ↓
Interpretation
       ↓
Academic writing
       ↓
References
```

Academic information should be checked against authoritative sources before
submission. The chatbot should not invent citations, DOI values or publication
details.

---
# Developer

**Owino Brian Otieno**

Developer of:

**OBO CHATBOT**

Application identity:

**OBO CHATBOT**

My brand:

**Xerxes Brian Tech**

---

# Professional inquiries

Need custom chatbots, AI integrations, software documentation, data
automation, research-support systems or development workflows?

**Sponsor the project or book a milestone retainer:**

https://github.com/sponsors/owino-brian

---

# Project direction

The application is structured as an extensible foundation. Future releases
can add stronger model integration, document RAG, authentication, managed
conversation storage, advanced analytics, richer research tools and additional
live-data sources without changing the clean user-facing interface.
