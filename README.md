# 🤖 OWNO BRIAN OITOENO CHATBOT

**Developer: Owino Brian Otieno**

A professional browser-based Streamlit chatbot and data workspace for
technology, computer science, programming, artificial intelligence, academic
research, software development, data, cloud, DevOps and cybersecurity.

The application is designed as a user-facing AI assistant rather than a
developer diagnostic console.

---

## ✨ Main interface

The application has a genuine browser GUI built with Streamlit.

It includes:

- **OWNO BRIAN OITOENO CHATBOT** identity
- **New chat**
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

The application identity is:

**OWNO BRIAN OITOENO CHATBOT**

The visible brand is intentionally kept simple as:

**OWNO BRIAN**

It does not use “Owino Brian Tech Suite” branding.

---

# 🧠 Knowledge coverage

The internal response engine covers a broad range of topics.

### Programming

Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, PHP, Ruby,
Kotlin, Swift, Dart, Scala, SQL, Bash, PowerShell, algorithms, data
structures, recursion, debugging, testing, APIs, REST, GraphQL, JSON, XML,
YAML, object-oriented programming and functional programming.

### Artificial intelligence

Artificial intelligence, machine learning, deep learning, generative AI,
large language models, transformers, attention, RAG, AI agents, agentic AI,
embeddings, vector databases, semantic search, prompt engineering, prompt
injection, AI evaluation, model evaluation, model drift, data leakage,
overfitting, underfitting, supervised learning, unsupervised learning,
reinforcement learning, computer vision, NLP, speech recognition, OCR,
recommendation systems, knowledge bases, fine-tuning, transfer learning,
MLOps, responsible AI, explainable AI, AI governance, AI security and AI
privacy.

### Computer science

Operating systems, computer architecture, computer networks, distributed
systems, databases, compilers, concurrency, parallel computing, information
theory, cryptography, software engineering, software architecture, complexity
and computer-science fundamentals.

### Cloud and DevOps

AWS, Microsoft Azure, Google Cloud, Docker, Kubernetes, Terraform, Ansible,
CI/CD, GitHub Actions, Jenkins, Linux, serverless, microservices, event-driven
architecture, message queues, API gateways, load balancing, caching, CDN,
observability, high availability, disaster recovery, infrastructure as code,
containers, virtual machines and cloud security.

### Data

Data analysis, data cleaning, data quality, data governance, data lineage,
metadata, schemas, CSV, JSON, Excel, Pandas, NumPy, Matplotlib,
Scikit-learn, PyTorch, TensorFlow, Apache Spark, Apache Kafka, ETL, ELT,
data warehouses, data lakes, SQL, PostgreSQL, MySQL, MongoDB, Redis, NoSQL,
ORMs, indexing, normalisation, transactions, ACID, visualisation, statistics,
correlation, regression, classification, clustering and anomaly detection.

### Cybersecurity

Cybersecurity, information security, encryption, cryptography,
authentication, authorisation, OAuth, JWT, TLS, HTTPS, MFA, IAM, zero trust,
least privilege, firewalls, secure coding, threat modelling, penetration
testing, OWASP, SQL injection, cross-site scripting, CSRF, incident response,
backups, disaster recovery and vulnerability management.

### Academic research

Research methodology, research design, research questions, objectives,
hypotheses, literature reviews, systematic reviews, qualitative research,
quantitative research, mixed methods, sampling, interviews, surveys, case
studies, content analysis, thematic analysis, statistics, validity,
reliability, research ethics, research gaps, conceptual frameworks,
theoretical frameworks, academic argument, critical analysis, synthesis,
abstracts, introductions, methodology chapters, results chapters, discussion
chapters, conclusions, recommendations, proposals, dissertations and theses.

### Referencing

IEEE, Harvard, APA, Chicago and MLA referencing, in-text citations, reference
lists, bibliographies, annotated bibliographies, DOI references and citations
for journals, books, conference papers, websites, datasets and software.

---

# 🌐 Live information

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

# 💬 Conversational behaviour

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

For example:

```text
User: Hello

OWNO BRIAN OITOENO CHATBOT:
Hello! I am the OWNO BRIAN OITOENO CHATBOT. I can help with technology,
computer science, programming, AI, academic research, software development,
data, cloud, DevOps and cybersecurity. What would you like to work on?
```

The application does not expose awkward backend messages such as:

```text
I could not use an AI model key...
```

and does not display internal API configuration diagnostics to normal users.

---

# 📎 File workspace

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

# 🗂️ Chat history

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

# 🎨 GUI architecture

This is a browser GUI, not a desktop Tkinter program.

The application uses:

```text
Browser
   ↓
Streamlit GUI
   ↓
Chat / History / Files
   ↓
Internal response engine
   ↓
Optional live public research
```

It does **not** require:

```python
import tkinter
```

It does **not** create:

```python
tk.Tk()
```

and does **not** call:

```python
root.mainloop()
```

This prevents the `_tkinter` problem associated with deploying a Tkinter
desktop application into a Streamlit cloud environment.

---

# 🚀 Local installation

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

# ☁️ Deployment

Upload the three files to your GitHub repository yourself.

For Streamlit Community Cloud:

1. Open your Streamlit deployment dashboard.
2. Select your GitHub repository.
3. Choose `chatbot_assistant.py` as the main application file.
4. Deploy.
5. Wait for dependencies to install.
6. Open the application.

Official documentation:

- https://docs.streamlit.io/
- https://docs.streamlit.io/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app

---

# 📦 Dependencies

The application uses:

```text
streamlit
pandas
requests
openpyxl
```

No Tkinter dependency is required.

---

# 🔐 Secrets and security

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

# 🤖 AI-model expansion

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

- OpenAI or other model providers
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

# 💡 Example questions

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

# 📊 Data workflow

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

# 🔬 Academic workflow

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

# 🧪 Troubleshooting

## `_tkinter` error

If you see:

```text
ImportError: No module named '_tkinter'
```

make sure the deployed `chatbot_assistant.py` is the current version and does
not contain Tkinter imports.

This application uses Streamlit as its GUI.

## Missing module

Run:

```bash
pip install -r requirements.txt
```

Then restart Streamlit.

## Live search unavailable

Public services can have rate limits, outages or query restrictions. The
internal response catalogue remains available.

## Chat history does not survive deployment

Some cloud environments use ephemeral storage. For permanent multi-user
history, use a managed database.

---

# 📁 Repository structure

```text
ai-chatbot-and-data-utilities/
│
├── chatbot_assistant.py
├── README.md
└── requirements.txt
```

Runtime:

```text
owino_chat_history.db
```

may be created automatically when the application runs.

---

# 👨‍💻 Developer

**Owino Brian Otieno**

Developer of:

**OWNO BRIAN OITOENO CHATBOT**

Application identity:

**OWNO BRIAN OITOENO CHATBOT**

Visible brand:

**OWNO BRIAN**

---

# 💼 Professional inquiries

Need custom chatbots, AI integrations, software documentation, data
automation, research-support systems or development workflows?

**Sponsor the project or book a milestone retainer:**

https://github.com/sponsors/owino-brian

---

# 📌 Project direction

The application is structured as an extensible foundation. Future releases
can add stronger model integration, document RAG, authentication, managed
conversation storage, advanced analytics, richer research tools and additional
live-data sources without changing the clean user-facing interface.
