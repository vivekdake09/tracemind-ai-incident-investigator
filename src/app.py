import os
import sys
import json
import streamlit as st
from dotenv import load_dotenv

# Ensure project root is available in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Guard against Streamlit watcher attempting to inspect optional multi-modal submodules in transformers
if "torchvision" not in sys.modules:
    try:
        import torchvision
    except ImportError:
        from unittest.mock import MagicMock
        sys.modules["torchvision"] = MagicMock()
        sys.modules["torchvision.transforms"] = MagicMock()
        sys.modules["torchvision.transforms.v2"] = MagicMock()
        sys.modules["torchvision.transforms.v2.functional"] = MagicMock()

from src.investigator import Investigator, PRIMARY_MODEL, FALLBACK_MODELS
from src.schemas import InvestigationReport
from src.log_parser import MAX_LOG_LENGTH, MAX_STACK_LENGTH, MAX_TITLE_LENGTH
from src.tools import get_available_tool_definitions

# Load local environment configuration
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="TraceMind — Production Incident Investigator",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS: Understated Developer Engineering Aesthetic
st.markdown("""
<style>
    /* Global styles */
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Header typography */
    h1, h2, h3, h4 {
        color: #0F172A;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    
    /* Monospace elements */
    code, pre, .mono-text {
        font-family: "JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace !important;
        font-size: 0.85rem !important;
    }
    
    /* Input fields styling */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 4px;
        color: #0F172A;
        font-family: "JetBrains Mono", Consolas, monospace;
        font-size: 0.85rem;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #2563EB;
        box-shadow: 0 0 0 1px #2563EB;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #0F172A;
        color: #F8FAFC;
        border: 1px solid #0F172A;
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.85rem;
        padding: 0.4rem 0.8rem;
        transition: all 0.15s ease;
    }
    .stButton>button:hover {
        background-color: #1E293B;
        border-color: #1E293B;
        color: #FFFFFF;
    }
    
    /* Custom status indicators */
    .status-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.55rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        letter-spacing: 0.02em;
    }
    .status-online { background-color: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; }
    .status-offline { background-color: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; }
    .status-warning { background-color: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
    .status-error { background-color: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; }

    /* Confidence Badges */
    .badge-confidence-High {
        background-color: #EFF6FF;
        color: #1E40AF;
        border: 1px solid #BFDBFE;
        padding: 0.15rem 0.45rem;
        border-radius: 3px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-confidence-Medium {
        background-color: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
        padding: 0.15rem 0.45rem;
        border-radius: 3px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-confidence-Low {
        background-color: #F1F5F9;
        color: #475569;
        border: 1px solid #E2E8F0;
        padding: 0.15rem 0.45rem;
        border-radius: 3px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Panels & Containers */
    .eng-panel {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 4px;
        padding: 1.1rem;
        margin-bottom: 1rem;
    }
    .evidence-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 3px solid #2563EB;
        padding: 0.8rem;
        margin-bottom: 0.75rem;
        border-radius: 0 4px 4px 0;
    }
    .tool-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 3px solid #0F172A;
        padding: 0.8rem;
        margin-bottom: 0.75rem;
        border-radius: 0 4px 4px 0;
    }
    .warning-box {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        color: #92400E;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }
    .info-notice {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-radius: 4px;
        padding: 0.5rem 0.75rem;
        color: #166534;
        font-size: 0.8rem;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("GROQ_API_KEY", "")
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False if st.session_state.api_key else True
if "model_name" not in st.session_state:
    st.session_state.model_name = PRIMARY_MODEL
if "incident_input" not in st.session_state:
    st.session_state.incident_input = {
        "title": "",
        "logs": "",
        "stack_trace": "",
        "api_response": "",
        "code_snippet": ""
    }
if "investigation_results" not in st.session_state:
    st.session_state.investigation_results = None
if "model_status_cache" not in st.session_state:
    st.session_state.model_status_cache = None

# Sidebar Configuration
with st.sidebar:
    st.markdown("### TraceMind")
    st.caption("AI Production Incident Investigator • v1.0")
    st.markdown("---")

    st.markdown("#### Provider Settings")
    api_key_input = st.text_input(
        "Groq API Key",
        type="password",
        value=st.session_state.api_key,
        help="Free API key from console.groq.com. Stored only in session memory."
    )
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input
        st.session_state.model_status_cache = None

    selected_model = st.selectbox(
        "Inference Model",
        options=[PRIMARY_MODEL] + FALLBACK_MODELS,
        index=0,
        help="Instruction-tuned model on Groq hardware"
    )
    if selected_model != st.session_state.model_name:
        st.session_state.model_name = selected_model
        st.session_state.model_status_cache = None

    demo_toggle = st.checkbox(
        "Demo Mode (Offline / Free)",
        value=st.session_state.demo_mode,
        help="Generates verified synthetic reports without external API calls."
    )
    st.session_state.demo_mode = demo_toggle

    # Real Model Status Health Check
    st.markdown("#### System Connectivity")
    if st.session_state.demo_mode:
        st.markdown("<span class='status-pill status-offline'>Demo Mode (Offline)</span>", unsafe_allow_html=True)
        st.caption("No external inference calls are made.")
    else:
        if st.button("Check API Status", use_container_width=True) or st.session_state.model_status_cache is None:
            investigator_probe = Investigator(api_key=st.session_state.api_key, model_name=st.session_state.model_name)
            st.session_state.model_status_cache = investigator_probe.check_model_status()
        
        status_info = st.session_state.model_status_cache
        if status_info["online"]:
            st.markdown(f"<span class='status-pill status-online'>Live API Online ({status_info['latency_ms']}ms)</span>", unsafe_allow_html=True)
            st.caption(f"Connected to Groq ({status_info['model']}).")
        else:
            st.markdown("<span class='status-pill status-error'>API Unreachable</span>", unsafe_allow_html=True)
            st.caption(status_info["message"])

    st.markdown("---")
    st.markdown("#### Diagnostic Tool Registry")
    tools = get_available_tool_definitions()
    for t in tools:
        st.markdown(f"• **`{t['name']}`**")
        st.caption(t["description"])

    st.markdown("---")
    st.caption("Human Approval Policy: TraceMind generates hypotheses and diagnostic recommendations. It never mutates production systems or runs destructive commands.")
    st.markdown("[Documentation](README.md) • [Evaluation Suite](evaluation/results.json)")

# Header Section
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title("TraceMind: Incident Investigator")
    st.markdown(
        "Root cause hypothesis generation and diagnostic analysis grounded in historical incident postmortems and runbooks."
    )
with header_col2:
    st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)
    if st.session_state.demo_mode:
        st.markdown("<span class='status-pill status-offline' style='font-size: 0.85rem;'>MODE: OFFLINE DEMO</span>", unsafe_allow_html=True)
    elif st.session_state.model_status_cache and st.session_state.model_status_cache["online"]:
        st.markdown("<span class='status-pill status-online' style='font-size: 0.85rem;'>MODE: LIVE INFERENCE</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-pill status-warning' style='font-size: 0.85rem;'>MODE: UNCONFIGURED</span>", unsafe_allow_html=True)

# Privacy & Security Banner
st.markdown("""
<div class='info-notice'>
    <strong>Local Privacy Filter Active:</strong> All input logs, traces, and API payloads are automatically sanitized for passwords, Bearer tokens, JWTs, AWS credentials, and database connection strings before processing.
</div>
""", unsafe_allow_html=True)

# Layout Tabs
tab_investigate, tab_evaluation, tab_about = st.tabs(["Investigation Console", "Quantitative Evaluation", "System Architecture"])

# -----------------------------------------------------------------------------
# TAB 1: Investigation Console
# -----------------------------------------------------------------------------
with tab_investigate:
    # Preset sample incident loader
    st.markdown("#### Sample Incident Scenarios")
    sample_col1, sample_col2, sample_col3, sample_col4, sample_col5 = st.columns(5)

    with sample_col1:
        if st.button("DB Pool Timeout", use_container_width=True):
            st.session_state.incident_input = {
                "title": "Database Connection Timeout on Checkout Service",
                "logs": "FATAL: connection to database 'payments' failed\ntimeout expired while waiting for connection slot in pool\nserver closed connection unexpectedly at 10.0.4.12:5432",
                "stack_trace": "psycopg2.OperationalError: timeout expired\n  at db_pool.acquire() line 84 in /app/db/client.py\n  at handle_checkout() line 124 in /app/services/checkout.py",
                "api_response": "504 Gateway Timeout",
                "code_snippet": "with db_pool.acquire(timeout=5) as conn:\n    conn.cursor().execute('SELECT * FROM orders WHERE id = %s', (order_id,))"
            }
            st.rerun()

    with sample_col2:
        if st.button("401 JWT Rotation", use_container_width=True):
            st.session_state.incident_input = {
                "title": "Spike in HTTP 401 Unauthorized Errors on Mobile API",
                "logs": "HTTP 401 Unauthorized: Invalid signature for JWT token\nToken header alg=RS256 kid=2026-auth-key-q3\nFailed authentication attempt for user_id=98214 tenant_id=45",
                "stack_trace": "jwt.exceptions.InvalidSignatureError: Signature verification failed\n  at verify_token() line 45 in /app/auth/verifier.py\n  at auth_middleware() line 22 in /app/middleware/auth.py",
                "api_response": "401 Unauthorized",
                "code_snippet": "decoded = jwt.decode(token, key=cached_public_key, algorithms=['RS256'])"
            }
            st.rerun()

    with sample_col3:
        if st.button("Missing Config", use_container_width=True):
            st.session_state.incident_input = {
                "title": "Inventory Service Failed Container Startup",
                "logs": "KeyError: 'INVENTORY_DB_URL' not found in environment variables.\nContainer terminated with exit code 1 (CrashLoopBackOff)",
                "stack_trace": "KeyError: 'INVENTORY_DB_URL'\n  at os.environ['INVENTORY_DB_URL'] line 14 in /app/config.py\n  at init_app() line 30 in /app/main.py",
                "api_response": "N/A (Container crashed before port binding)",
                "code_snippet": "database_url = os.environ['INVENTORY_DB_URL']"
            }
            st.rerun()

    with sample_col4:
        if st.button("Redis OOM", use_container_width=True):
            st.session_state.incident_input = {
                "title": "Redis Cache OOM Rejection on User Sessions",
                "logs": "Redis::CommandError: OOM command not allowed when used memory > 'maxmemory' on cluster shard 2\nEviction rate 0 keys/sec under policy noeviction",
                "stack_trace": "redis.exceptions.ResponseError: OOM command not allowed\n  at set_session() line 52 in /app/cache/session.py",
                "api_response": "500 Internal Server Error",
                "code_snippet": "redis_client.set(f'session:{user_id}', session_data)"
            }
            st.rerun()

    with sample_col5:
        if st.button("Unknown / Insufficient", use_container_width=True):
            st.session_state.incident_input = {
                "title": "Uncatalogued Quantum Kernel Desync Error",
                "logs": "QuantumEntanglementBus: coherence lost at cryogenic bus 4 sector 9 (code 0x99B4F)\nTelemetry buffer frame dropped",
                "stack_trace": "",
                "api_response": "Unknown Hardware Code 0x99B4F",
                "code_snippet": ""
            }
            st.rerun()

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Input Form
    input_col1, input_col2 = st.columns([3, 2])

    with input_col1:
        title_val = st.text_input(
            "Incident Title *",
            value=st.session_state.incident_input["title"],
            max_chars=MAX_TITLE_LENGTH,
            placeholder="e.g., Database Connection Timeout on Checkout Service",
            help="High-level description of the observable incident."
        )

        logs_val = st.text_area(
            "Application Logs *",
            value=st.session_state.incident_input["logs"],
            height=180,
            max_chars=MAX_LOG_LENGTH,
            placeholder="Paste stderr, stdout, or container logs here (credentials scrubbed automatically)...",
            help=f"Max {MAX_LOG_LENGTH} characters. Treated as untrusted input."
        )
        st.caption(f"{len(logs_val):,} / {MAX_LOG_LENGTH:,} characters")

    with input_col2:
        stack_val = st.text_area(
            "Stack Trace (Optional)",
            value=st.session_state.incident_input["stack_trace"],
            height=100,
            max_chars=MAX_STACK_LENGTH,
            placeholder="Paste language exception stack trace...",
        )

        api_val = st.text_input(
            "API Response / HTTP Status (Optional)",
            value=st.session_state.incident_input["api_response"],
            placeholder="e.g., 504 Gateway Timeout or JSON error payload",
        )

        code_val = st.text_area(
            "Related Code Snippet (Optional)",
            value=st.session_state.incident_input["code_snippet"],
            height=60,
            placeholder="Optional Python/Go/JS snippet near callsite...",
        )

    # Submission
    btn_col1, btn_col2 = st.columns([1, 4])
    with btn_col1:
        run_btn = st.button("Investigate Incident", type="primary", use_container_width=True)

    with btn_col2:
        if st.session_state.demo_mode:
            st.caption("Running in Free Demo Mode. Results will be synthesized offline from verified patterns.")
        elif not st.session_state.api_key:
            st.caption("Warning: No Groq API key set. Execution will use offline Demo Mode.")

    if run_btn:
        if not title_val.strip():
            st.error("Validation Error: Incident Title is required.")
        elif not logs_val.strip():
            st.error("Validation Error: Application Logs are required.")
        else:
            with st.spinner("Analyzing logs, querying ChromaDB vector store, and running diagnostics..."):
                investigator = Investigator(
                    api_key=st.session_state.api_key,
                    model_name=st.session_state.model_name
                )
                
                analysis_result = investigator.analyze(
                    title=title_val,
                    logs=logs_val,
                    stack_trace=stack_val,
                    api_response=api_val,
                    demo_mode=st.session_state.demo_mode,
                )
                st.session_state.investigation_results = analysis_result

    # Display Results
    if st.session_state.investigation_results:
        res = st.session_state.investigation_results
        
        st.markdown("---")
        
        if res.get("status") == "error":
            st.error(f"Investigation Failed: {res.get('message')}")
            if "details" in res:
                st.code(res["details"])
        else:
            report_data = res.get("report", {})
            evidence_data = res.get("evidence", [])
            tools_data = res.get("tool_results", {})
            warnings = res.get("validation_warnings", [])
            redactions = res.get("redactions_count", 0)

            # Metadata header
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            with meta_col1:
                st.caption(f"**Execution Mode:** `{res.get('mode', 'unknown').upper()}`")
            with meta_col2:
                st.caption(f"**Engine / Model:** `{res.get('model_used', 'N/A')}`")
            with meta_col3:
                st.caption(f"**Redacted Credentials:** `{redactions}` items scrubbed locally")

            # Grounding Warnings if any
            if warnings:
                for w in warnings:
                    st.markdown(f"<div class='warning-box'><strong>Grounding Enforcement:</strong> {w}</div>", unsafe_allow_html=True)

            # Incident Summary Panel
            st.markdown("<div class='eng-panel'>", unsafe_allow_html=True)
            st.markdown("### Incident Summary & Assessment")
            st.write(report_data.get("incident_summary", "No summary provided."))
            
            if report_data.get("insufficient_evidence"):
                st.markdown("""
                <div class='warning-box'>
                    <strong>Insufficient Evidence Declared:</strong> The knowledge base lacks sufficiently similar historical incidents or runbooks. 
                    Hypotheses are abstained or flagged as ungrounded to prevent hallucination.
                </div>
                """, unsafe_allow_html=True)
            
            if report_data.get("missing_information"):
                st.markdown(f"**Information Needed for Conclusive Diagnosis:**\n{report_data['missing_information']}")
            st.markdown("</div>", unsafe_allow_html=True)

            # Two Column Results: Hypotheses vs Evidence & Diagnostics
            res_col1, res_col2 = st.columns([3, 2])

            with res_col1:
                st.markdown("### Root Cause Hypotheses (Ranked)")
                st.caption("Formulated as plausible hypotheses. Requires engineer verification before action.")

                hypotheses = report_data.get("hypotheses", [])
                if not hypotheses:
                    st.info("No plausible hypotheses generated due to insufficient matching evidence.")
                else:
                    for i, hyp in enumerate(hypotheses):
                        conf = hyp.get("confidence", "Medium")
                        with st.container():
                            st.markdown(f"""
                            <div class='eng-panel'>
                                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;'>
                                    <h4 style='margin: 0;'>#{hyp.get('rank', i+1)}: {hyp.get('title')}</h4>
                                    <span class='badge-confidence-{conf}'>{conf.upper()} CONFIDENCE</span>
                                </div>
                                <p style='color: #334155; font-size: 0.9rem;'>{hyp.get('explanation')}</p>
                            </div>
                            """, unsafe_allow_html=True)

                            with st.expander("Diagnostic Checks & Human Remediation Steps", expanded=True):
                                st.markdown("##### Recommended Diagnostic Checks")
                                checks = hyp.get("diagnostic_checks", [])
                                if checks:
                                    for chk in checks:
                                        st.markdown(f"• **`{chk.get('check_name')}`**: {chk.get('description')}")
                                else:
                                    st.caption("No specific automated checks recommended.")

                                st.markdown("##### Proposed Remediation (Pending Human Approval)")
                                st.markdown(f"> {hyp.get('remediation')}")

                                st.markdown("##### Post-Fix Verification Steps")
                                st.markdown(f"• {hyp.get('verification_steps')}")

                                cited = hyp.get("cited_evidence_ids", [])
                                if cited:
                                    st.caption(f"**Cited Evidence Records:** {', '.join([f'`{cid}`' for cid in cited])}")
                                else:
                                    st.caption("**Cited Evidence Records:** None (Abstained or ungrounded)")

            with res_col2:
                st.markdown("### Retrieved Evidence")
                st.caption("Relevant historical incident records and runbooks retrieved from ChromaDB.")

                if not evidence_data:
                    st.caption("No evidence records returned from vector store.")
                else:
                    for ev in evidence_data:
                        score_pct = int(ev.get("similarity_score", 0.0) * 100)
                        st.markdown(f"""
                        <div class='evidence-card'>
                            <div style='display: flex; justify-content: space-between;'>
                                <span class='mono-text' style='font-weight: 600;'>{ev['id']}</span>
                                <span class='mono-text' style='color: #2563EB;'>{score_pct}% match</span>
                            </div>
                            <div style='font-size: 0.8rem; color: #64748B; margin-bottom: 0.3rem;'>Source: {ev['source']} • {ev['title']}</div>
                            <div class='mono-text' style='color: #334155; white-space: pre-wrap; max-height: 120px; overflow-y: auto;'>{ev['content'][:250]}...</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("### Executed Diagnostic Activity")
                st.caption("Safe, whitelisted tools executed during investigation.")

                if not tools_data:
                    st.caption("No diagnostic tools executed.")
                else:
                    for tool_name, tool_res in tools_data.items():
                        st.markdown(f"""
                        <div class='tool-card'>
                            <div class='mono-text' style='font-weight: 600;'>Tool: {tool_name}</div>
                            <div style='font-size: 0.75rem; color: #166534;'>Status: {tool_res.get('status')}</div>
                            <pre style='background: #F1F5F9; padding: 0.4rem; border-radius: 3px; max-height: 100px; overflow-y: auto;'>{json.dumps(tool_res.get('output', {}), indent=2)}</pre>
                        </div>
                        """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 2: Quantitative Evaluation
# -----------------------------------------------------------------------------
with tab_evaluation:
    st.markdown("### Automated Evaluation Benchmark")
    st.markdown(
        "TraceMind includes a standalone evaluation suite (`evaluation/evaluate.py`) that evaluates "
        "both dense vector retrieval recall and diagnosis accuracy against a labeled dataset of incident scenarios."
    )

    results_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evaluation", "results.json")
    if os.path.exists(results_file):
        with open(results_file, "r", encoding="utf-8") as f:
            eval_data = json.load(f)

        metrics = eval_data.get("metrics", {})
        metadata = eval_data.get("metadata", {})
        cases = eval_data.get("cases", [])

        # Metric Tiles
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        with m_col1:
            st.metric("Recall@5", f"{metrics.get('recall_at_5', 0.0) * 100:.1f}%")
            st.caption("Relevant record in top 5")
        with m_col2:
            st.metric("Top-1 Diagnosis", f"{metrics.get('top_1_diagnosis_accuracy', 0.0) * 100:.1f}%")
            st.caption("Rank-1 hypothesis matches")
        with m_col3:
            st.metric("Evidence Support", f"{metrics.get('evidence_support_rate', 0.0) * 100:.1f}%")
            st.caption("Citations match retrieved IDs")
        with m_col4:
            st.metric("Schema Validity", f"{metrics.get('schema_validity_rate', 0.0) * 100:.1f}%")
            st.caption("Pydantic validation pass rate")
        with m_col5:
            st.metric("Abstention Accuracy", f"{metrics.get('abstention_accuracy', 0.0) * 100:.1f}%")
            st.caption("Correct insufficient handling")

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

        st.markdown("#### Scenario Evaluation Breakdown")
        
        # Display table of test cases
        table_rows = []
        for c in cases:
            table_rows.append({
                "ID": c.get("id"),
                "Category": c.get("category"),
                "Incident Scenario": c.get("title"),
                "Retrieval Hit": "Yes" if c.get("retrieval_hit") is True else str(c.get("retrieval_hit")),
                "Top-1 Match": "Yes" if c.get("top1_diagnosis_match") else "No",
                "Citations Valid": c.get("cited_ids_valid"),
                "Abstention Correct": "Yes" if c.get("abstained_correctly") else "No",
                "Schema Pass": "Yes" if c.get("schema_valid") else "No",
            })
        st.dataframe(table_rows, use_container_width=True)

        st.markdown("#### Methodology & Limitations Note")
        st.info(metadata.get("limitations_note", "Evaluation performed on synthetic test scenarios."))
    else:
        st.info("No evaluation results found. Run `python evaluation/evaluate.py` to generate metrics.")

# -----------------------------------------------------------------------------
# TAB 3: System Architecture
# -----------------------------------------------------------------------------
with tab_about:
    st.markdown("### System Architecture & Grounding Pipeline")
    st.markdown("""
    TraceMind applies a four-stage pipeline to ensure incident hypotheses remain strictly grounded in verified engineering knowledge:
    """)

    st.markdown("""
    ```
    +---------------------------------------------------------------------------------------------------+
    |                                   TRACEMIND INGESTION & RUNTIME                                   |
    +---------------------------------------------------------------------------------------------------+
    |                                                                                                   |
    |  [data/incidents.jsonl] + [data/runbooks/*.md]                                                    |
    |         |                                                                                         |
    |         v                                                                                         |
    |  [SentenceTransformers all-MiniLM-L6-v2] ---> [ChromaDB Vector Store (Persistent)]               |
    |                                                                |                                  |
    |                                                                v (Dense Search Top-5)             |
    |  [Raw Logs & Traces] ---> [Log Sanitizer (Scrub Credentials)] ---> [Prompt Context Assembly]      |
    |                                    |                                       |                      |
    |                                    v                                       v                      |
    |                         [Safe Diagnostic Tools]                   [Groq Llama-3.3-70B]            |
    |                                    |                                       |                      |
    |                                    +-------------------------------------> v                      |
    |                                                         [Pydantic Schema Validation]              |
    |                                                                    |                              |
    |                                                                    v                              |
    |                                                   [Code-Level Citation Verifier]                  |
    |                                                                    |                              |
    |                                                                    v                              |
    |                                                   [TraceMind Streamlit Dashboard]                 |
    +---------------------------------------------------------------------------------------------------+
    ```
    """)

    arch_col1, arch_col2 = st.columns(2)
    with arch_col1:
        st.markdown("#### Hallucination Defenses")
        st.markdown("""
        1. **Strict Context Grounding**: Prompts explicitly constrain the LLM to cite only documents present in the prompt.
        2. **Code-Level Verification**: The application verifies cited IDs against actual retrieved ChromaDB IDs and strips hallucinated citations with inline warnings.
        3. **Safe Abstention**: If vector similarity drops below the relevance threshold, the engine forces an `insufficient_evidence` declaration.
        """)

    with arch_col2:
        st.markdown("#### Safety & Security Architecture")
        st.markdown("""
        1. **Client-Side Credential Scrubbing**: Bearer tokens, passwords, DB URIs, and API keys are redacted locally before any network dispatch.
        2. **Untrusted Prompt Isolation**: Logs and stack traces are fenced inside explicit untrusted markdown blocks with anti-prompt-injection headers.
        3. **Whitelisted Tool Dispatch**: Diagnostic tools are limited to deterministic, read-only inspection functions validated via Pydantic schemas.
        """)

# Footer
st.markdown("---")
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.caption("TraceMind v1.0 • Built with Python, Streamlit, ChromaDB, Sentence Transformers, and Groq.")
with footer_col2:
    st.caption("Results are AI-generated hypotheses. Always verify before executing production remediations.")
