import gradio as gr
import json
import logging
import uuid
import time
import base64
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any

from app.database import SessionLocal
from app.models.statement import BankStatement
from app.services.fraud_model import fraud_engine
from app.services.compliance_agent import compliance_agent
from app.services.finlens_engine import finlens_engine
from app.services.drift_detector import drift_detector
from app.services.document_parser import statement_parser

logger = logging.getLogger(__name__)

# --- Styling and Aesthetics ---
CSS = """
body {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: 'Inter', -apple-system, sans-serif;
}
.gradio-container {
    background-color: #0F172A !important;
    border: none !important;
}
.premium-card {
    background: rgba(30, 41, 59, 0.7);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
}
.accent-button {
    background: linear-gradient(135deg, #14A085, #0D7377) !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
.accent-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 15px rgba(20, 160, 133, 0.4) !important;
}
.nav-tabs {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
}
.tabitem {
    border: none !important;
}
"""

def generate_shap_plot(shap_values: dict) -> plt.Figure:
    """Generates a clean, modern horizontal bar chart of SHAP values using matplotlib."""
    fig, ax = plt.subplots(figsize=(6, 3.2), facecolor='#1E293B')
    ax.set_facecolor('#1E293B')
    
    # Sort features by absolute contribution
    sorted_feats = sorted(shap_values.items(), key=lambda x: abs(x[1]))
    names = [f[0].replace("_", " ").title() for f in sorted_feats]
    values = [f[1] for f in sorted_feats]
    
    # Elegant color palette: Red for positive (risk increasing), Teal for negative (risk reducing)
    colors = ['#EF4444' if v >= 0 else '#10B981' for v in values]
    
    bars = ax.barh(names, values, color=colors, height=0.6, edgecolor='none')
    
    # Add vertical baseline
    ax.axvline(0, color='rgba(255,255,255,0.2)', linestyle='--', linewidth=0.8)
    
    # Customize axis styling
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('rgba(255,255,255,0.2)')
    ax.spines['bottom'].set_color('rgba(255,255,255,0.2)')
    
    ax.tick_params(colors='#94A3B8', labelsize=9)
    ax.set_title("SHAP Feature Contributions\n(Red increases risk, Green reduces risk)", color='#F8FAFC', fontsize=11, pad=10, weight='bold')
    ax.set_xlabel("Impact on Fraud Probability", color='#94A3B8', fontsize=9)
    
    plt.tight_layout()
    return fig

# --- Service Wrappers for UI Callbacks ---

def run_fraud_scoring(amount: float, hour: int, velocity: int, distance: float, merchant_risk: float, channel: str):
    """Callback for FraudSense scoring execution."""
    tx_dict = {
        "amount": amount,
        "hour": hour,
        "velocity_1h": velocity,
        "distance_from_home": distance,
        "merchant_risk": merchant_risk,
        "channel": channel,
        "user_id": str(uuid.uuid4())
    }
    
    # Hook drift check
    drift_detector.check_drift(amount, velocity)
    
    # Run scoring
    res = fraud_engine.score_transaction(tx_dict)
    
    prob = res["fraud_probability"]
    tier = res["risk_tier"]
    explanation = res["explanation"]
    shap_vals = res["shap_values"]
    source = res["model_source"]
    
    # Create HTML stylized badge
    color_map = {
        "LOW": "#10B981",
        "MEDIUM": "#F59E0B",
        "HIGH": "#EF4444",
        "CRITICAL": "#7F1D1D"
    }
    badge_color = color_map.get(tier, "#94A3B8")
    
    badge_html = f"""
    <div style="background-color: {badge_color}; color: white; padding: 12px 24px; border-radius: 8px; font-weight: bold; font-size: 20px; display: inline-block; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
        {tier} RISK TIER
    </div>
    """
    
    fig = generate_shap_plot(shap_vals)
    
    return (
        badge_html,
        f"**Probability:** {prob * 100:.1f}%\n\n**Anomaly Score:** {res['anomaly_score']:.4f}",
        explanation,
        fig,
        f"Executed via: `{source}`"
    )

def run_compliance_query(query: str):
    """Callback for RegGuard compliance Q&A."""
    res = compliance_agent.query_compliance(query)
    
    answer = res["answer"]
    citations = res.get("citations", [])
    confidence = res.get("confidence", 0.0)
    model = res.get("model_used", "Offline")
    time_ms = res.get("processing_time_ms", 0.0)
    
    # Format Citations as a Markdown table
    citation_text = ""
    if citations:
        citation_text = "### 📚 Retrieved Regulatory Citations\n\n| Document | Section | Relevance Score | Extract Preview |\n| :--- | :--- | :--- | :--- |\n"
        for cite in citations:
            score = cite.get('relevance_score', 0.0)
            preview = cite.get('chunk_text_preview', '').replace('\n', ' ')
            if len(preview) > 100:
                preview = preview[:100] + "..."
            citation_text += f"| {cite.get('document', 'RBI')} | Section {cite.get('section', 'N/A')} | {score:.2f} | {preview} |\n"
    else:
        citation_text = "*No specific regulatory citations retrieved.*"
        
    stats_markdown = f"""
    * **Confidence Index:** `{confidence:.2f}`
    * **LLM Engine:** `{model}`
    * **Latency:** `{time_ms:.1f}ms`
    """
    
    return answer, citation_text, stats_markdown

def upload_statement_callback(file_obj):
    """Callback for statement uploading and processing."""
    if file_obj is None:
        return "No file selected.", gr.update()
        
    try:
        with open(file_obj.name, "r") as f:
            content = f.read()
            
        db = SessionLocal()
        try:
            res = statement_parser.parse_and_store_statement(db, content)
            
            # Re-fetch statement list for dropdown
            statements = db.query(BankStatement).all()
            choices = [f"ID {s.id} - {s.bank_name} (Ending Balance: ₹{s.ending_balance:,.2f})" for s in statements]
            
            summary_info = f"""
            ### ✅ Statement Uploaded & Parsed Successfully!
            * **Statement ID:** `{res['statement_id']}`
            * **Bank Name:** `{res['bank_name']}`
            * **Account Number:** `{res['account_number']}`
            * **Total Deposits:** `₹{res['total_deposits']:,.2f}`
            * **Total Withdrawals:** `₹{res['total_withdrawals']:,.2f}`
            * **Ending Balance:** `₹{res['ending_balance']:,.2f}`
            * **Row Count:** `{res['transaction_count']}`
            """
            
            return summary_info, gr.update(choices=choices, value=choices[-1] if choices else None)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error handling UI upload: {e}")
        return f"### ❌ Parsing Failed\nError detail: {str(e)}", gr.update()

def run_statement_query(dropdown_val: str, query: str):
    """Callback for FinLens statement natural language auditing."""
    if not dropdown_val:
        return "Please upload a bank statement first.", "", "No Query Executed"
        
    try:
        # Extract statement ID
        statement_id = int(dropdown_val.split(" ")[1])
        
        db = SessionLocal()
        try:
            res = finlens_engine.answer_numerical_query(db, query, statement_id)
            
            answer = res["answer"]
            sql = res.get("compiled_sql", "N/A")
            status = res.get("audit_status", "COMPLETED")
            
            return (
                f"### 💬 FinLens Response\n\n{answer}",
                sql,
                f"Audit Status: `{status}`"
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error executing statement query: {e}")
        return f"Failed to execute query: {str(e)}", "", "Execution Failed"

def check_monitoring_drift():
    """Callback for Monitoring drift analysis."""
    # Read the current rolling window and trigger a report
    current_df = pd.DataFrame({
        "amount": list(drift_detector.amount_window) if drift_detector.amount_window else [0.0],
        "velocity_1h": list(drift_detector.velocity_window) if drift_detector.velocity_window else [1]
    })
    
    # Run report
    report = Report(metrics=[DataDriftPreset()])
    report.run(
        reference_data=drift_detector.baseline_df[["amount", "velocity_1h"]],
        current_data=current_df
    )
    drift_detector.last_report = report
    
    report_dict = report.as_dict()
    drift_table = None
    for m in report_dict.get("metrics", []):
        if m.get("metric") == "DataDriftTable":
            drift_table = m
            break
            
    amount_score = 0.0
    velocity_score = 0.0
    dataset_drift = False
    
    if drift_table:
        res_cols = drift_table["result"]["drift_by_columns"]
        amount_score = 1.0 - res_cols["amount"].get("drift_score", 1.0)
        velocity_score = 1.0 - res_cols["velocity_1h"].get("drift_score", 1.0)
        dataset_drift = drift_table["result"].get("dataset_drift", False)
        
    # Build a nice markdown display
    summary_md = f"""
    ### 📊 Live Data Drift Summary (Evidently AI)
    
    | Feature Name | Drift Index (1 - p_value) | Drift Detected? | Statistical test used |
    | :--- | :--- | :--- | :--- |
    | **amount** | `{amount_score:.4f}` | `{"YES" if amount_score > 0.95 else "NO"}` | Z-test / KS-test |
    | **velocity_1h** | `{velocity_score:.4f}` | `{"YES" if velocity_score > 0.95 else "NO"}` | Z-test / KS-test |
    
    * **Overall Dataset Drift State:** `{"⚠️ DRIFT DETECTED" if dataset_drift else "✅ STABLE"}`
    * **Current Sample Window Size:** `{len(current_df)} / 100` (evaluations require >= 10 rows)
    """
    
    # Base64 iframe report
    report_base64 = drift_detector.get_drift_report_html_base64()
    iframe_html = f"""
    <iframe src="data:text/html;base64,{report_base64}" width="100%" height="800px" style="border:1px solid rgba(255,255,255,0.1); border-radius:8px; background-color:white;"></iframe>
    """
    
    return summary_md, iframe_html

# --- Dashboard Layout Building ---

def build_dashboard():
    """Initializes the unified Gradio blocks dashboard with structured premium layouts."""
    # Fetch existing statements to pre-populate dropdown
    db = SessionLocal()
    try:
        statements = db.query(BankStatement).all()
        initial_choices = [f"ID {s.id} - {s.bank_name} (Ending Balance: ₹{s.ending_balance:,.2f})" for s in statements]
    except Exception:
        initial_choices = []
    finally:
        db.close()
        
    with gr.Blocks(theme=gr.themes.Default(), css=CSS) as demo:
        gr.HTML("""
        <div style="text-align: center; padding: 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;">
            <h1 style="color: #14A085; margin: 0; font-size: 32px; font-weight: 800; letter-spacing: 1px;">ARTHA AI</h1>
            <p style="color: #94A3B8; margin: 5px 0 0 0; font-size: 16px;">Production-Grade FinTech Intelligence & Observability Platform</p>
        </div>
        """)
        
        with gr.Tabs():
            # Tab 1: FraudSense
            with gr.Tab("🧠 FraudSense Real-Time Scoring"):
                gr.Markdown("### Real-Time Transaction Anomaly & Fraud Assessment")
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### Transaction Parameters")
                        amount = gr.Number(label="Transaction Amount (₹ INR)", value=5000.0)
                        hour = gr.Slider(label="Hour of Execution", minimum=0, maximum=23, value=12, step=1)
                        velocity = gr.Slider(label="Transaction Frequency (Last Hour)", minimum=0, maximum=50, value=1, step=1)
                        distance = gr.Number(label="Distance from Cardholder Address (km)", value=5.0)
                        merchant_risk = gr.Slider(label="Merchant Risk Index", minimum=0.0, maximum=1.0, value=0.05, step=0.01)
                        channel = gr.Dropdown(label="Processing Channel", choices=["UPI", "CASH", "CARD"], value="UPI")
                        
                        score_btn = gr.Button("Evaluate Transaction", elem_classes="accent-button")
                        
                    with gr.Column(scale=1):
                        gr.Markdown("#### Fraud Assessment Output")
                        with gr.Row():
                            badge_out = gr.HTML("<div style='color:#94A3B8;'>Submit a transaction for evaluation</div>")
                            prob_out = gr.Markdown("")
                        
                        explanation_out = gr.Markdown("### Explanation Detail\n*No transaction processed yet.*")
                        source_out = gr.Markdown("")
                        
                        gr.Markdown("#### explainability analysis")
                        shap_plot = gr.Plot(label="SHAP Analysis")
                        
                score_btn.click(
                    fn=run_fraud_scoring,
                    inputs=[amount, hour, velocity, distance, merchant_risk, channel],
                    outputs=[badge_out, prob_out, explanation_out, shap_plot, source_out]
                )
                
            # Tab 2: RegGuard
            with gr.Tab("📋 RegGuard Compliance RAG"):
                gr.Markdown("### Indian Regulatory Compliance RAG Query Engine")
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### Compliance Query")
                        compliance_input = gr.Textbox(
                            label="Enter Query (e.g. RBI guidelines, UPI limits, FEMA regulations)", 
                            placeholder="e.g. What is the UPI daily transaction limit?",
                            value="What is the UPI daily limit?"
                        )
                        compliance_btn = gr.Button("Search Regulations", elem_classes="accent-button")
                        
                        gr.Markdown("#### Session Execution Metadata")
                        compliance_metadata = gr.Markdown("*Metrics will appear here after query execution.*")
                        
                    with gr.Column(scale=2):
                        gr.Markdown("#### Compliance Ruling")
                        compliance_output = gr.Markdown("### RAG Ruling Result\n*Waiting for compliance query...*")
                        
                        citations_output = gr.Markdown("")
                        
                compliance_btn.click(
                    fn=run_compliance_query,
                    inputs=[compliance_input],
                    outputs=[compliance_output, citations_output, compliance_metadata]
                )
                
            # Tab 3: FinLens
            with gr.Tab("🔍 FinLens Statement Auditing"):
                gr.Markdown("### Conversational SQL Statement Auditing Engine")
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### Step 1: Upload Bank Statement")
                        file_input = gr.File(label="Upload Bank Statement File (CSV or Pipe-Delimited text)", file_types=[".csv", ".txt"])
                        upload_btn = gr.Button("Parse & Ingest Statement", elem_classes="accent-button")
                        
                        upload_status = gr.Markdown("")
                        
                    with gr.Column(scale=2):
                        gr.Markdown("#### Step 2: Conversational Statement Auditing")
                        statement_dropdown = gr.Dropdown(
                            label="Select Statement to Audit",
                            choices=initial_choices,
                            value=initial_choices[-1] if initial_choices else None
                        )
                        
                        query_input = gr.Textbox(
                            label="Conversational Numerical Query",
                            placeholder="e.g. How much did I spend on food?",
                            value="How much did I spend on food?"
                        )
                        query_btn = gr.Button("Execute Audit Query", elem_classes="accent-button")
                        
                        query_output = gr.Markdown("### Audit Output\n*Waiting for query execution...*")
                        sql_box = gr.Code(label="Compiled SQL Executed", language="sql")
                        query_status = gr.Markdown("")
                        
                upload_btn.click(
                    fn=upload_statement_callback,
                    inputs=[file_input],
                    outputs=[upload_status, statement_dropdown]
                )
                
                query_btn.click(
                    fn=run_statement_query,
                    inputs=[statement_dropdown, query_input],
                    outputs=[query_output, sql_box, query_status]
                )
                
            # Tab 4: Monitoring
            with gr.Tab("📈 MLOps & Data Drift"):
                gr.Markdown("### Statistical Feature Data Drift Monitoring (Evidently AI)")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### Observability Control Center")
                        drift_btn = gr.Button("Calculate Live Data Drift", elem_classes="accent-button")
                        drift_summary = gr.Markdown("*Run analysis to view live feature drift indices.*")
                        
                    with gr.Column(scale=2):
                        gr.Markdown("#### Evidently AI Report")
                        drift_iframe = gr.HTML("""
                        <div style="border:1px solid rgba(255,255,255,0.1); border-radius:8px; background-color:#1E293B; height:300px; display:flex; justify-content:center; align-items:center; color:#94A3B8;">
                            Click 'Calculate Live Data Drift' to render the fully interactive Evidently AI HTML dashboard report.
                        </div>
                        """)
                        
                drift_btn.click(
                    fn=check_monitoring_drift,
                    inputs=[],
                    outputs=[drift_summary, drift_iframe]
                )
                
        gr.HTML("""
        <div style="text-align: center; padding: 20px 0; border-top: 1px solid rgba(255,255,255,0.1); margin-top: 40px; color: #64748B; font-size: 12px;">
            Artha AI Platform · Powered by Groq LLaMA-3.1-70B · Under JPMC GCC & Tier-1 Technical Scrutiny
        </div>
        """)
        
    return demo

if __name__ == "__main__":
    demo = build_dashboard()
    demo.launch(server_port=7860)
