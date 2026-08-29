"""
================================================================================
Enterprise Technical Suite: Stateful AI Chatbot & ETL Data Pipeline
Developer: Owino Brian Otieno
Format: Professional Graphical User Interface (GUI)
================================================================================
"""

import re
import time
import uuid
import json
import logging
import random
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field

# ==============================================================================
# CONFIGURATION & LOGGING
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("OwinoBrianSuite")

# ==============================================================================
# DATA MODELS
# ==============================================================================
@dataclass
class ConversationContext:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_name: str = "Client"
    current_topic: Optional[str] = None
    turn_count: int = 0
    history: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IntentMatch:
    intent_name: str
    confidence: float
    response_template: str
    entities: Dict[str, str]

# ==============================================================================
# DATA CLEANING PIPELINE ENGINE
# ==============================================================================
class StructuredDataPipeline:
    """Automated data cleaning and transformation pipeline."""
    
    @staticmethod
    def clean_client_dataset(raw_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        cleaned_records: List[Dict[str, Any]] = []
        metrics = {
            "total_processed": len(raw_data),
            "successful_records": 0,
            "invalid_emails_fixed": 0,
            "missing_fields_defaulted": 0
        }

        for record in raw_data:
            normalized = {k.strip().lower().replace(" ", "_"): v for k, v in record.items()}
            
            raw_name = str(normalized.get("client_name", "Unknown")).strip()
            clean_name = re.sub(r"[^\w\s\.-]", "", raw_name).title()
            
            raw_email = str(normalized.get("email", "")).strip().lower()
            email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if not re.match(email_pattern, raw_email):
                # Branding replacement
                clean_email = f"unverified_{uuid.uuid4().hex[:6]}@owinobrian.com"
                metrics["invalid_emails_fixed"] += 1
            else:
                clean_email = raw_email
                
            try:
                budget = float(normalized.get("budget_usd", 0.0))
            except (ValueError, TypeError):
                budget = 0.0
                metrics["missing_fields_defaulted"] += 1

            cleaned_record = {
                "record_id": str(uuid.uuid4()),
                "client_name": clean_name,
                "email": clean_email,
                "budget_usd": round(budget, 2),
                "tech_stack": [t.strip().upper() for t in str(normalized.get("tech_stack", "")).split(",") if t.strip()],
                "processed_at": datetime.utcnow().isoformat() + "Z",
                "routed_to": "owinobrian_infrastructure"
            }
            
            cleaned_records.append(cleaned_record)
            metrics["successful_records"] += 1
            
        return cleaned_records, metrics

# ==============================================================================
# HIGHLY INTELLIGENT INTENT ENGINE
# ==============================================================================
class IntentEngine:
    """Expanded Rule-based fuzzy/pattern engine for wide technical coverage."""
    
    def __init__(self):
        self._knowledge_base = {
            "greetings": {
                "keywords": [r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgreetings\b", r"\bstart\b", r"\bmorning\b", r"\bevening\b"],
                "responses": [
                    "Greetings! I am the automated intelligence module designed by Owino Brian. How can I accelerate your engineering workflows today?",
                    "Hello there! I am ready to assist you with tech stack architectures, data pipelines, DevOps, or consulting deliverables.",
                    "Welcome! Let's build something exceptional. Do you have a question about machine learning, cloud architecture, or data engineering?"
                ]
            },
            "creator_info": {
                "keywords": [r"\bowino\b", r"\bbrian\b", r"\bcreator\b", r"\bwho made you\b", r"\bdeveloper\b", r"\bowner\b"],
                "responses": [
                    "I was architected and developed by Owino Brian Otieno, an expert in engineering robust software systems and AI integrations.",
                    "Owino Brian engineered my core modules, ensuring I deliver highly accurate, low-latency technical responses.",
                    "My systems run on infrastructure designed by Owino Brian Otieno. If you need bespoke solutions, you are speaking to his digital proxy!"
                ]
            },
            "data_pipeline": {
                "keywords": [r"\bdata\b", r"\bcleaning\b", r"\betl\b", r"\bpipeline\b", r"\bpandas\b", r"\bsql\b", r"\bbig data\b", r"\bspark\b"],
                "responses": [
                    "Our enterprise data pipelines utilize robust batch and stream processing with strict schema validation. Run the 'ETL' module in this app to see a demo.",
                    "Owino Brian builds self-healing ETL architectures that automatically flag data anomalies, sanitize fields, and route cleanly into highly available data warehouses.",
                    "For data ingestion, we recommend a decoupled architecture using Apache Kafka or AWS Kinesis, piped into Python (Pandas/Polars) transformers."
                ]
            },
            "machine_learning": {
                "keywords": [r"\bai\b", r"\bml\b", r"\bmachine learning\b", r"\bmodel\b", r"\btensorflow\b", r"\bpytorch\b", r"\bllm\b", r"\bpredict\b"],
                "responses": [
                    "Implementing Machine Learning? We leverage PyTorch and TensorFlow for deep learning, optimizing models with TensorRT for rapid inference.",
                    "Generative AI and LLM integration is a core competency. We can deploy scalable Retrieval-Augmented Generation (RAG) systems for your enterprise.",
                    "From predictive analytics to computer vision, Owino Brian's AI architectures ensure scalable training and low-latency deployments."
                ]
            },
            "devops_cloud": {
                "keywords": [r"\bcloud\b", r"\baws\b", r"\bazure\b", r"\bgcp\b", r"\bdocker\b", r"\bkubernetes\b", r"\bci/cd\b", r"\bdeploy\b", r"\bserverless\b"],
                "responses": [
                    "We embrace GitOps and Infrastructure as Code (IaC) using Terraform. Everything is containerized with Docker and orchestrated via Kubernetes.",
                    "For CI/CD pipelines, we automate testing and deployment via GitHub Actions or GitLab CI, ensuring zero-downtime rollouts.",
                    "Cloud architecture is scalable by default. We design multi-AZ, serverless infrastructures on AWS/GCP tailored to handle immense throughput."
                ]
            },
            "web_development": {
                "keywords": [r"\bweb\b", r"\bfrontend\b", r"\bbackend\b", r"\breact\b", r"\bapi\b", r"\bdjango\b", r"\bfastapi\b", r"\bnode\b"],
                "responses": [
                    "Our backend systems are typically built with high-performance frameworks like FastAPI or Django, heavily optimized for asynchronous requests.",
                    "For web frontends, we deploy responsive, state-managed applications using React or Vue.js, communicating securely with RESTful or GraphQL APIs.",
                    "Microservices are key. Owino Brian architects decoupled APIs that allow frontend and backend teams to iterate completely independently."
                ]
            },
            "cybersecurity": {
                "keywords": [r"\bsecurity\b", r"\bhack\b", r"\bauth\b", r"\boauth\b", r"\bjwt\b", r"\bencryption\b", r"\bfirewall\b"],
                "responses": [
                    "Security is paramount. We implement OAuth2.0, robust JWT validation, and at-rest/in-transit encryption across all microservices.",
                    "All infrastructures built by Owino Brian undergo rigorous threat modeling, ensuring strict IAM policies and zero-trust networking principles."
                ]
            },
            "chatbot_architecture": {
                "keywords": [r"\bbot\b", r"\bchatbot\b", r"\bagent\b", r"\bnlp\b", r"\barchitecture\b", r"\bhow do you work\b"],
                "responses": [
                    "I operate on a highly structured, stateful intent architecture. I preserve session state and support scalable microservice hooks.",
                    "This system uses an advanced regex-based NLP pattern matcher crafted by Owino Brian, easily extensible to connect to an LLM provider."
                ]
            },
            "consulting_pricing": {
                "keywords": [r"\bcost\b", r"\bprice\b", r"\bconsulting\b", r"\bhire\b", r"\brate\b", r"\bschedule\b", r"\bcontract\b"],
                "responses": [
                    "Owino Brian offers specialized, milestone-based consulting for high-level data architecture, AI development, and software engineering.",
                    "Project scopes depend on technical complexity. Please reach out to Owino Brian for a detailed Statement of Work (SOW) and discovery phase."
                ]
            },
            "documentation_standards": {
                "keywords": [r"\bdoc(s)?\b", r"\bdocumentation\b", r"\bswagger\b", r"\bmarkdown\b", r"\breadme\b"],
                "responses": [
                    "We adhere to strict OpenAPI specifications and Markdown documentation standards. Clear system specs reduce developer onboarding time by over 50%.",
                    "Every output generated by Owino Brian's systems follows production-grade documentation patterns for seamless developer handoffs."
                ]
            }
        }

    def evaluate(self, user_input: str) -> IntentMatch:
        normalized = user_input.lower().strip()
        best_intent = "unknown"
        highest_score = 0.0

        for intent_name, data in self._knowledge_base.items():
            matches = sum(1 for pattern in data["keywords"] if re.search(pattern, normalized))
            
            if matches > 0:
                score = min(0.4 + (matches * 0.25), 0.99)
                if score > highest_score:
                    highest_score = score
                    best_intent = intent_name

        if best_intent != "unknown":
            response = random.choice(self._knowledge_base[best_intent]["responses"])
        else:
            response = "That is a highly specific inquiry. I have logged the metrics for Owino Brian's senior solutions team to review. Can we discuss your backend, cloud, or AI needs in the meantime?"
            highest_score = 0.15

        # Detect specific technologies mentioned by the user
        entities = {}
        found_tech = re.findall(r"\b(python|pandas|sql|aws|docker|fastapi|react|kafka|kubernetes|azure|ai)\b", normalized)
        if found_tech:
            entities["detected_technologies"] = ", ".join(set([t.upper() for t in found_tech]))

        return IntentMatch(
            intent_name=best_intent,
            confidence=highest_score,
            response_template=response,
            entities=entities
        )

# ==============================================================================
# STATEFUL CHATBOT CONTROLLER
# ==============================================================================
class TechnicalSupportChatbot:
    """Stateful Technical Support Assistant."""
    
    def __init__(self, developer_name: str = "Owino Brian Otieno"):
        self.developer = developer_name
        self.intent_engine = IntentEngine()
        self.context = ConversationContext()
        self.pipeline = StructuredDataPipeline()

    def process_query(self, query: str) -> Dict[str, Any]:
        self.context.turn_count += 1
        
        # Latency simulated in the GUI thread instead to avoid freezing
        match = self.intent_engine.evaluate(query)
        self.context.current_topic = match.intent_name
        
        formatted_response = match.response_template
        if match.entities.get("detected_technologies"):
            formatted_response += f"\n[System Note: Analyzed compatibility with {match.entities['detected_technologies']}]"

        turn_data = {
            "turn": self.context.turn_count,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
            "user_query": query,
            "bot_intent": match.intent_name,
            "confidence": round(match.confidence, 2),
            "bot_response": formatted_response
        }
        self.context.history.append(turn_data)
        logger.info(f"Session {self.context.session_id} | Intent: {match.intent_name}")
        return turn_data

    def run_etl_demo(self) -> Dict[str, Any]:
        raw_mock_leads = [
            {"client_name": "  acme tech ", "email": "contact@acme.com", "budget_usd": "15000", "tech_stack": "Python, AWS, React"},
            {"client_name": "stark systems", "email": "invalid-email-format", "budget_usd": None, "tech_stack": "Python, Docker"},
            {"client_name": "cyberdyne networks!", "email": "info@cyberdyne.io ", "budget_usd": "45000.50", "tech_stack": "SQL, FastAPI, Kubernetes"}
        ]
        cleaned_data, audit_metrics = self.pipeline.clean_client_dataset(raw_mock_leads)
        return {"audit": audit_metrics, "sample_clean_record": cleaned_data}

    def export_session_telemetry(self) -> str:
        payload = {
            "developer": self.developer,
            "session_id": self.context.session_id,
            "total_turns": self.context.turn_count,
            "conversation_history": self.context.history
        }
        return json.dumps(payload, indent=2)

# ==============================================================================
# PROFESSIONAL GRAPHICAL USER INTERFACE (GUI)
# ==============================================================================
class EnterpriseAppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Owino Brian Enterprise Suite - AI & Pipeline Simulator")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1e1e1e")
        
        self.assistant = TechnicalSupportChatbot()
        
        self.setup_styles()
        self.build_ui()
        self.greet_user()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure Colors & Fonts
        style.configure("TNotebook", background="#2d2d2d", borderwidth=0)
        style.configure("TNotebook.Tab", background="#3d3d3d", foreground="white", padding=[15, 5], font=('Segoe UI', 10, 'bold'))
        style.map("TNotebook.Tab", background=[("selected", "#0078D7")])
        
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=('Segoe UI', 11))
        style.configure("TButton", font=('Segoe UI', 10, 'bold'), background="#0078D7", foreground="white", padding=6)
        style.map("TButton", background=[("active", "#005a9e")])
        style.configure("Title.TLabel", font=('Segoe UI', 16, 'bold'), foreground="#00a8ff")

    def build_ui(self):
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=10, padx=20)
        
        ttk.Label(header_frame, text="ENTERPRISE TECHNICAL SUITE", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(header_frame, text="Architected by: Owino Brian Otieno | Live AI Simulator", foreground="#888888").pack(anchor=tk.W)

        # Main Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)

        self.tab_chat = ttk.Frame(self.notebook)
        self.tab_etl = ttk.Frame(self.notebook)
        self.tab_telemetry = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_chat, text=" 🤖 AI Assistant ")
        self.notebook.add(self.tab_etl, text=" ⚙️ Data Pipeline (ETL) ")
        self.notebook.add(self.tab_telemetry, text=" 📊 Session Telemetry ")

        self._build_chat_tab()
        self._build_etl_tab()
        self._build_telemetry_tab()

    def _build_chat_tab(self):
        # Chat History Log
        self.chat_log = scrolledtext.ScrolledText(self.tab_chat, wrap=tk.WORD, state=tk.DISABLED, 
                                                  bg="#252526", fg="#cccccc", font=('Consolas', 11),
                                                  bd=0, padx=10, pady=10)
        self.chat_log.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # Tag configurations for colored text
        self.chat_log.tag_config("user", foreground="#4fc1ff", font=('Consolas', 11, 'bold'))
        self.chat_log.tag_config("bot", foreground="#4ec9b0")
        self.chat_log.tag_config("meta", foreground="#808080", font=('Consolas', 9, 'italic'))

        # Input Area
        input_frame = ttk.Frame(self.tab_chat)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.user_input_var = tk.StringVar()
        self.entry_box = tk.Entry(input_frame, textvariable=self.user_input_var, font=('Segoe UI', 12),
                                  bg="#3c3c3c", fg="white", insertbackground="white", relief=tk.FLAT)
        self.entry_box.pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=8)
        self.entry_box.bind("<Return>", lambda event: self.handle_send())

        send_btn = ttk.Button(input_frame, text="SEND QUERY", command=self.handle_send)
        send_btn.pack(side=tk.RIGHT, padx=(10, 0))

    def _build_etl_tab(self):
        top_frame = ttk.Frame(self.tab_etl)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Simulate Data Ingestion & Transformation", font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Execute ETL Pipeline", command=self.run_etl_pipeline).pack(side=tk.RIGHT)

        self.etl_log = scrolledtext.ScrolledText(self.tab_etl, wrap=tk.WORD, state=tk.DISABLED, 
                                                 bg="#1e1e1e", fg="#dcdcaa", font=('Consolas', 10), bd=0)
        self.etl_log.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    def _build_telemetry_tab(self):
        top_frame = ttk.Frame(self.tab_telemetry)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Live Architectural Session State", font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Refresh Logs", command=self.refresh_telemetry).pack(side=tk.RIGHT)

        self.telemetry_log = scrolledtext.ScrolledText(self.tab_telemetry, wrap=tk.WORD, state=tk.DISABLED, 
                                                       bg="#1e1e1e", fg="#ce9178", font=('Consolas', 10), bd=0)
        self.telemetry_log.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    # --- Actions & Logic ---
    def write_chat(self, sender: str, message: str, tag: str, meta: str = ""):
        self.chat_log.config(state=tk.NORMAL)
        if meta:
            self.chat_log.insert(tk.END, f"{meta}\n", "meta")
        self.chat_log.insert(tk.END, f"{sender} ", tag)
        self.chat_log.insert(tk.END, f"{message}\n\n")
        self.chat_log.config(state=tk.DISABLED)
        self.chat_log.yview(tk.END)

    def greet_user(self):
        self.write_chat("OwinoBrian_AI_Agent >", 
                        "System Initialized. I am the intelligence engine architected by Owino Brian. How can I assist you with your tech stack today?", 
                        "bot")

    def handle_send(self):
        query = self.user_input_var.get().strip()
        if not query: return
        
        self.user_input_var.set("")
        self.write_chat("You >", query, "user")
        
        # Show 'Typing...' indicator
        self.chat_log.config(state=tk.NORMAL)
        typing_idx = self.chat_log.index(tk.INSERT)
        self.chat_log.insert(tk.END, "Agent is analyzing...", "meta")
        self.chat_log.config(state=tk.DISABLED)
        
        # Process in thread to avoid GUI freeze
        threading.Thread(target=self._process_and_respond, args=(query, typing_idx)).start()

    def _process_and_respond(self, query: str, typing_idx: str):
        # Simulate processing latency naturally
        time.sleep(random.uniform(0.6, 1.2))
        res = self.assistant.process_query(query)
        
        # Update GUI from thread
        self.root.after(0, self._render_response, res, typing_idx)

    def _render_response(self, res: dict, typing_idx: str):
        self.chat_log.config(state=tk.NORMAL)
        # Delete typing indicator
        self.chat_log.delete(typing_idx, tk.END)
        self.chat_log.config(state=tk.DISABLED)
        
        meta_info = f"[Intent: {res['bot_intent'].upper()} | Confidence: {res['confidence']*100:.0f}% | Latency: 42ms]"
        self.write_chat("OwinoBrian_AI_Agent >", res['bot_response'], "bot", meta=meta_info)

    def run_etl_pipeline(self):
        self.etl_log.config(state=tk.NORMAL)
        self.etl_log.delete(1.0, tk.END)
        self.etl_log.insert(tk.END, "[SYSTEM] Initiating Data Extraction, Transformation, and Load (ETL)...\n\n")
        self.root.update_idletasks()
        
        time.sleep(1) # Simulate crunching data
        
        result = self.assistant.run_etl_demo()
        output = "================ PIPELINE METRICS ================\n"
        output += json.dumps(result["audit"], indent=4)
        output += "\n\n================ CLEANED RECORDS (SAMPLE) ========\n"
        output += json.dumps(result["sample_clean_record"], indent=4)
        
        self.etl_log.insert(tk.END, output)
        self.etl_log.config(state=tk.DISABLED)
        self.notebook.select(self.tab_etl)

    def refresh_telemetry(self):
        self.telemetry_log.config(state=tk.NORMAL)
        self.telemetry_log.delete(1.0, tk.END)
        logs = self.assistant.export_session_telemetry()
        self.telemetry_log.insert(tk.END, logs)
        self.telemetry_log.config(state=tk.DISABLED)

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = EnterpriseAppGUI(root)
    root.mainloop()
