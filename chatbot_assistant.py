"""
OBO CHATBOT
Developer: Owino Brian Otieno

A browser-based Streamlit assistant for technology, computer science,
programming, artificial intelligence, cloud, DevOps, cybersecurity, data
analysis and academic research.

Design principles
------------------
1.  Zero-hallucination answers. Every response the chatbot gives is either
    pulled directly from the curated internal knowledge base, or, when live
    search is switched on, clearly attributed to a named external source.
    The assistant never invents facts, citations, statistics or code
    behaviour that is not backed by one of those two sources.
2.  Honest scope. If a question falls outside the knowledge base and live
    search (when enabled) returns nothing relevant, the chatbot says so
    plainly and points the user to OBO Human Agents instead of guessing.
3.  Browser-native GUI. Everything runs through Streamlit; there is no
    Tkinter or desktop GUI dependency, which keeps it deployable to any
    standard Streamlit host.
4.  No required API keys. The base assistant, chat history and knowledge
    base all work without any secrets configured. Live search only touches
    public, unauthenticated endpoints by default; a real Google result set
    can be added on top of that if the deployer sets an optional API key
    (see the Google Custom Search section below), but nothing breaks
    without one.

This file requires Streamlit 1.43 or later. Two features used here landed
together in that release: st.chat_input(accept_file=...), which gives the
message box its own native attachment control, and st.context.timezone_offset,
which is how the greeting is timed to the visitor's own local clock instead
of the server's.
"""

from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st


# =============================================================================
# APPLICATION CONSTANTS
# =============================================================================

APP_TITLE = "OBO Chatbot"
DEVELOPER = "Owino Brian Otieno"
HUMAN_AGENTS_LABEL = "OBO Human Agents"
DEVELOPER_SPONSOR_URL = "https://github.com/sponsors/owino-brian"
DEVELOPER_LINKEDIN_URL = "https://www.linkedin.com/in/owinobrian/"
DB_PATH = Path("obo_chatbot_history.db")
MAX_UPLOAD_MB = 50
MAX_HISTORY_ITEMS = 40
LIVE_TIMEOUT_SECONDS = 10
MIN_MATCH_SCORE = 2  # below this, a knowledge-base match is not trusted


# =============================================================================
# PAGE CONFIGURATION AND STYLE
# =============================================================================

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp { background: #f7f7f8; }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #e5e7eb;
        }

        .obo-brand { padding: 10px 4px 18px 4px; }
        .obo-brand-title { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; }
        .obo-brand-subtitle { color: #6b7280; font-size: 0.78rem; margin-top: 2px; }

        .obo-hero { max-width: 860px; margin: 6vh auto 2rem auto; text-align: center; }
        .obo-hero h1 { font-size: 2.3rem; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
        .obo-hero p { color: #6b7280; font-size: 1rem; }
        .obo-hero .obo-dev { color: #9ca3af; font-size: 0.78rem; margin-top: 0.7rem; }

        .obo-card {
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 15px;
            background: white;
            min-height: 108px;
        }
        .obo-card-title { font-weight: 650; margin-bottom: 4px; }
        .obo-card-text { color: #6b7280; font-size: 0.86rem; line-height: 1.45; }

        .obo-footer { text-align: center; color: #9ca3af; font-size: 0.72rem; padding: 26px 0 8px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# LOCAL TIME (used for the greeting)
# =============================================================================

def visitor_local_time() -> datetime:
    """Best-effort local time of the person using the app, from the browser's
    own UTC offset via st.context.timezone_offset. Falls back to the
    server's local time if that is unavailable for any reason (older
    Streamlit version, or the value not being reported yet on this run)."""
    try:
        offset_minutes = st.context.timezone_offset
        if offset_minutes is not None:
            tz = timezone(-timedelta(minutes=offset_minutes))
            return datetime.now(timezone.utc).astimezone(tz)
    except Exception:
        pass
    return datetime.now()


def time_of_day_greeting(hour: int) -> str:
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    if 17 <= hour < 22:
        return "Good evening"
    return "Hello"


def opening_greeting() -> str:
    hour = visitor_local_time().hour
    return f"{time_of_day_greeting(hour)}! I am {APP_TITLE}. How may I help you?"


# =============================================================================
# DATABASE LAYER (chat history)
# =============================================================================

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialise_database() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            question TEXT NOT NULL,
            created_at TEXT NOT NULL,
            emailed INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # A previous version of this app created a conversation row the moment
    # "New chat" was clicked, before any message existed, which is why the
    # sidebar could fill up with empty "New conversation" entries. This
    # clears out any such leftover rows from an existing database file.
    conn.execute(
        "DELETE FROM conversations WHERE id NOT IN (SELECT DISTINCT conversation_id FROM messages)"
    )
    conn.commit()
    conn.close()


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_conversation_id() -> str:
    """Generate a fresh conversation id without touching the database. A row
    is only written once the first real message is sent (see
    ensure_conversation_row), which is what keeps the sidebar history free
    of empty 'New conversation' placeholders."""
    return str(uuid.uuid4())


def ensure_conversation_row(conversation_id: str, title_seed: str) -> None:
    conn = get_connection()
    exists = conn.execute(
        "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    if exists is None:
        stamp = now_string()
        title = re.sub(r"\s+", " ", title_seed).strip()[:58] or "New conversation"
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conversation_id, title, stamp, stamp),
        )
        conn.commit()
    conn.close()


def load_conversation(conversation_id: str) -> list[dict[str, str]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
    ).fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def save_message(conversation_id: str, role: str, content: str) -> None:
    stamp = now_string()
    conn = get_connection()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, stamp),
    )
    conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (stamp, conversation_id))
    conn.commit()
    conn.close()


def recent_conversations(limit: int = MAX_HISTORY_ITEMS) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, title, updated_at FROM conversations c
        WHERE EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = c.id)
        ORDER BY updated_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def log_escalation(conversation_id: str, question: str) -> int:
    stamp = now_string()
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO escalations (conversation_id, question, created_at, emailed) VALUES (?, ?, ?, 0)",
        (conversation_id, question, stamp),
    )
    conn.commit()
    escalation_id = cursor.lastrowid
    conn.close()
    return escalation_id


def mark_escalation_emailed(escalation_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE escalations SET emailed = 1 WHERE id = ?", (escalation_id,))
    conn.commit()
    conn.close()


def send_to_human_agents(question: str, conversation_id: str) -> bool:
    """Logs the escalated question locally (so nothing is lost even if
    email delivery is not configured), then attempts to email it to
    HUMAN_AGENT_EMAIL. Returns True only if the email genuinely sent.
    Delivery needs SMTP_HOST, SMTP_USERNAME and SMTP_PASSWORD set as
    Streamlit secrets or environment variables (SMTP_PORT defaults to 587);
    without them this still records the escalation, it just does not
    email it, and the caller is told the truth about which happened."""
    escalation_id = log_escalation(conversation_id, question)

    smtp_host = st.secrets.get("SMTP_HOST", os.getenv("SMTP_HOST", ""))
    smtp_port = st.secrets.get("SMTP_PORT", os.getenv("SMTP_PORT", "587"))
    smtp_username = st.secrets.get("SMTP_USERNAME", os.getenv("SMTP_USERNAME", ""))
    smtp_password = st.secrets.get("SMTP_PASSWORD", os.getenv("SMTP_PASSWORD", ""))

    if not (smtp_host and smtp_username and smtp_password):
        return False

    body = (
        f"A visitor question was escalated from {APP_TITLE}.\n\n"
        f"Conversation reference: {conversation_id}\n"
        f"Time: {now_string()}\n\n"
        f"Question:\n{question}\n\n"
        "No further visitor contact details were collected by the app."
    )
    message = EmailMessage()
    message["Subject"] = f"{APP_TITLE}: question escalated to human agents"
    message["From"] = smtp_username
    message["To"] = HUMAN_AGENT_EMAIL
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message)
        mark_escalation_emailed(escalation_id)
        return True
    except Exception:
        return False


initialise_database()


# =============================================================================
# SESSION STATE
# =============================================================================

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = new_conversation_id()

if "messages" not in st.session_state:
    st.session_state.messages = load_conversation(st.session_state.conversation_id)

if "live_search_enabled" not in st.session_state:
    st.session_state.live_search_enabled = False

if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = None

if "uploaded_name" not in st.session_state:
    st.session_state.uploaded_name = None

if "pending_escalation" not in st.session_state:
    st.session_state.pending_escalation = None

if "last_evidence" not in st.session_state:
    st.session_state.last_evidence = []


# =============================================================================
# KNOWLEDGE BASE
#
# Every entry below is a plain factual reference statement, written to be
# accurate on its own without needing an external model to "fill in the
# gaps". This is what makes the assistant's answers trustworthy: if a topic
# is not represented here (and live search is off, or also comes up empty),
# the assistant redirects to OBO Human Agents instead of guessing.
#
# Each record: (topic, category, keywords, answer)
# =============================================================================

_KB_RECORDS: list[tuple[str, str, tuple[str, ...], str]] = [
    # ---- Programming languages -------------------------------------------------
    ("Python", "Programming Languages", ("python", "pip", "virtualenv", "venv"),
     "Python is a general-purpose, interpreted programming language used in web development, "
     "automation, data analysis, scientific computing and artificial intelligence. Dependencies "
     "are normally isolated in a virtual environment, and packages are installed with pip."),
    ("JavaScript", "Programming Languages", ("javascript", "js", "ecmascript"),
     "JavaScript is the primary scripting language of web browsers and, through runtimes such as "
     "Node.js, is also used on servers. It supports event-driven, asynchronous, object-oriented "
     "and functional programming styles."),
    ("TypeScript", "Programming Languages", ("typescript",),
     "TypeScript adds static typing on top of JavaScript. Interfaces, type annotations and "
     "compiler checks catch many mistakes before the code ever runs, which helps on larger "
     "codebases and teams."),
    ("Java", "Programming Languages", ("java programming", "java language", " java "),
     "Java is a statically typed, object-oriented language that runs on the Java Virtual Machine. "
     "It is widely used in enterprise backend systems, Android development and large-scale "
     "distributed applications."),
    ("C", "Programming Languages", ("c programming", "c language"),
     "C is a compiled, low-level systems language. It gives direct control over memory and "
     "hardware, which is why it underlies operating systems, embedded software and many "
     "performance-critical libraries."),
    ("C++", "Programming Languages", ("c++", "cpp"),
     "C++ extends C with object-oriented, generic and (in modern standards) some functional "
     "programming features, while keeping close-to-hardware performance."),
    ("C#", "Programming Languages", ("c#", "c sharp", "dotnet", ".net"),
     "C# is a statically typed language in the .NET ecosystem, commonly used for enterprise "
     "applications, desktop software, web backends (ASP.NET) and game development (Unity)."),
    ("Go", "Programming Languages", ("golang", "go programming", "go language"),
     "Go is a compiled language designed for simplicity, fast builds and built-in concurrency "
     "primitives (goroutines and channels). It is popular for cloud infrastructure and networked "
     "services."),
    ("Rust", "Programming Languages", ("rust programming", "rust language"),
     "Rust is a compiled systems language that enforces memory safety at compile time through its "
     "ownership and borrowing rules, without needing a garbage collector."),
    ("PHP", "Programming Languages", ("php",),
     "PHP is a server-side scripting language built for the web. It powers a large share of "
     "existing web applications and content management systems such as WordPress."),
    ("Ruby", "Programming Languages", ("ruby programming", "ruby language"),
     "Ruby is a dynamic, object-oriented language known for readable syntax. It is closely "
     "associated with the Ruby on Rails web framework."),
    ("Kotlin", "Programming Languages", ("kotlin",),
     "Kotlin is a statically typed language that runs on the JVM and is the primary recommended "
     "language for modern Android development."),
    ("Swift", "Programming Languages", ("swift programming", "swift language"),
     "Swift is Apple's modern language for iOS, macOS, watchOS and tvOS development, designed to "
     "replace Objective-C with safer, more concise syntax."),
    ("Python virtual environments", "Programming Languages", ("virtual environment", "venv module"),
     "A Python virtual environment creates an isolated set of installed packages for a single "
     "project, preventing dependency conflicts between different projects on the same machine."),
    ("Python decorators", "Programming Languages", ("decorator", "decorators", "@property"),
     "A decorator wraps a function or class to add or modify behaviour without changing its "
     "original source code, commonly used for logging, timing, caching and access control."),
    ("Python generators", "Programming Languages", ("generator", "generators", "yield keyword"),
     "A generator produces values one at a time using the yield keyword, which keeps memory usage "
     "low when working through large or unbounded sequences."),
    ("Object-oriented programming", "Programming Languages", ("object oriented programming", "oop"),
     "Object-oriented programming organises code around objects that combine data and behaviour. "
     "Its core ideas are encapsulation, abstraction, inheritance and polymorphism."),
    ("Functional programming", "Programming Languages", ("functional programming",),
     "Functional programming treats computation as the evaluation of functions, favouring "
     "immutability and function composition over changing shared state."),
    ("Recursion", "Programming Languages", ("recursion", "recursive function"),
     "Recursion solves a problem by having a function call itself on a smaller version of the "
     "same problem. A correct recursive function needs a base case and a step that moves toward it."),

    # ---- Web development ---------------------------------------------------
    ("HTML", "Web Development", ("html", "html5"),
     "HTML structures the content of a web page. Semantic elements such as header, nav, main, "
     "section, article and footer make a page's structure clearer to both browsers and assistive "
     "technology."),
    ("CSS", "Web Development", ("css", "stylesheet", "responsive design"),
     "CSS controls the visual presentation of HTML content. Flexbox, Grid, media queries and "
     "custom properties are the main tools for building layouts that adapt across screen sizes."),
    ("React", "Web Development", ("react", "reactjs"),
     "React is a JavaScript library for building user interfaces out of reusable components. "
     "Application state drives what is rendered, and changes to that state trigger re-renders."),
    ("Next.js", "Web Development", ("next.js", "nextjs"),
     "Next.js is a React framework that adds routing, server-side rendering, static generation "
     "and other application-level concerns on top of React."),
    ("Node.js", "Web Development", ("node.js", "nodejs"),
     "Node.js runs JavaScript outside the browser, which makes it possible to build servers, "
     "APIs, command-line tools and real-time applications in JavaScript."),
    ("Django", "Web Development", ("django",),
     "Django is a full-featured Python web framework that includes routing, an ORM, templating "
     "and authentication out of the box, following a batteries-included philosophy."),
    ("Flask", "Web Development", ("flask",),
     "Flask is a lightweight Python web framework with a small core. Additional capabilities are "
     "added through extensions rather than being built in by default."),
    ("FastAPI", "Web Development", ("fastapi",),
     "FastAPI is a Python framework for building HTTP APIs. It uses Python type hints to validate "
     "requests and automatically generates interactive OpenAPI documentation."),
    ("REST API", "Web Development", ("rest api", "restful api", "rest"),
     "A REST API exposes resources through HTTP methods and a consistent URL structure. Good "
     "design uses clear resource names, sensible status codes and predictable error responses."),
    ("GraphQL", "Web Development", ("graphql",),
     "GraphQL lets a client request exactly the fields it needs through a single typed schema, "
     "which can reduce over-fetching compared with fixed REST endpoints."),
    ("HTTP methods", "Web Development", ("http methods", "get post put delete", "http verbs"),
     "The common HTTP methods are GET (retrieve), POST (create), PUT/PATCH (update) and DELETE "
     "(remove). Each has a defined meaning that well-behaved APIs are expected to follow."),
    ("HTTP status codes", "Web Development", ("http status code", "status codes", "404", "500"),
     "HTTP status codes report the outcome of a request: 2xx for success, 3xx for redirection, "
     "4xx for client errors and 5xx for server errors."),
    ("WebSockets", "Web Development", ("websocket", "websockets"),
     "WebSockets keep a persistent, two-way connection open between client and server, which "
     "suits real-time features such as chat or live updates better than repeated HTTP requests."),
    ("Webhooks", "Web Development", ("webhook", "webhooks"),
     "A webhook is an HTTP callback: one system sends a request to a URL you provide whenever a "
     "specific event happens, instead of you having to poll for updates."),

    # ---- Databases ----------------------------------------------------------
    ("SQL", "Databases", ("sql", "select statement", "database query"),
     "SQL is the standard language for querying and managing relational data. Core concepts "
     "include SELECT, JOIN, GROUP BY, indexes, constraints and transactions."),
    ("PostgreSQL", "Databases", ("postgresql", "postgres"),
     "PostgreSQL is an open-source relational database known for strong transaction guarantees, "
     "rich indexing options, extensibility and advanced data types such as JSONB."),
    ("MySQL", "Databases", ("mysql",),
     "MySQL is a widely used open-source relational database, common in web application stacks, "
     "with performance that depends heavily on schema design and indexing."),
    ("MongoDB", "Databases", ("mongodb", "mongo"),
     "MongoDB is a document-oriented database that stores data as flexible, JSON-like documents "
     "rather than fixed relational tables."),
    ("Redis", "Databases", ("redis",),
     "Redis is an in-memory data store commonly used for caching, session storage, rate limiting "
     "and lightweight message queues, valued for very low latency."),
    ("NoSQL", "Databases", ("nosql", "no sql"),
     "NoSQL databases (document, key-value, wide-column or graph) trade some relational "
     "guarantees for flexible schemas or horizontal scalability, and fit workloads where a fixed "
     "table structure is not the best match."),
    ("ORM", "Databases", ("orm", "object relational mapping"),
     "An object-relational mapper lets application code work with objects instead of writing raw "
     "SQL directly, at the cost of an extra abstraction layer to understand and tune."),
    ("Database transactions", "Databases", ("transaction", "database transaction", "acid"),
     "A database transaction groups operations so they succeed or fail together. The ACID "
     "properties (atomicity, consistency, isolation, durability) describe the guarantees a "
     "well-implemented transactional system aims to provide."),
    ("Database normalisation", "Databases", ("normalisation", "normalization"),
     "Normalisation organises relational tables to reduce redundant data and avoid update "
     "anomalies. The right level of normalisation depends on the workload, not a fixed rule."),
    ("Database indexing", "Databases", ("database index", "indexes", "indexing"),
     "An index gives the database an alternate, faster path to find rows, at the cost of extra "
     "storage and slightly slower writes. Indexes should match the queries actually being run."),
    ("Data warehouse", "Databases", ("data warehouse",),
     "A data warehouse is structured for analytical queries and reporting rather than day-to-day "
     "transactional workloads, often using dimensional modelling."),
    ("Data lake", "Databases", ("data lake", "data lakes"),
     "A data lake stores data in a relatively raw form for later processing. Without good "
     "governance and metadata, a data lake can become hard to use, sometimes called a data swamp."),

    # ---- Cloud and DevOps -----------------------------------------------------
    ("Cloud computing", "Cloud & DevOps", ("cloud computing", "cloud technology"),
     "Cloud computing provides on-demand computing resources over a network. Key design concerns "
     "are elasticity, reliability, security, cost and how tightly you couple to one vendor."),
    ("AWS", "Cloud & DevOps", ("aws", "amazon web services", "ec2", "s3"),
     "Amazon Web Services is a cloud platform offering compute (EC2), storage (S3), databases, "
     "networking and machine-learning services, among many others."),
    ("Microsoft Azure", "Cloud & DevOps", ("azure", "microsoft azure"),
     "Microsoft Azure is a cloud platform offering compute, identity, databases, networking and "
     "AI services, commonly chosen where an organisation already relies on Microsoft tooling."),
    ("Google Cloud", "Cloud & DevOps", ("google cloud", "gcp"),
     "Google Cloud Platform offers compute, storage, data analytics and machine-learning services, "
     "with particular strength in big-data and AI tooling."),
    ("Docker", "Cloud & DevOps", ("docker", "container", "dockerfile"),
     "Docker packages an application with its dependencies into a container image, making "
     "behaviour more consistent across development, testing and production environments."),
    ("Kubernetes", "Cloud & DevOps", ("kubernetes", "k8s"),
     "Kubernetes orchestrates containerised applications: scheduling them onto machines, scaling "
     "them, handling rolling updates, and restarting failed instances to match a desired state."),
    ("Terraform", "Cloud & DevOps", ("terraform", "infrastructure as code"),
     "Terraform is an infrastructure-as-code tool. Infrastructure is described in configuration "
     "files, which lets changes be reviewed, versioned and applied repeatably."),
    ("CI/CD", "Cloud & DevOps", ("ci/cd", "continuous integration", "continuous delivery"),
     "Continuous integration automatically builds and tests code changes; continuous delivery or "
     "deployment automates getting those changes safely into staging or production."),
    ("Linux", "Cloud & DevOps", ("linux", "bash", "linux command line"),
     "Linux is the operating-system family behind most servers and cloud infrastructure. Its "
     "command-line tools are central to server administration, scripting and automation."),
    ("Serverless", "Cloud & DevOps", ("serverless", "serverless computing"),
     "Serverless computing runs code without the developer managing servers directly. It can "
     "simplify scaling, but cold starts, execution time limits and cost at scale need attention."),
    ("Load balancing", "Cloud & DevOps", ("load balancer", "load balancing"),
     "A load balancer distributes incoming requests across multiple servers, improving "
     "availability and throughput, provided health checks and session handling are configured."),
    ("Caching", "Cloud & DevOps", ("cache", "caching"),
     "Caching stores frequently needed data closer to where it is used. The hard part is usually "
     "invalidation: deciding when cached data is stale and needs refreshing."),
    ("CDN", "Cloud & DevOps", ("cdn", "content delivery network"),
     "A content delivery network serves content from locations closer to the user, reducing "
     "latency for static assets such as images, scripts and video."),
    ("Observability", "Cloud & DevOps", ("observability", "monitoring", "logging", "tracing"),
     "Observability combines logs, metrics and traces so a team can understand what a running "
     "system is actually doing, not just whether it is up or down."),
    ("Microservices", "Cloud & DevOps", ("microservices", "microservice architecture"),
     "A microservices architecture splits an application into independently deployable services. "
     "It can improve team autonomy and scaling, at the cost of distributed-systems complexity."),
    ("Monolith", "Cloud & DevOps", ("monolith", "monolithic architecture"),
     "A monolithic application ships its components as a single deployable unit. A well-structured "
     "monolith is often simpler to build and operate than a premature set of microservices."),
    ("DevOps", "Cloud & DevOps", ("devops",),
     "DevOps combines development and operations practices, using automation, testing and "
     "monitoring to make software delivery faster and more reliable."),

    # ---- Cybersecurity ---------------------------------------------------------
    ("Encryption", "Cybersecurity", ("encryption", "cryptography", "cipher"),
     "Encryption converts readable data into protected ciphertext using an algorithm and a key. "
     "Its security depends on correct key management as much as on the algorithm itself."),
    ("TLS / HTTPS", "Cybersecurity", ("tls", "https", "transport layer security"),
     "TLS protects data in transit against eavesdropping and tampering. HTTPS is simply HTTP "
     "carried over a TLS connection."),
    ("OAuth", "Cybersecurity", ("oauth", "oauth 2", "oauth 2.0"),
     "OAuth 2.0 is an authorisation framework that lets an application access a resource on a "
     "user's behalf without ever seeing that user's actual password."),
    ("JWT", "Cybersecurity", ("jwt", "json web token"),
     "A JSON Web Token is a compact, signed way to carry claims between parties. Applications "
     "still need to check expiry, signature and scope correctly to use it securely."),
    ("Zero trust", "Cybersecurity", ("zero trust", "zero-trust"),
     "A zero-trust security model checks every request explicitly rather than trusting it because "
     "it came from inside the network, based on identity, device state and policy."),
    ("IAM", "Cybersecurity", ("iam", "identity access management"),
     "Identity and access management controls who or what can access a resource, typically "
     "through roles, policies and the principle of least privilege."),
    ("Firewalls", "Cybersecurity", ("firewall", "firewalls"),
     "A firewall filters network traffic according to defined rules, forming one layer in a "
     "broader, defence-in-depth security design."),
    ("Secure coding", "Cybersecurity", ("secure coding", "secure software"),
     "Secure coding means validating untrusted input, handling errors without leaking internal "
     "detail, using proven cryptography, and never trusting data from outside the application."),
    ("Threat modelling", "Cybersecurity", ("threat modelling", "threat modeling"),
     "Threat modelling identifies a system's assets, trust boundaries and likely threats before or "
     "during design, so mitigations can be built in rather than bolted on afterwards."),
    ("Penetration testing", "Cybersecurity", ("penetration testing", "pentest"),
     "Penetration testing is authorised, scoped testing of a system's security controls to find "
     "exploitable weaknesses before an attacker does."),
    ("OWASP Top 10", "Cybersecurity", ("owasp", "owasp top 10"),
     "The OWASP Top 10 is a widely referenced list of common and serious web application security "
     "risks, used as a baseline checklist by many security teams."),
    ("SQL injection", "Cybersecurity", ("sql injection", "sqli"),
     "SQL injection happens when untrusted input is allowed to change the structure of a database "
     "query. Parameterised queries are the standard defence."),
    ("Multi-factor authentication", "Cybersecurity", ("mfa", "two factor authentication", "2fa"),
     "Multi-factor authentication requires two or more independent proofs of identity, which "
     "significantly reduces the risk from a single stolen password."),
    ("Incident response", "Cybersecurity", ("incident response", "security incident"),
     "Incident response is the coordinated process of detecting, containing, investigating and "
     "recovering from a security event, followed by documenting lessons learned."),

    # ---- Artificial intelligence and machine learning -------------------------
    ("Machine learning", "Artificial Intelligence", ("machine learning", "ml model"),
     "Machine learning uses data to learn patterns that support prediction, classification or "
     "decision-making. A responsible workflow covers data preparation, training, validation and "
     "ongoing monitoring after deployment."),
    ("Deep learning", "Artificial Intelligence", ("deep learning", "neural network", "neural networks"),
     "Deep learning uses multi-layer neural networks to learn representations directly from data, "
     "and underlies most modern computer vision and language systems."),
    ("Generative AI", "Artificial Intelligence", ("generative ai", "gen ai"),
     "Generative AI systems produce new content, such as text, code or images. Good applications "
     "pair clear instructions and relevant context with human review wherever mistakes matter."),
    ("Large language models", "Artificial Intelligence", ("llm", "large language model", "language model"),
     "Large language models learn statistical patterns in text and can generate, summarise, "
     "translate or classify language. Fluent output is not the same as correct output, so claims "
     "should still be checked."),
    ("Retrieval-augmented generation", "Artificial Intelligence", ("rag", "retrieval augmented generation"),
     "Retrieval-augmented generation retrieves relevant documents and supplies them as context so "
     "a model's answer is grounded in that material rather than relying purely on what it "
     "memorised during training."),
    ("AI agents", "Artificial Intelligence", ("ai agent", "ai agents", "agentic ai"),
     "AI agents pursue a task across multiple steps, often using external tools. Reliable agents "
     "need constrained tools, input validation, error handling and a clear stopping condition."),
    ("Embeddings", "Artificial Intelligence", ("embedding", "embeddings"),
     "Embeddings represent items such as text as numerical vectors, so that similar meanings end "
     "up close together and can be found through vector similarity."),
    ("Vector databases", "Artificial Intelligence", ("vector database", "vector store"),
     "A vector database stores and searches embeddings efficiently, and is a common building block "
     "in semantic search and retrieval-augmented generation systems."),
    ("Prompt engineering", "Artificial Intelligence", ("prompt engineering", "prompt design"),
     "Prompt engineering is the deliberate design of instructions, context and examples given to "
     "an AI model, with the goal of producing more reliable, on-target output."),
    ("Prompt injection", "Artificial Intelligence", ("prompt injection",),
     "Prompt injection is an attempt to manipulate an AI system through instructions hidden in "
     "untrusted content. Systems defend against it by separating trusted instructions from "
     "untrusted input and constraining what tools a model can call."),
    ("AI hallucination", "Artificial Intelligence", ("ai hallucination", "hallucinations", "model hallucination"),
     "An AI hallucination is a confident-sounding but unsupported or incorrect output. Grounding "
     "answers in retrieved evidence and verifying claims against sources reduces this risk."),
    ("Computer vision", "Artificial Intelligence", ("computer vision", "image recognition", "object detection"),
     "Computer vision applies computational methods to images and video, covering tasks such as "
     "classification, object detection, segmentation and optical character recognition."),
    ("Natural language processing", "Artificial Intelligence", ("nlp", "natural language processing"),
     "Natural language processing covers computational methods for analysing and generating human "
     "language, including classification, extraction, translation and summarisation."),
    ("MLOps", "Artificial Intelligence", ("mlops",),
     "MLOps applies software-engineering and operations discipline to machine learning: data "
     "pipelines, experiment tracking, model versioning, deployment and monitoring."),
    ("Transformers", "Artificial Intelligence", ("transformer model", "transformers", "attention mechanism"),
     "Transformer architectures use an attention mechanism to weigh relationships between elements "
     "in a sequence, and are the basis of most modern large language models."),
    ("Fine-tuning", "Artificial Intelligence", ("fine tuning", "fine-tuning", "finetuning"),
     "Fine-tuning takes a model already trained on broad data and trains it further on a narrower, "
     "task-specific dataset."),
    ("Transfer learning", "Artificial Intelligence", ("transfer learning",),
     "Transfer learning reuses knowledge a model learned on one task or dataset to help with a "
     "different but related task, usually needing far less new data than training from scratch."),
    ("Reinforcement learning", "Artificial Intelligence", ("reinforcement learning",),
     "Reinforcement learning trains an agent to choose actions in an environment based on rewards, "
     "gradually learning a policy that maximises long-term reward."),
    ("Overfitting", "Artificial Intelligence", ("overfitting", "underfitting"),
     "Overfitting happens when a model learns patterns specific to its training data that do not "
     "generalise. Validation data, regularisation and appropriately sized models help control it."),
    ("AI bias", "Artificial Intelligence", ("ai bias", "algorithmic bias"),
     "AI bias can come from the training data, labels, objectives or deployment context. It should "
     "be checked for explicitly by evaluating performance across the groups that matter."),
    ("Responsible AI", "Artificial Intelligence", ("responsible ai", "ethical ai"),
     "Responsible AI practice weighs reliability, fairness, transparency, privacy, safety and "
     "appropriate human oversight, not just raw model performance."),

    # ---- Computer science fundamentals -----------------------------------------
    ("Algorithms", "Computer Science", ("algorithm", "algorithms"),
     "An algorithm is a defined, step-by-step procedure for solving a problem. It is normally "
     "judged on correctness, time complexity, space complexity and how well its assumptions match "
     "the real input."),
    ("Big O notation", "Computer Science", ("big o", "time complexity", "space complexity"),
     "Big O notation describes how an algorithm's resource use grows as input size increases. A "
     "linear scan is O(n); binary search on sorted data is O(log n) under its usual assumptions."),
    ("Data structures", "Computer Science", ("data structures", "array", "linked list"),
     "Data structures organise information for efficient access and change. Arrays, linked lists, "
     "stacks, queues, hash tables, trees and graphs each trade off speed and memory differently."),
    ("Hash tables", "Computer Science", ("hash table", "hashmap", "dictionary data structure"),
     "A hash table maps keys to values using a hash function, giving average-case near-constant "
     "time lookups, though collisions and load factor affect real performance."),
    ("Trees", "Computer Science", ("binary tree", "tree data structure", "bst"),
     "Trees model hierarchical relationships. Binary search trees support ordered operations, and "
     "balanced variants keep operations close to logarithmic time."),
    ("Graphs", "Computer Science", ("graph data structure", "graph algorithm"),
     "Graphs represent relationships between nodes through edges. Breadth-first search, "
     "depth-first search and shortest-path algorithms are standard tools for working with them."),
    ("Sorting algorithms", "Computer Science", ("sorting algorithm", "quicksort", "merge sort"),
     "Sorting algorithms differ in time complexity, memory use and stability. Merge sort has "
     "predictable O(n log n) time; quicksort is fast on average but has a worse simple worst case."),
    ("Binary search", "Computer Science", ("binary search",),
     "Binary search repeatedly halves the search space in sorted data, giving O(log n) time under "
     "its standard assumptions."),
    ("Operating systems", "Computer Science", ("operating system", "operating systems"),
     "An operating system manages hardware resources and exposes services to applications, "
     "covering processes, threads, memory management, filesystems and device access."),
    ("Computer networks", "Computer Science", ("computer network", "networking", "tcp/ip"),
     "Computer networking lets systems communicate through protocols, addressing and routing. "
     "TCP/IP, DNS, HTTP and TLS are foundational concepts for building networked applications."),
    ("Distributed systems", "Computer Science", ("distributed system", "distributed systems"),
     "Distributed systems coordinate components across multiple machines, and must account for "
     "network delay, partial failure, concurrency and consistency trade-offs."),
    ("Computer architecture", "Computer Science", ("computer architecture", "cpu", "cache memory"),
     "Computer architecture describes how hardware implements computation: CPUs, caches, memory "
     "hierarchy, buses and instruction sets all influence real-world performance."),
    ("Compilers", "Computer Science", ("compiler", "compilers"),
     "A compiler translates source code into another form, typically through lexical analysis, "
     "parsing, semantic checking, optimisation and code generation."),
    ("Concurrency", "Computer Science", ("concurrency", "threading", "threads"),
     "Concurrency deals with tasks whose execution overlaps in time. Correctness depends on "
     "carefully handling shared state, locking and synchronisation."),

    # ---- Software engineering practice -----------------------------------------
    ("Software requirements", "Software Engineering", ("software requirements", "requirements engineering"),
     "Requirements define what a system must do (functional requirements) and the qualities it "
     "must have, such as performance or security (non-functional requirements)."),
    ("Design patterns", "Software Engineering", ("design pattern", "design patterns"),
     "Design patterns are named, reusable solutions to recurring software design problems, such as "
     "the observer, factory or strategy patterns."),
    ("MVC", "Software Engineering", ("mvc", "model view controller"),
     "The Model-View-Controller pattern separates data and business logic (model), presentation "
     "(view) and request handling (controller) into distinct, more maintainable layers."),
    ("Clean architecture", "Software Engineering", ("clean architecture", "hexagonal architecture"),
     "Clean and hexagonal architecture styles keep core business logic independent of frameworks, "
     "databases and other external infrastructure, so those details can change without rewriting "
     "the core logic."),
    ("Technical debt", "Software Engineering", ("technical debt", "tech debt"),
     "Technical debt is the future cost created by a shortcut or compromise made now. Like "
     "financial debt, it accrues interest the longer it is left unaddressed."),
    ("Code review", "Software Engineering", ("code review", "pull request review"),
     "Code review checks a change for correctness, readability, security and test coverage before "
     "it is merged, and is one of the most effective ways to catch defects early."),
    ("Refactoring", "Software Engineering", ("refactoring", "refactor code"),
     "Refactoring restructures existing code without changing its external behaviour, usually to "
     "make it easier to understand or extend later."),
    ("Unit testing", "Software Engineering", ("unit test", "unit testing", "pytest"),
     "Unit tests check a small piece of code in isolation. Good unit tests are focused, repeatable "
     "and explicit about the behaviour they expect."),
    ("Integration testing", "Software Engineering", ("integration testing", "integration test"),
     "Integration tests check that multiple components, such as an application and a database, "
     "work correctly together."),
    ("Agile and Scrum", "Software Engineering", ("agile", "scrum", "sprint"),
     "Agile approaches favour iterative delivery and regular feedback over large up-front plans. "
     "Scrum is one specific framework, with defined roles, sprints and ceremonies."),
    ("System design", "Software Engineering", ("system design", "software architecture"),
     "System design starts from requirements and constraints, then works through components, "
     "data flow, scalability, reliability, security and operational concerns."),

    # ---- Data analysis and tooling ----------------------------------------------
    ("Data cleaning", "Data Analysis", ("data cleaning", "data cleansing"),
     "Data cleaning identifies and handles missing values, duplicates, inconsistent formats and "
     "invalid records before any analysis is trusted."),
    ("Data visualisation", "Data Analysis", ("data visualization", "data visualisation", "charts"),
     "Data visualisation communicates patterns in data through an appropriate chart type. The "
     "right chart depends on the analytical question, not just what looks impressive."),
    ("Pandas", "Data Analysis", ("pandas", "pandas dataframe"),
     "Pandas is a Python library providing the DataFrame, a labelled, two-dimensional structure "
     "widely used for cleaning, transforming and analysing tabular data."),
    ("NumPy", "Data Analysis", ("numpy", "numpy array"),
     "NumPy provides fast, memory-efficient numerical arrays and the mathematical operations that "
     "much of the Python data and scientific computing ecosystem is built on top of."),
    ("Matplotlib", "Data Analysis", ("matplotlib",),
     "Matplotlib is a Python library for producing static charts and plots, and underlies many "
     "higher-level Python visualisation tools."),
    ("Statistics basics", "Data Analysis", ("mean median mode", "standard deviation", "variance"),
     "Mean, median and mode describe central tendency; standard deviation and variance describe "
     "spread around that centre. The median is generally more robust to extreme values than the "
     "mean."),
    ("Correlation and causation", "Data Analysis", ("correlation", "causation", "causal inference"),
     "Correlation measures association between variables; it does not by itself establish that "
     "one causes the other. Causal claims need a study design built to support them."),
    ("Confidence intervals", "Data Analysis", ("confidence interval",),
     "A confidence interval expresses a range estimate produced by a statistical procedure, under "
     "the assumptions of that procedure. It is not a probability statement about a single "
     "true value."),
    ("Statistical significance", "Data Analysis", ("statistical significance", "p value", "p-value"),
     "Statistical significance describes how a result compares to a null model under stated "
     "assumptions. It is not the same thing as an effect being practically important."),
    ("Regression", "Data Analysis", ("regression", "linear regression"),
     "Regression models the relationship between variables and can support prediction or "
     "inference. Its assumptions should be checked before results are interpreted."),
    ("Classification", "Data Analysis", ("classification", "classifier"),
     "Classification assigns observations to categories. It is typically evaluated with accuracy, "
     "precision, recall and F1 score rather than accuracy alone."),
    ("Clustering", "Data Analysis", ("clustering", "k-means", "k means"),
     "Clustering groups observations by similarity without predefined labels. The number and "
     "meaning of clusters should be justified, not assumed."),
    ("Overfitting in analysis", "Data Analysis", ("cross validation", "cross-validation"),
     "Cross-validation repeatedly splits data to estimate how well a model may generalise, and "
     "should avoid leaking information between the training and evaluation portions."),

    # ---- Academic research methodology -------------------------------------------
    ("Research methodology", "Academic Research", ("research methodology", "methodology"),
     "Research methodology explains how a study collects, analyses and interprets evidence in "
     "relation to its research questions, and should be justified rather than merely described."),
    ("Literature review", "Academic Research", ("literature review", "review of literature"),
     "A literature review synthesises existing scholarship, showing agreements, disagreements and "
     "gaps, rather than simply listing sources one after another."),
    ("Systematic review", "Academic Research", ("systematic review", "systematic literature review"),
     "A systematic review uses an explicit, reproducible protocol for searching, screening, "
     "selecting and synthesising evidence, with clear inclusion and exclusion criteria."),
    ("Qualitative research", "Academic Research", ("qualitative research",),
     "Qualitative research investigates meaning, experience and context, typically through "
     "interviews, focus groups, observation or document analysis."),
    ("Quantitative research", "Academic Research", ("quantitative research",),
     "Quantitative research uses numerical data and statistical analysis to examine patterns, "
     "differences or relationships."),
    ("Mixed methods", "Academic Research", ("mixed methods", "mixed-methods"),
     "Mixed-methods research combines qualitative and quantitative approaches, and should explain "
     "why they were combined and how the findings were integrated."),
    ("Research questions", "Academic Research", ("research question", "research questions"),
     "Strong research questions are focused and answerable, aligned with the study's methodology "
     "and evidence rather than framed so broadly they cannot be properly addressed."),
    ("Hypothesis", "Academic Research", ("hypothesis", "hypotheses"),
     "A hypothesis is a testable statement about an expected relationship or outcome, framed so "
     "the evidence collected can support or challenge it."),
    ("Sampling", "Academic Research", ("sampling", "sample size"),
     "Sampling is how participants or observations are selected from a wider population. The "
     "choice between probability and non-probability sampling should match the claims being made."),
    ("Thematic analysis", "Academic Research", ("thematic analysis", "coding qualitative"),
     "Thematic analysis identifies patterns of meaning in qualitative data through "
     "familiarisation, coding, developing themes, reviewing them and interpreting significance."),
    ("Validity", "Academic Research", ("validity", "internal validity", "external validity"),
     "Validity concerns whether the evidence actually supports the interpretation being drawn from "
     "a measure or study; different forms of validity address different aspects of that question."),
    ("Reliability", "Academic Research", ("reliability", "reliable measurement"),
     "Reliability concerns consistency of a measurement under repeated, comparable conditions. A "
     "measure can be reliable without necessarily being valid."),
    ("Research ethics", "Academic Research", ("research ethics", "ethical approval"),
     "Research ethics covers informed consent where applicable, privacy, confidentiality, risk to "
     "participants and honest handling of data."),
    ("Research gap", "Academic Research", ("research gap", "gap in literature"),
     "A research gap is a genuine limitation, unanswered question or underexplored area in "
     "existing scholarship. It needs to be supported by the literature, not simply asserted."),
    ("Conceptual and theoretical frameworks", "Academic Research", ("conceptual framework", "theoretical framework"),
     "A conceptual or theoretical framework organises the concepts and relationships used to "
     "interpret a research problem, and should be applied analytically rather than just named."),
    ("Dissertation structure", "Academic Research", ("dissertation", "thesis structure"),
     "A dissertation typically moves through introduction, literature review, methodology, "
     "results, discussion and conclusion, with each chapter building on the ones before it."),
    ("Abstract", "Academic Research", ("research abstract", "abstract writing"),
     "A research abstract briefly states the problem, purpose, method, key findings and "
     "significance, and should represent the actual study rather than promise more than it delivers."),
    ("Discussion chapter", "Academic Research", ("discussion chapter",),
     "A discussion chapter interprets findings against the research questions and the existing "
     "literature; it explains what results mean rather than repeating them."),
    ("Research limitations", "Academic Research", ("research limitations", "study limitations"),
     "Stating limitations honestly identifies constraints that affect how far the findings can be "
     "generalised or applied, and strengthens rather than weakens a study's credibility."),
    ("Academic argument", "Academic Research", ("academic argument", "critical analysis"),
     "An academic argument connects claims, evidence and reasoning. Description becomes analysis "
     "once the writer explains why the evidence matters and how it relates to the question."),
    ("Plagiarism", "Academic Research", ("plagiarism", "academic integrity"),
     "Plagiarism is presenting someone else's work or ideas as your own without proper "
     "acknowledgement. Academic integrity also requires accurately representing your own "
     "contribution."),

    # ---- Referencing styles --------------------------------------------------------
    ("IEEE referencing", "Referencing", ("ieee referencing", "ieee citation"),
     "IEEE referencing typically uses numbered in-text citations in square brackets, matched to a "
     "numbered reference list, with the exact format depending on source type."),
    ("Harvard referencing", "Referencing", ("harvard referencing", "harvard style"),
     "Harvard referencing typically uses an author-date in-text citation, matched to full details "
     "in an alphabetical reference list. Universities may use slightly different Harvard variants."),
    ("APA referencing", "Referencing", ("apa referencing", "apa style"),
     "APA style uses author-date in-text citations with specific formatting rules that vary by "
     "source type, matched to a reference list at the end of the document."),
    ("Chicago referencing", "Referencing", ("chicago referencing", "chicago style"),
     "Chicago style supports two systems: notes-bibliography (footnotes or endnotes) and "
     "author-date, and the correct choice depends on the discipline and the instructions given."),
    ("DOI", "Referencing", ("doi", "digital object identifier"),
     "A DOI is a persistent identifier used to reliably link to a scholarly publication or other "
     "digital object, even if its web address changes."),
]


def _build_keyword_string(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


KNOWLEDGE_BASE: list[dict[str, Any]] = [
    {
        "topic": topic,
        "category": category,
        "keywords": tuple(_build_keyword_string(k) for k in keywords),
        "answer": answer,
    }
    for topic, category, keywords, answer in _KB_RECORDS
]

KNOWLEDGE_CATEGORIES: list[str] = sorted({entry["category"] for entry in KNOWLEDGE_BASE})

# When someone types a single broad word or short phrase rather than a
# specific question ("research", "cloud", "cybersecurity"), it is more
# useful to show them what is available in that area than to redirect them
# straight to a human, since the knowledge base clearly does cover that
# ground in general even if this exact phrasing did not score a match.
CATEGORY_ALIASES: dict[str, str] = {
    "research": "Academic Research",
    "academic research": "Academic Research",
    "academic": "Academic Research",
    "referencing": "Referencing",
    "citations": "Referencing",
    "programming": "Programming Languages",
    "coding": "Programming Languages",
    "programming languages": "Programming Languages",
    "web development": "Web Development",
    "web dev": "Web Development",
    "databases": "Databases",
    "database": "Databases",
    "cloud": "Cloud & DevOps",
    "devops": "Cloud & DevOps",
    "cloud computing": "Cloud & DevOps",
    "cybersecurity": "Cybersecurity",
    "cyber security": "Cybersecurity",
    "security": "Cybersecurity",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "machine learning": "Artificial Intelligence",
    "computer science": "Computer Science",
    "software engineering": "Software Engineering",
    "data analysis": "Data Analysis",
    "data": "Data Analysis",
    "statistics": "Data Analysis",
}


def topics_in_category(category: str) -> list[str]:
    return [entry["topic"] for entry in KNOWLEDGE_BASE if entry["category"] == category]


def category_browse_answer(question: str) -> str | None:
    q = normalise(question).rstrip("?.! ")
    if len(q.split()) > 3:
        return None
    category = CATEGORY_ALIASES.get(q)
    if not category:
        return None
    topics = topics_in_category(category)
    listed = "\n".join(f"- {topic}" for topic in topics[:12])
    return (
        f"**{category}** is one of the areas I cover. Here are some specific topics you can ask "
        f"me about directly:\n\n{listed}\n\n"
        "Ask about any of these by name and I will give you a full answer."
    )


# =============================================================================
# CONVERSATIONAL SMALL TALK
# =============================================================================

_CONVERSATION_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    (("hello", "hi", "hey", "hiya", "greetings"),
     f"Hello! I am **{APP_TITLE}**. I can help with programming, web development, databases, "
     "cloud and DevOps, cybersecurity, AI and machine learning, computer science fundamentals, "
     "data analysis and academic research and referencing. What would you like to work on?"),
    (("good morning",), f"Good morning! I am **{APP_TITLE}**. What can I help you with today?"),
    (("good afternoon",), f"Good afternoon! I am **{APP_TITLE}**. What would you like to work on?"),
    (("good evening",), f"Good evening! I am **{APP_TITLE}**. What can I help you with?"),
    (("who are you", "what are you"),
     f"I am **{APP_TITLE}**, a knowledge-base-driven assistant built by {DEVELOPER} for "
     "technology, computer science, AI and academic research questions. I only answer from a "
     "curated knowledge base (plus optional live search results), so I never guess."),
    (("what can you do", "what do you do", "capabilities"),
     "I can explain concepts, compare technologies, walk through debugging approaches, discuss "
     "software architecture and academic methodology, and work with files you upload. If a "
     f"question is outside my knowledge base, I will say so and point you to {HUMAN_AGENTS_LABEL} "
     "instead of guessing."),
    (("how are you", "how is it going"),
     "Ready to help. Send me a question, a piece of code, a research problem or a dataset."),
    (("thank you", "thanks"), "You're welcome. Send the next question whenever you are ready."),
    (("bye", "goodbye", "see you"), "Goodbye. You can start a new conversation any time."),
    (("who is your developer", "who developed you", "who created you", "who made you", "who built you"),
     f"I was built by **{DEVELOPER}**. You can support the work or get in touch here:\n\n"
     f"- Sponsor on GitHub: {DEVELOPER_SPONSOR_URL}\n"
     f"- LinkedIn: {DEVELOPER_LINKEDIN_URL}"),
]


# =============================================================================
# INTENT DETECTION AND KNOWLEDGE MATCHING
# =============================================================================

def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def find_conversation_response(question: str) -> str | None:
    q = normalise(question)
    for patterns, response in _CONVERSATION_PATTERNS:
        for pattern in patterns:
            if q == pattern or q.startswith(pattern + " ") or q.startswith(pattern + "?"):
                return response
    return None


def detect_intent(question: str) -> str:
    q = normalise(question)
    if any(x in q for x in ("difference between", "compare", "versus", " vs ", " vs.")):
        return "comparison"
    if any(x in q for x in ("how do i", "how can i", "how to", "how does", "steps to")):
        return "how"
    if any(x in q for x in ("error", "exception", "traceback", "bug", "not working", "fails")):
        return "debugging"
    if any(x in q for x in ("advantages", "benefits", "pros", "why use")):
        return "advantages"
    if any(x in q for x in ("disadvantages", "limitations", "cons", "drawbacks")):
        return "limitations"
    if any(x in q for x in ("example", "show me", "sample")):
        return "example"
    if any(x in q for x in ("what is", "what are", "define", "meaning of")):
        return "definition"
    return "general"


def _contains_whole_phrase(haystack: str, phrase: str) -> bool:
    """Whole-word/phrase containment check. Plain substring search would let
    a short keyword like 'rag' match inside an unrelated word like
    'storage', which either creates false matches or (if scores are kept
    low to compensate) makes short but legitimate keywords such as 'rag',
    'jwt' or 'dns' impossible to match at all. Word boundaries fix both."""
    pattern = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def match_knowledge_base(question: str) -> list[tuple[int, dict[str, Any]]]:
    """Score every knowledge-base entry against the question and return the
    matches sorted by score, highest first. A score of zero means no
    keyword or topic name from that entry appeared in the question."""
    q = normalise(question)
    scored: list[tuple[int, dict[str, Any]]] = []

    for entry in KNOWLEDGE_BASE:
        score = 0
        for keyword in entry["keywords"]:
            if keyword and _contains_whole_phrase(q, keyword):
                score += max(2, len(keyword.split()) * 2)
        if _contains_whole_phrase(q, entry["topic"].lower()):
            score += 3
        if score:
            scored.append((score, entry))

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def redirect_message() -> str:
    return (
        "I will direct that question to **" + HUMAN_AGENTS_LABEL + "**, since it is not within "
        "my current knowledge base. I would rather tell you that plainly than guess."
    )


def build_kb_answer(entry: dict[str, Any], intent: str) -> str:
    name = entry["topic"]
    base = entry["answer"]

    if intent == "comparison":
        return (
            f"**{name}** is one side of that comparison.\n\n{base}\n\n"
            "A fair comparison should also weigh purpose, performance, complexity, security, "
            "ecosystem maturity and the actual constraints of your project."
        )
    if intent == "how":
        return (
            f"**{name}**\n\n{base}\n\n"
            "A practical way to get started: define the outcome you need, build the smallest "
            "working example, test it against a realistic case, then expand it step by step."
        )
    if intent == "debugging":
        return (
            f"**{name}**\n\n{base}\n\n"
            "For debugging specifically: reproduce the problem reliably, capture the exact error "
            "message, isolate the smallest failing piece of code, then change one thing at a time "
            "and retest."
        )
    if intent == "advantages":
        return (
            f"**{name}**\n\n{base}\n\n"
            "Whether these advantages apply to your case still depends on your team's skills, "
            "budget, performance needs and long-term maintenance plans."
        )
    if intent == "limitations":
        return (
            f"**{name}**\n\n{base}\n\n"
            "Worth weighing against this: operational complexity, cost, performance ceilings, "
            "security surface and how much ongoing maintenance it will need."
        )
    if intent == "example":
        return (
            f"**{name}**\n\n{base}\n\n"
            "If you share the specific scenario you are working on, I can point you to the most "
            "relevant part of this in more detail."
        )
    return f"### {name}\n\n{base}"


# =============================================================================
# OPTIONAL LIVE SEARCH (supplementary only, never a substitute for the KB)
# =============================================================================

def _safe_get(url: str, params: dict[str, Any] | None = None) -> requests.Response | None:
    try:
        response = requests.get(
            url,
            params=params,
            timeout=LIVE_TIMEOUT_SECONDS,
            headers={"User-Agent": f"{APP_TITLE.replace(' ', '-')}/1.0"},
        )
        response.raise_for_status()
        return response
    except requests.RequestException:
        return None


def _search_github(query: str, limit: int = 4) -> list[dict[str, str]]:
    response = _safe_get(
        "https://api.github.com/search/repositories",
        {"q": query[:180], "sort": "stars", "order": "desc", "per_page": limit},
    )
    if response is None:
        return []
    try:
        data = response.json()
    except ValueError:
        return []
    return [
        {
            "source": "GitHub",
            "title": item.get("full_name", "Repository"),
            "summary": item.get("description") or "No description available.",
            "url": item.get("html_url", "https://github.com"),
        }
        for item in data.get("items", [])[:limit]
    ]


def _search_stackoverflow(query: str, limit: int = 4) -> list[dict[str, str]]:
    response = _safe_get(
        "https://api.stackexchange.com/2.3/search/advanced",
        {"site": "stackoverflow", "q": query[:180], "order": "desc", "sort": "relevance", "pagesize": limit},
    )
    if response is None:
        return []
    try:
        data = response.json()
    except ValueError:
        return []
    return [
        {
            "source": "Stack Overflow",
            "title": re.sub(r"<[^>]+>", "", item.get("title", "Question")),
            "summary": "Developer question and community answers.",
            "url": item.get("link", "https://stackoverflow.com"),
        }
        for item in data.get("items", [])[:limit]
    ]


def _search_crossref(query: str, limit: int = 3) -> list[dict[str, str]]:
    response = _safe_get("https://api.crossref.org/works", {"query": query[:180], "rows": limit})
    if response is None:
        return []
    try:
        data = response.json()
    except ValueError:
        return []
    results = []
    for item in data.get("message", {}).get("items", [])[:limit]:
        title = (item.get("title") or ["Scholarly work"])[0]
        doi = item.get("DOI")
        url = f"https://doi.org/{doi}" if doi else "https://www.crossref.org/"
        results.append({"source": "Crossref", "title": title, "summary": "Scholarly publication metadata.", "url": url})
    return results


def _search_wikipedia(query: str, limit: int = 3) -> list[dict[str, str]]:
    response = _safe_get(
        "https://en.wikipedia.org/w/api.php",
        {"action": "query", "list": "search", "srsearch": query[:180], "format": "json", "srlimit": limit},
    )
    if response is None:
        return []
    try:
        data = response.json()
    except ValueError:
        return []
    results = []
    for item in data.get("query", {}).get("search", [])[:limit]:
        title = item.get("title", "Wikipedia article")
        url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
        snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
        results.append({"source": "Wikipedia", "title": title, "summary": snippet, "url": url})
    return results


def _search_duckduckgo(query: str) -> list[dict[str, str]]:
    """DuckDuckGo's Instant Answer API is the closest thing to a general web
    search that works with no API key. It is much narrower than a real
    Google result page (it mainly surfaces topic summaries and related
    concepts, not arbitrary ranked web pages), which is a genuine
    limitation worth knowing about rather than papering over."""
    response = _safe_get(
        "https://api.duckduckgo.com/",
        {"q": query[:180], "format": "json", "no_html": 1, "skip_disambig": 1},
    )
    if response is None:
        return []
    try:
        data = response.json()
    except ValueError:
        return []

    results: list[dict[str, str]] = []
    if data.get("AbstractText") and data.get("AbstractURL"):
        results.append({
            "source": "DuckDuckGo",
            "title": data.get("Heading") or query,
            "summary": data["AbstractText"],
            "url": data["AbstractURL"],
        })
    for topic in data.get("RelatedTopics", [])[:4]:
        if isinstance(topic, dict) and topic.get("FirstURL") and topic.get("Text"):
            results.append({
                "source": "DuckDuckGo",
                "title": topic["Text"].split(" - ")[0][:90],
                "summary": topic["Text"],
                "url": topic["FirstURL"],
            })
    return results


def _search_reddit(query: str, limit: int = 3) -> list[dict[str, str]]:
    """Public, read-only Reddit search. This uses no OAuth token, which
    means it can be rate-limited or blocked by Reddit at any time; it is
    included as a best-effort look at social/community discussion, not a
    guaranteed source. A dropped or empty response is treated the same as
    any other source that came up empty."""
    response = _safe_get(
        "https://www.reddit.com/search.json",
        {"q": query[:180], "limit": limit, "sort": "relevance"},
    )
    if response is None:
        return []
    try:
        data = response.json()
    except ValueError:
        return []
    results = []
    for child in data.get("data", {}).get("children", [])[:limit]:
        post = child.get("data", {})
        title = post.get("title")
        permalink = post.get("permalink")
        if not title or not permalink:
            continue
        results.append({
            "source": "Reddit",
            "title": title,
            "summary": f"r/{post.get('subreddit', 'reddit')} discussion.",
            "url": "https://www.reddit.com" + permalink,
        })
    return results


def _search_google_custom(query: str, limit: int = 4) -> list[dict[str, str]]:
    """Real Google results, but only if the deployer has set up a (free
    tier available) Google Programmable Search Engine and supplied its
    key and search-engine id as GOOGLE_CSE_API_KEY / GOOGLE_CSE_CX in
    Streamlit secrets or environment variables. There is no official way
    to query Google search results without credentials, so this stays
    optional rather than pretending to work out of the box."""
    api_key = st.secrets.get("GOOGLE_CSE_API_KEY", os.getenv("GOOGLE_CSE_API_KEY", ""))
    cx = st.secrets.get("GOOGLE_CSE_CX", os.getenv("GOOGLE_CSE_CX", ""))
    if not api_key or not cx:
        return []
    response = _safe_get(
        "https://www.googleapis.com/customsearch/v1",
        {"key": api_key, "cx": cx, "q": query[:180], "num": limit},
    )
    if response is None:
        return []
    try:
        data = response.json()
    except ValueError:
        return []
    return [
        {
            "source": "Google",
            "title": item.get("title", "Result"),
            "summary": item.get("snippet", ""),
            "url": item.get("link", ""),
        }
        for item in data.get("items", [])[:limit]
    ]


_LIVE_SEARCH_TRIGGERS = (
    "find current", "find recent", "find github", "find repositories",
    "find projects", "current github", "on github", "github projects",
    "github repositories", "search github", "current research",
    "recent research", "recent papers", "current papers", "current news",
    "latest news", "latest version", "current projects", "search for",
    "look up", "recent discussions", "current discussions",
)


def is_live_search_intent(question: str) -> bool:
    """True when the question is explicitly asking to go and look something
    up right now, as opposed to asking what something is. Definitional
    questions ('what is Python') should still be answered from the
    knowledge base even while live search is switched on; only an explicit
    request like 'find current GitHub projects for X' should route to live
    search instead of a keyword-matched knowledge-base topic."""
    q = normalise(question)
    return any(trigger in q for trigger in _LIVE_SEARCH_TRIGGERS)


def run_live_search(question: str) -> list[dict[str, str]]:
    """Query a handful of public sources. Results are only ever shown as
    attributed links, never rewritten into freestanding factual claims,
    which is what keeps this feature hallucination-free. This checks
    developer/technical sources, academic sources, a general-web source
    (DuckDuckGo, plus real Google results if the deployer has configured
    an API key), community/social discussion (Reddit) and finally
    Wikipedia as a fallback."""
    q = normalise(question)
    results: list[dict[str, str]] = []

    if any(x in q for x in ("code", "python", "javascript", "programming", "api", "github", "bug", "error")):
        results.extend(_search_github(question))
        results.extend(_search_stackoverflow(question))

    if any(x in q for x in ("research", "paper", "study", "literature", "journal", "academic")):
        results.extend(_search_crossref(question))

    results.extend(_search_google_custom(question))
    results.extend(_search_duckduckgo(question))
    results.extend(_search_reddit(question))

    if not results:
        results.extend(_search_wikipedia(question))

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in results:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        unique.append(item)

    return unique[:8]


# =============================================================================
# ANSWER ENGINE
# =============================================================================

def _format_live_results(evidence: list[dict[str, str]], as_primary: bool) -> str:
    if as_primary:
        lines = ["Here is what live search found:", ""]
    else:
        lines = [
            "This is outside my verified knowledge base, so I am not going to state it as fact. "
            "Live search did find some potentially relevant sources, which you should check "
            f"yourself. I can also direct this question to **{HUMAN_AGENTS_LABEL}** if you would "
            "prefer that instead:",
            "",
        ]
    for item in evidence:
        lines.append(f"- **{item['source']}** — [{item['title']}]({item['url']})")
    return "\n".join(lines)


def generate_answer(question: str, live_search_enabled: bool) -> tuple[str, list[dict[str, str]]]:
    conversational = find_conversation_response(question)
    if conversational:
        return conversational, []

    # An explicit request to go look something up externally takes priority
    # over a loose knowledge-base keyword match, so a question like "find
    # current GitHub projects for Python data engineering" is not silently
    # answered with the static definition of Python instead.
    if is_live_search_intent(question):
        if not live_search_enabled:
            return (
                "Live search is currently switched off, so I cannot go and look that up right "
                "now. Turn on live search next to the message box if you would like me to search "
                f"externally, or I will direct this question to **{HUMAN_AGENTS_LABEL}**.",
                [],
            )
        evidence = run_live_search(question)
        if evidence:
            return _format_live_results(evidence, as_primary=True), evidence
        # Fall through to the knowledge base and redirect logic below if
        # live search itself came back empty.

    matches = match_knowledge_base(question)

    if matches and matches[0][0] >= MIN_MATCH_SCORE:
        intent = detect_intent(question)
        answer = build_kb_answer(matches[0][1], intent)
        return answer, []

    browse = category_browse_answer(question)
    if browse:
        return browse, []

    evidence = run_live_search(question) if live_search_enabled else []
    if evidence:
        return _format_live_results(evidence, as_primary=False), evidence

    return redirect_message(), []


# =============================================================================
# FILE / DATA WORKSPACE UTILITIES
# =============================================================================

def read_uploaded_file(uploaded_file) -> tuple[pd.DataFrame | None, str]:
    suffix = Path(uploaded_file.name).suffix.lower()
    raw = uploaded_file.getvalue()

    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return None, f"Please upload a file smaller than {MAX_UPLOAD_MB} MB."

    try:
        if suffix == ".csv":
            return pd.read_csv(io.BytesIO(raw)), ""
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(io.BytesIO(raw)), ""
        if suffix == ".json":
            data = json.loads(raw.decode("utf-8"))
            return (pd.DataFrame(data) if isinstance(data, list) else pd.json_normalize(data)), ""
        if suffix in (".txt", ".md"):
            text = raw.decode("utf-8", errors="replace")
            return pd.DataFrame({"text": text.splitlines()}), ""
        return None, "Supported formats are CSV, XLSX, XLS, JSON, TXT and MD."
    except Exception:
        return None, "The file could not be read. Please check its format and try again."


def summarise_dataframe(df: pd.DataFrame) -> dict[str, int]:
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing": int(df.isna().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
    }


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [re.sub(r"\s+", "_", str(c).strip().lower()) for c in cleaned.columns]
    for column in cleaned.select_dtypes(include="object").columns:
        cleaned[column] = cleaned[column].map(lambda v: v.strip() if isinstance(v, str) else v)
    return cleaned.drop_duplicates()


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown(
        f"""
        <div class="obo-brand">
            <div class="obo-brand-title">{APP_TITLE}</div>
            <div class="obo-brand-subtitle">Developer: {DEVELOPER}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("＋ New chat", use_container_width=True, type="primary"):
        st.session_state.conversation_id = new_conversation_id()
        st.session_state.messages = []
        st.session_state.last_evidence = []
        st.rerun()

    st.divider()
    st.markdown("**Recent chats**")
    conversations = recent_conversations()
    if not conversations:
        st.caption("Your conversations will appear here once you send a message.")
    for conversation in conversations:
        label = (conversation["title"] or "New conversation")[:38]
        if st.button(label, key=f"conv_{conversation['id']}", use_container_width=True):
            st.session_state.conversation_id = conversation["id"]
            st.session_state.messages = load_conversation(conversation["id"])
            st.session_state.last_evidence = []
            st.rerun()

    st.divider()
    st.markdown("**Support the developer**")
    st.markdown(
        f"[Sponsor on GitHub]({DEVELOPER_SPONSOR_URL})  \n"
        f"[Connect on LinkedIn]({DEVELOPER_LINKEDIN_URL})"
    )


# =============================================================================
# MAIN LAYOUT
# =============================================================================

st.markdown(
    f"""
    <div class="obo-hero">
        <h1>{APP_TITLE}</h1>
        <p>Programming, web development, cloud, cybersecurity, AI and academic research.</p>
        <div class="obo-dev">Developer: {DEVELOPER}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(opening_greeting())

    cols = st.columns(3)
    cards = [
        ("Technology", "Programming languages, web development, databases, cloud, DevOps and cybersecurity."),
        ("AI & Data", "Machine learning, generative AI, RAG, data analysis, algorithms and your uploaded files."),
        ("Academic", "Research methodology, literature reviews, dissertations, statistics and referencing."),
    ]
    for column, (title, text) in zip(cols, cards):
        with column:
            st.markdown(
                f'<div class="obo-card"><div class="obo-card-title">{title}</div>'
                f'<div class="obo-card-text">{text}</div></div>',
                unsafe_allow_html=True,
            )
    st.write("")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.uploaded_data is not None:
    with st.expander(f"File workspace · {st.session_state.uploaded_name}", expanded=False):
        df = st.session_state.uploaded_data
        summary = summarise_dataframe(df)

        a, b, c, d = st.columns(4)
        a.metric("Rows", summary["rows"])
        b.metric("Columns", summary["columns"])
        c.metric("Missing", summary["missing"])
        d.metric("Duplicates", summary["duplicates"])

        st.dataframe(df.head(100), use_container_width=True)

        if st.button("Clean column names & duplicates", key="clean_dataset"):
            st.session_state.uploaded_data = clean_dataframe(df)
            st.success("The displayed dataset has been cleaned.")
            st.rerun()

        csv_bytes = st.session_state.uploaded_data.to_csv(index=False).encode("utf-8")
        st.download_button("Download cleaned CSV", data=csv_bytes, file_name="cleaned_data.csv", mime="text/csv")

# ---- Message box row: a compact live-search toggle beside the input, and ----
# file attachment handled natively by chat_input's own "+" control. Streamlit
# does not let a custom icon be injected inside the native input bar itself,
# so the closest faithful equivalent is the built-in attach control plus a
# toggle placed immediately next to it.
toggle_col, input_col = st.columns([0.16, 0.84])

with toggle_col:
    st.session_state.live_search_enabled = st.toggle(
        "Search",
        value=st.session_state.live_search_enabled,
        help=(
            "Only used when a question is outside the knowledge base, or when you explicitly "
            "ask to find or search for something current. Results are shown as attributed "
            "links, never rewritten as confirmed facts."
        ),
    )

with input_col:
    prompt = st.chat_input(
        f"Message {APP_TITLE}...",
        accept_file="multiple",
        file_type=["csv", "xlsx", "xls", "json", "txt", "md"],
    )

question = ""
attachment_summary = ""
attachment_error = ""

if prompt:
    question = (prompt.text or "").strip()
    for attached in prompt["files"] or []:
        df, error = read_uploaded_file(attached)
        if error:
            attachment_error = f"I could not read {attached.name}: {error}"
        else:
            st.session_state.uploaded_data = df
            st.session_state.uploaded_name = attached.name
            summary = summarise_dataframe(df)
            attachment_summary = (
                f"I've loaded **{attached.name}** into the file workspace above this message box "
                f"({summary['rows']} rows, {summary['columns']} columns, {summary['missing']} "
                f"missing values, {summary['duplicates']} duplicate rows). You can preview, clean "
                "or download it from there."
            )

if question or attachment_summary or attachment_error:
    display_question = question or "Uploaded a file."
    st.session_state.messages.append({"role": "user", "content": display_question})

    if len(st.session_state.messages) == 1:
        ensure_conversation_row(st.session_state.conversation_id, display_question)

    save_message(st.session_state.conversation_id, "user", display_question)

    with st.chat_message("user"):
        st.markdown(display_question)

    with st.chat_message("assistant"):
        evidence: list[dict[str, str]] = []
        parts = []
        if attachment_error:
            parts.append(attachment_error)
        elif attachment_summary:
            parts.append(attachment_summary)
        if question:
            with st.spinner("Checking the knowledge base..."):
                text_answer, evidence = generate_answer(question, st.session_state.live_search_enabled)
            parts.append(text_answer)
        answer = "\n\n".join(parts)
        st.markdown(answer)
        if evidence:
            with st.expander(f"Sources · {len(evidence)}", expanded=False):
                for item in evidence:
                    st.markdown(f"- **{item['source']}** · [{item['title']}]({item['url']})")

    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_message(st.session_state.conversation_id, "assistant", answer)
    st.session_state.last_evidence = evidence
    st.rerun()

st.markdown(
    f'<div class="obo-footer">{APP_TITLE} · Developer: {DEVELOPER} · '
    f'Unanswered questions are redirected to {HUMAN_AGENTS_LABEL}<br>'
    f'<a href="{DEVELOPER_SPONSOR_URL}" target="_blank">Support on GitHub</a> · '
    f'<a href="{DEVELOPER_LINKEDIN_URL}" target="_blank">LinkedIn</a></div>',
    unsafe_allow_html=True,
)
