"""
Enterprise Technical Suite
Streamlit edition - web/cloud safe
Developer: Owino Brian Otieno

Key design goals:
- No tkinter/Tk dependencies.
- Streamlit-native graphical interface.
- SQLite persistence for local application data.
- Live public data retrieval from several research/developer APIs.
- Optional AI provider for broad natural-language answers.
- CSV/Excel/JSON ETL utilities.
- Research-oriented citations/links in the UI.
"""

import io
import json
import os
import re
import sqlite3
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st


# =============================================================================
# APP CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Owino Brian | Enterprise Technical Suite",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "Owino Brian Enterprise Technical Suite"
DB_PATH = "enterprise_suite.db"
HTTP_TIMEOUT = 12

TECH_CATEGORIES = {
    "Artificial Intelligence": [
        "machine learning", "deep learning", "large language models",
        "generative AI", "RAG", "AI agents", "computer vision",
        "natural language processing", "reinforcement learning",
        "MLOps", "embeddings", "vector databases"
    ],
    "Software Development": [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#",
        "Go", "Rust", "PHP", "Django", "FastAPI", "Flask",
        "React", "Next.js", "Node.js", "Spring Boot"
    ],
    "Data Engineering": [
        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
        "Apache Spark", "Apache Kafka", "Airflow", "dbt",
        "Pandas", "Polars", "ETL", "ELT", "data warehouse"
    ],
    "Cloud & DevOps": [
        "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes",
        "Terraform", "GitHub Actions", "GitLab CI", "CI/CD",
        "serverless", "observability", "Infrastructure as Code"
    ],
    "Cybersecurity": [
        "OAuth", "JWT", "TLS", "encryption", "zero trust",
        "IAM", "penetration testing", "threat modelling",
        "vulnerability management", "secure coding"
    ],
    "Academic & Research": [
        "research methodology", "literature review", "systematic review",
        "qualitative research", "quantitative research", "statistics",
        "machine learning research", "computer science", "IEEE",
        "Harvard referencing", "thesis", "dissertation"
    ],
    "General Computing": [
        "algorithms", "data structures", "operating systems",
        "computer networks", "databases", "distributed systems",
        "software engineering", "computer architecture"
    ],
}


# =============================================================================
# DATABASE
# =============================================================================

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            intent TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS research_cache (
            cache_key TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            query TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            rating INTEGER,
            comment TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            topic TEXT NOT NULL,
            description TEXT NOT NULL,
            keywords TEXT NOT NULL
        )
    """)

    # Seed a broad local knowledge catalogue once.
    cur.execute("SELECT COUNT(*) FROM knowledge_base")
    if cur.fetchone()[0] == 0:
        rows = []
        for category, topics in TECH_CATEGORIES.items():
            for topic in topics:
                rows.append((
                    category,
                    topic,
                    f"Reference topic in {category}: {topic}.",
                    json.dumps([topic.lower(), category.lower()])
                ))
        cur.executemany(
            "INSERT INTO knowledge_base(category, topic, description, keywords) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )

    conn.commit()
    conn.close()


init_db()


def save_message(session_id: str, role: str, content: str, intent: str = "") -> None:
    conn = db()
    conn.execute(
        "INSERT INTO conversations(session_id, role, content, intent, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            session_id,
            role,
            content,
            intent,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def conversation_count() -> int:
    conn = db()
    value = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    conn.close()
    return int(value)


# =============================================================================
# SESSION STATE
# =============================================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:12]

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_sources" not in st.session_state:
    st.session_state.last_sources = []

if "last_live_results" not in st.session_state:
    st.session_state.last_live_results = []

if "last_query" not in st.session_state:
    st.session_state.last_query = ""


# =============================================================================
# NETWORK HELPERS
# =============================================================================

def safe_get(url: str, params: Optional[dict] = None,
             headers: Optional[dict] = None) -> Optional[requests.Response]:
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers or {"User-Agent": "OwinoBrianEnterpriseSuite/2.0"},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response
    except requests.RequestException:
        return None


def get_json(url: str, params: Optional[dict] = None) -> Optional[dict]:
    response = safe_get(url, params=params)
    if response is None:
        return None
    try:
        return response.json()
    except ValueError:
        return None


# =============================================================================
# LIVE DATA SOURCES
# =============================================================================

def search_github(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    data = get_json(
        "https://api.github.com/search/repositories",
        {"q": query, "sort": "stars", "order": "desc", "per_page": limit},
    )
    if not data:
        return []

    results = []
    for item in data.get("items", []):
        results.append({
            "source": "GitHub",
            "title": item.get("full_name", ""),
            "summary": item.get("description") or "No repository description.",
            "url": item.get("html_url", ""),
            "metadata": (
                f"★ {item.get('stargazers_count', 0):,} | "
                f"Forks {item.get('forks_count', 0):,} | "
                f"Language: {item.get('language') or 'N/A'}"
            ),
        })
    return results


def search_stackoverflow(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    data = get_json(
        "https://api.stackexchange.com/2.3/search/advanced",
        {
            "site": "stackoverflow",
            "q": query,
            "order": "desc",
            "sort": "relevance",
            "pagesize": limit,
            "filter": "default",
        },
    )
    if not data:
        return []

    results = []
    for item in data.get("items", []):
        results.append({
            "source": "Stack Overflow",
            "title": re.sub(r"<[^>]+>", "", item.get("title", "")),
            "summary": (
                f"Score {item.get('score', 0)} | "
                f"Answers {item.get('answer_count', 0)} | "
                f"Tags: {', '.join(item.get('tags', []))}"
            ),
            "url": item.get("link", ""),
            "metadata": "Community developer question",
        })
    return results


def search_crossref(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    data = get_json(
        "https://api.crossref.org/works",
        {"query": query, "rows": limit, "select":
         "title,author,published,DOI,URL,container-title,type"},
    )
    if not data:
        return []

    results = []
    for item in data.get("message", {}).get("items", []):
        title = (item.get("title") or ["Untitled"])[0]
        journal = (item.get("container-title") or [""])[0]
        year = ""
        date_parts = item.get("published", {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = str(date_parts[0][0])

        results.append({
            "source": "Crossref",
            "title": title,
            "summary": f"{journal} | {year} | DOI: {item.get('DOI', 'N/A')}",
            "url": item.get("URL") or (
                f"https://doi.org/{item.get('DOI')}" if item.get("DOI") else ""
            ),
            "metadata": item.get("type", "research work"),
        })
    return results


def search_openalex(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    data = get_json(
        "https://api.openalex.org/works",
        {"search": query, "per-page": limit},
    )
    if not data:
        return []

    results = []
    for item in data.get("results", []):
        title = item.get("display_name") or "Untitled work"
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in item.get("authorships", [])[:3]
        )
        results.append({
            "source": "OpenAlex",
            "title": title,
            "summary": (
                f"Year: {item.get('publication_year', 'N/A')} | "
                f"Citations: {item.get('cited_by_count', 0):,} | "
                f"Authors: {authors or 'N/A'}"
            ),
            "url": item.get("doi") or item.get("id", ""),
            "metadata": "Open scholarly metadata",
        })
    return results


def search_hackernews(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    data = get_json(
        "https://hn.algolia.com/api/v1/search",
        {"query": query, "tags": "story", "hitsPerPage": limit},
    )
    if not data:
        return []

    results = []
    for item in data.get("hits", []):
        title = item.get("title") or item.get("story_title") or "Untitled"
        url = item.get("url") or (
            f"https://news.ycombinator.com/item?id={item.get('objectID')}"
        )
        results.append({
            "source": "Hacker News",
            "title": title,
            "summary": (
                f"Points: {item.get('points', 0)} | "
                f"Comments: {item.get('num_comments', 0)}"
            ),
            "url": url,
            "metadata": "Developer/technology community",
        })
    return results


def search_wikipedia(query: str) -> List[Dict[str, Any]]:
    data = get_json(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 6,
        },
    )
    if not data:
        return []

    results = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        results.append({
            "source": "Wikipedia",
            "title": title,
            "summary": re.sub(r"<[^>]+>", "", item.get("snippet", "")),
            "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
            "metadata": "General reference",
        })
    return results


def search_pypi(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    # PyPI's public JSON endpoint is excellent for exact package lookups.
    clean = query.strip().split()[0] if query.strip() else ""
    if not clean:
        return []
    data = get_json(f"https://pypi.org/pypi/{clean}/json")
    if not data:
        return []

    info = data.get("info", {})
    return [{
        "source": "PyPI",
        "title": info.get("name", clean),
        "summary": info.get("summary") or "Python package",
        "url": info.get("project_url") or info.get("package_url", ""),
        "metadata": (
            f"Version: {info.get('version', 'N/A')} | "
            f"Python package"
        ),
    }]


def live_research(query: str, sources: List[str]) -> List[Dict[str, Any]]:
    all_results = []

    for source in sources:
        if source == "GitHub":
            all_results.extend(search_github(query))
        elif source == "Stack Overflow":
            all_results.extend(search_stackoverflow(query))
        elif source == "Crossref":
            all_results.extend(search_crossref(query))
        elif source == "OpenAlex":
            all_results.extend(search_openalex(query))
        elif source == "Hacker News":
            all_results.extend(search_hackernews(query))
        elif source == "Wikipedia":
            all_results.extend(search_wikipedia(query))
        elif source == "PyPI":
            all_results.extend(search_pypi(query))

    return all_results


# =============================================================================
# OPTIONAL AI ANSWER ENGINE
# =============================================================================

def get_ai_settings() -> Tuple[str, str, str]:
    api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    model = st.secrets.get(
        "OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    )
    base_url = st.secrets.get(
        "OPENAI_BASE_URL",
        os.getenv("OPENAI_BASE_URL", "https://api.openai.com"),
    ).rstrip("/")
    return api_key, model, base_url


def ask_ai(question: str, evidence: List[Dict[str, Any]]) -> Optional[str]:
    api_key, model, base_url = get_ai_settings()
    if not api_key:
        return None

    evidence_text = "\n".join(
        f"- [{x['source']}] {x['title']}: {x['summary']} {x['url']}"
        for x in evidence[:18]
    )

    system_prompt = """
You are a broad technical and academic research assistant.
Answer clearly and accurately. Distinguish established facts from
recommendations or inference. For academic questions, help with
research design, literature review, computer science, referencing,
data analysis and dissertation writing. For development questions,
provide practical explanations and safe production-oriented code.
For AI questions, explain architectures, evaluation, RAG, agents,
ML, data and deployment. Do not invent citations or claim that a
live source says something it does not say.

When live evidence is supplied, use it as evidence and include a
short Sources section containing the supplied source names/URLs.
"""

    user_prompt = f"""
Question:
{question}

Live research evidence:
{evidence_text or "No live evidence was retrieved."}
"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, TypeError):
        return None


# =============================================================================
# LOCAL KNOWLEDGE / FALLBACK ANSWER
# =============================================================================

def detect_topics(question: str) -> List[str]:
    q = question.lower()
    matches = []

    for category, topics in TECH_CATEGORIES.items():
        for topic in topics:
            if topic.lower() in q:
                matches.append(f"{category}: {topic}")

    return list(dict.fromkeys(matches))[:12]


def fallback_answer(question: str, evidence: List[Dict[str, Any]]) -> str:
    topics = detect_topics(question)

    if evidence:
        lines = [
            "I could not use an AI model key, so I am answering from the live "
            "retrieval results rather than pretending to have generated a full "
            "model-based answer.",
            "",
            f"**Question:** {question}",
            "",
            "**Relevant live findings:**",
        ]
        for item in evidence[:8]:
            lines.append(
                f"- **{item['source']} — {item['title']}**: "
                f"{item['summary']}"
            )
        if topics:
            lines.extend(["", "**Detected technical areas:**"])
            lines.extend(f"- {x}" for x in topics)
        return "\n".join(lines)

    if topics:
        return (
            "I identified these areas in your question: "
            + ", ".join(topics)
            + ". Enable an AI provider key in Streamlit Secrets for "
              "full natural-language answers, or use the Live Research "
              "tab to retrieve current evidence."
        )

    return (
        "I can route this question to the live research connectors, but a "
        "general-purpose AI answer requires an AI provider API key. Add "
        "OPENAI_API_KEY in Streamlit Secrets, then retry the question."
    )


# =============================================================================
# ETL ENGINE
# =============================================================================

def clean_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    original_rows = len(df)
    working = df.copy()

    working.columns = [
        re.sub(r"\s+", "_", str(c).strip().lower())
        for c in working.columns
    ]

    missing_before = int(working.isna().sum().sum())

    for column in working.columns:
        if pd.api.types.is_object_dtype(working[column]):
            working[column] = working[column].astype(str).str.strip()

    # Standard email cleaning if an email field exists.
    email_columns = [c for c in working.columns if "email" in c]
    invalid_emails = 0
    if email_columns:
        col = email_columns[0]
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        invalid_mask = ~working[col].fillna("").astype(str).str.match(pattern)
        invalid_emails = int(invalid_mask.sum())

    working = working.drop_duplicates().reset_index(drop=True)
    missing_after = int(working.isna().sum().sum())

    metrics = {
        "input_rows": original_rows,
        "output_rows": len(working),
        "duplicates_removed": original_rows - len(working),
        "missing_values_before": missing_before,
        "missing_values_after": missing_after,
        "invalid_emails_detected": invalid_emails,
        "columns": len(working.columns),
    }

    return working, metrics


# =============================================================================
# UI STYLING
# =============================================================================

st.markdown("""
<style>
    .main {
        background: #0b1020;
    }
    .block-container {
        max-width: 1500px;
        padding-top: 1.2rem;
    }
    .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #111a33, #18284a);
        border: 1px solid #2b416b;
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0;
        font-size: 2.2rem;
    }
    .hero p {
        color: #b8c7e0;
        margin-top: .45rem;
    }
    .card {
        padding: 1rem;
        border-radius: 14px;
        border: 1px solid #293958;
        background: #111827;
        min-height: 120px;
    }
    .small {
        color: #9fb0ca;
        font-size: .86rem;
    }
    .source {
        padding: .7rem;
        border-radius: 10px;
        background: #101827;
        border: 1px solid #25334d;
        margin-bottom: .5rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.title("🧠 Control Centre")
    st.caption("Enterprise AI, research, development and data workspace")

    research_sources = st.multiselect(
        "Live research sources",
        [
            "GitHub",
            "Stack Overflow",
            "Crossref",
            "OpenAlex",
            "Hacker News",
            "Wikipedia",
            "PyPI",
        ],
        default=["GitHub", "Stack Overflow", "Crossref", "OpenAlex"],
    )

    st.divider()

    api_key, ai_model, _ = get_ai_settings()
    if api_key:
        st.success(f"AI engine enabled · {ai_model}")
    else:
        st.warning(
            "AI engine is not configured. Live research and the local "
            "knowledge catalogue still work."
        )

    st.metric("Conversation records", conversation_count())
    st.caption(f"Session: `{st.session_state.session_id}`")

    if st.button("🧹 Start New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_sources = []
        st.rerun()

    st.divider()
    st.caption("Supported areas")
    for category in TECH_CATEGORIES:
        st.write(f"• {category}")


# =============================================================================
# HEADER / DASHBOARD
# =============================================================================

st.markdown("""
<div class="hero">
    <h1>🧠 Enterprise Technical Intelligence Suite</h1>
    <p>
        Live research • AI assistant • academic research • software engineering
        • data engineering • DevOps • cloud • cybersecurity • ETL
    </p>
</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Knowledge domains", len(TECH_CATEGORIES))
m2.metric("Live connectors", 7)
m3.metric("Database", "SQLite")
m4.metric("Session turns", len(st.session_state.messages))


# =============================================================================
# MAIN TABS
# =============================================================================

chat_tab, research_tab, etl_tab, database_tab, system_tab = st.tabs([
    "💬 AI Assistant",
    "🌐 Live Research",
    "🧹 Data / ETL",
    "🗄️ Knowledge Database",
    "⚙️ System"
])


# =============================================================================
# CHAT TAB
# =============================================================================

with chat_tab:
    left, right = st.columns([2.2, 1])

    with right:
        st.subheader("Answer controls")
        auto_research = st.toggle(
            "Use live research automatically",
            value=True,
            help="Retrieve current evidence before generating an answer.",
        )
        max_sources = st.slider("Evidence records", 3, 20, 8)

        st.info(
            "For genuinely broad questions, configure OPENAI_API_KEY in "
            "Streamlit Secrets. Without it, the app will not pretend that "
            "a rule-based matcher is a general AI model."
        )

    with left:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        question = st.chat_input(
            "Ask about AI, programming, databases, cloud, cybersecurity, "
            "research, algorithms, DevOps, academic writing, etc."
        )

        if question:
            st.session_state.last_query = question
            st.session_state.messages.append({
                "role": "user",
                "content": question,
            })
            save_message(st.session_state.session_id, "user", question)

            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Analysing question and retrieving current evidence..."):
                    evidence = []
                    if auto_research and research_sources:
                        evidence = live_research(question, research_sources)
                        evidence = evidence[:max_sources]

                    answer = ask_ai(question, evidence)
                    if not answer:
                        answer = fallback_answer(question, evidence)

                    st.markdown(answer)

                    if evidence:
                        st.markdown("#### Live evidence used")
                        for item in evidence[:max_sources]:
                            st.markdown(
                                f"- **{item['source']} — {item['title']}**  \n"
                                f"  {item['summary']}  \n"
                                f"  {item['url']}"
                            )

            st.session_state.last_sources = evidence
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
            })
            save_message(st.session_state.session_id, "assistant", answer)


# =============================================================================
# LIVE RESEARCH TAB
# =============================================================================

with research_tab:
    st.subheader("🌐 Live Technology & Academic Research")

    rq1, rq2 = st.columns([4, 1])
    with rq1:
        query = st.text_input(
            "Research query",
            value=st.session_state.last_query,
            placeholder="e.g. RAG evaluation, Python FastAPI, transformer architecture",
        )
    with rq2:
        run_search = st.button("🔎 Search Live", type="primary", use_container_width=True)

    if run_search and query.strip():
        with st.spinner("Querying live public sources..."):
            results = live_research(query.strip(), research_sources)
        st.session_state.last_live_results = results

    results = st.session_state.last_live_results

    if results:
        st.success(f"Retrieved {len(results)} live records.")
        for item in results:
            st.markdown(
                f"""
                <div class="source">
                    <strong>{item['source']}</strong><br>
                    <a href="{item['url']}" target="_blank">{item['title']}</a><br>
                    <span class="small">{item['summary']}</span><br>
                    <span class="small">{item['metadata']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Run a live search to populate current research results.")


# =============================================================================
# ETL TAB
# =============================================================================

with etl_tab:
    st.subheader("🧹 Data Engineering & ETL Workspace")
    st.write(
        "Upload CSV, Excel or JSON data. The pipeline normalises column names, "
        "trims text, removes duplicates and reports quality metrics."
    )

    uploaded = st.file_uploader(
        "Upload a dataset",
        type=["csv", "xlsx", "xls", "json"],
    )

    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                source_df = pd.read_csv(uploaded)
            elif uploaded.name.lower().endswith((".xlsx", ".xls")):
                source_df = pd.read_excel(uploaded)
            else:
                source_df = pd.read_json(uploaded)

            st.write("### Source preview")
            st.dataframe(source_df.head(100), use_container_width=True)

            cleaned_df, metrics = clean_dataframe(source_df)

            st.write("### Pipeline metrics")
            cols = st.columns(len(metrics))
            for col, (key, value) in zip(cols, metrics.items()):
                col.metric(key.replace("_", " ").title(), value)

            st.write("### Cleaned data")
            st.dataframe(cleaned_df.head(100), use_container_width=True)

            csv_bytes = cleaned_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download cleaned CSV",
                data=csv_bytes,
                file_name="cleaned_dataset.csv",
                mime="text/csv",
            )

        except Exception as exc:
            st.error(f"Could not process this file: {exc}")


# =============================================================================
# KNOWLEDGE DATABASE TAB
# =============================================================================

with database_tab:
    st.subheader("🗄️ Local Knowledge Catalogue")

    conn = db()
    df_kb = pd.read_sql_query(
        "SELECT id, category, topic, description FROM knowledge_base "
        "ORDER BY category, topic",
        conn,
    )
    conn.close()

    c1, c2 = st.columns([2, 1])
    with c1:
        kb_search = st.text_input("Search the local catalogue")
    with c2:
        kb_category = st.selectbox(
            "Category",
            ["All"] + sorted(df_kb["category"].unique().tolist()),
        )

    filtered = df_kb.copy()
    if kb_search.strip():
        mask = (
            filtered["topic"].str.contains(kb_search, case=False, na=False)
            | filtered["description"].str.contains(
                kb_search, case=False, na=False
            )
        )
        filtered = filtered[mask]

    if kb_category != "All":
        filtered = filtered[filtered["category"] == kb_category]

    st.metric("Matching catalogue records", len(filtered))
    st.dataframe(filtered, use_container_width=True, hide_index=True)


# =============================================================================
# SYSTEM TAB
# =============================================================================

with system_tab:
    st.subheader("⚙️ System Diagnostics")

    api_key, model, base_url = get_ai_settings()

    d1, d2, d3 = st.columns(3)
    d1.metric("AI provider", "Configured" if api_key else "Not configured")
    d2.metric("AI model", model)
    d3.metric("Live sources", len(research_sources))

    st.write("### Architecture")
    st.markdown("""
    **Browser UI → Streamlit → Research connectors → Optional AI engine → SQLite**

    The application intentionally avoids desktop GUI dependencies such as
    Tkinter. This is important for cloud deployment because Streamlit apps run
    in a Linux server environment rather than a normal Windows desktop session.

    **Live connectors**
    - GitHub repository search
    - Stack Overflow developer search
    - Crossref scholarly metadata
    - OpenAlex scholarly metadata
    - Hacker News technology stories
    - Wikipedia reference search
    - PyPI package metadata

    **Persistent application data**
    - Conversation history
    - Research cache schema
    - User feedback schema
    - Local technical knowledge catalogue
    """)

    st.write("### Export session")
    export_payload = {
        "session_id": st.session_state.session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": st.session_state.messages,
        "last_sources": st.session_state.last_sources,
    }

    st.download_button(
        "⬇️ Export session JSON",
        data=json.dumps(export_payload, indent=2),
        file_name=f"session_{st.session_state.session_id}.json",
        mime="application/json",
    )

    st.write("### Feedback")
    rating = st.slider("Rate this session", 1, 5, 5)
    comment = st.text_area("Optional comment")
    if st.button("Save feedback"):
        conn = db()
        conn.execute(
            "INSERT INTO feedback(session_id, rating, comment, created_at) "
            "VALUES (?, ?, ?, ?)",
            (
                st.session_state.session_id,
                rating,
                comment,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        st.success("Feedback saved.")


# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.caption(
    "Owino Brian Enterprise Technical Suite • Web-safe architecture • "
    "Live public-data retrieval • Optional AI reasoning • SQLite persistence"
)
