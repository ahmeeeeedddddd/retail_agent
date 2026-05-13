import os
import logging
from google import genai
from google.genai import types

# We will let user pass keys through env
def generate_manager_report(total_products, critical_alerts, forecast_acc, clusters_summary):
    import warnings
    warnings.simplefilter('ignore', FutureWarning)
    
    API_KEY = os.getenv("GEMINI_API_KEY", "")
    if not API_KEY:
        return {
            "summary": "Gemini API key missing. Mock summary generated.",
            "insights": "Mock cluster insights.",
            "actions": "Mock recommended actions."
        }
        
    try:
        client = genai.Client(api_key=API_KEY)
        
        prompt = f"""
        You are an AI Manager for an e-commerce retail store in Egypt. Give a clean, concise tactical report.
        Focus: Explain the recent outcomes, specific actions taken by the autonomous agent, and the underlying SHAP drivers (mathematical explanations) for market anomalies.
        
        Overall Data: {total_products} total products, {critical_alerts} critical alerts.
        Cluster Metrics: {clusters_summary}.
        
        Format your response as JSON with exactly these keys: 'summary', 'insights', 'actions'.
        """
        
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json"
            )
        )
        
        import json
        if response and response.text:
            try:
                report_data = json.loads(response.text)
                return {
                    "summary": report_data.get("summary", "N/A"),
                    "insights": report_data.get("insights", "N/A"),
                    "actions": report_data.get("actions", "N/A")
                }
            except json.JSONDecodeError:
                logging.error("Failed to decode Gemini JSON response.")
        
        raise ValueError("Empty or invalid response from Gemini")

    except Exception as e:
        # Graceful fallback for Quota/API errors
        status_msg = "Market Analysis: Stability Observed" if critical_alerts == 0 else f"Market Alert: {critical_alerts} Zones require attention"
        return {
            "summary": f"Autonomous Report (AI Logic Paused): {status_msg}. System is running in statistical fallback mode.",
            "insights": f"Current system metrics show {forecast_acc}% forecast accuracy. Cluster distribution analysis is {clusters_summary}.",
            "actions": "Continue standard monitoring. AI-enhanced tactical reasoning will resume once API quota is restored."
        }

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_action_email(product_id, store_id, units, action, context=None):
    """
    Revised: Handles URGENT priority for Human Audit actions and includes the trace.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Configuration
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = os.getenv("SMTP_USER", "aahmedaboalfath2005@gmail.com")
    PASSWORD = os.getenv("SMTP_PASS")
    RECEIVER_EMAIL = "ahmedaboalfath15@gmail.com"

    if not PASSWORD:
        logging.warning("SMTP Password not found in .env. Skipping email dispatch.")
        return False

    is_urgent = "Human" in action or "Escalate" in action or "Audit" in action
    priority_label = "URGENT: " if is_urgent else ""
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"{priority_label}RetailMind Action: {action} on {product_id}"
    
    if is_urgent:
        msg.add_header('X-Priority', '1 (Highest)')
        msg.add_header('Importance', 'High')

    thoughts = context.get('thoughts', 'Routine monitoring cycle.') if context else "..."
    trace_html = ""
    if context and 'trace' in context:
        trace_steps = "<br>".join([f"&bull; {step}" for step in context['trace']])
        trace_html = f"""
        <div style="background-color: #f0f7ff; padding: 12px; border-radius: 5px; margin-top: 10px; border-left: 4px solid #3b82f6;">
            <strong>Internal Process Trace:</strong><br>
            <span style="font-family: monospace; font-size: 13px; color: #444;">{trace_steps}</span>
        </div>
        """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: {'#d9534f' if is_urgent else '#337ab7'};">Tactical Agentic Execution</h2>
        <p>Product <b>{product_id}</b> at Store <b>{store_id}</b> was evaluated with <b>{units} units</b> impact.</p>
        <p><b>Determined Action:</b> <span style="color: orange; font-weight: bold;">{action}</span></p>
        
        <div style="background-color: #f9f9f9; padding: 15px; border-top: 2px solid #337ab7;">
            <h3>AI Reasoning Log</h3>
            <p><b>Agent Thought:</b> <i>"{thoughts}"</i></p>
            {trace_html}
        </div>
        <p style="margin-top: 20px; font-size: 11px; color: #999;">
            This is an automated tactical action dispatched by the RetailMind Autonomous Agent.
        </p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        logging.info(f"✓ SMTP Tactical Alert successfully sent to {RECEIVER_EMAIL}")
        return True
    except Exception as e:
        logging.error(f"❌ SMTP Tactical Error: {e}")
        return False

def calculate_action_score(svm_confidence, shap_score_sum, sarima_trend_percent):
    score = (svm_confidence * 0.4) + (shap_score_sum * 0.3) + (sarima_trend_percent * 0.3)
    return score

def send_executive_summary_email(report_json, metrics):
    """
    Sends a full AI-generated Market Intelligence Report via SMTP.
    """
    smtp_host = os.getenv("GMAIL_SMTP_HOST") or os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("GMAIL_SMTP_PORT") or os.getenv("SMTP_PORT") or 587)
    smtp_user = os.getenv("GMAIL_SMTP_USER") or os.getenv("SMTP_USER")
    smtp_pass = os.getenv("GMAIL_SMTP_PASS") or os.getenv("SMTP_PASS")
    
    from_email = os.getenv("ALERT_FROM_EMAIL", "alerts@retailmind.com")
    to_email = os.getenv("ALERT_TO_EMAIL", "manager@retailmind.com")

    if not all([smtp_host, smtp_user, smtp_pass]):
        print("SMTP Config Missing for Executive Report.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = f"RetailMind Intelligence Pulse | {metrics.get('criticalAlerts', 0)} Alerts"
    message["From"] = smtp_user
    message["To"] = to_email

    summary = report_json.get("summary", "No summary available.")
    insights = report_json.get("insights", "No insights available.")
    actions = report_json.get("actions", "Check dashboard for details.")

    html_content = f"""
    <html>
    <body style="font-family: sans-serif; color: #333;">
        <div style="background-color: #1a1c23; color: #fff; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0; color: #3b82f6;">RetailMind AI Intelligence</h1>
            <p style="margin: 5px 0;">Autonomous Market Analysis & Strategy</p>
        </div>
        <div style="padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #3b82f6; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Executive Summary</h2>
            <p>{summary}</p>
            
            <h2 style="color: #3b82f6; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Key Market Insights</h2>
            <p>{insights}</p>
            
            <h2 style="color: #3b82f6; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Recommended Strategic Actions</h2>
            <p style="background-color: #f3f4f6; padding: 15px; border-radius: 5px; font-weight: bold; border-left: 5px solid #3b82f6;">
                {actions}
            </p>
            
            <div style="margin-top: 20px; padding: 10px; background-color: #eef2ff; border-radius: 5px;">
                <strong>Cycle Telemetry:</strong><br/>
                Total Products: {metrics.get('totalProducts', 0)} | 
                Critical Alerts: {metrics.get('criticalAlerts', 0)}
            </div>
        </div>
        <div style="text-align: center; font-size: 12px; color: #999; margin-top: 20px;">
            This was an automated intelligence pulse from the RetailMind Agent.
        </div>
    </body>
    </html>
    """
    message.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, message.as_string())
        logging.info(f"✓ Executive Summary successfully sent to {to_email}")
        return True
    except Exception as e:
        logging.error(f"❌ Report Email Failed: {e}")
        return False
