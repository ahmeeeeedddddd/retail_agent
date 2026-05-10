import os
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
        You are an AI Manager for an e-commerce retail store in Egypt. Give a clean, concise report.
        Data: {total_products} total products, {critical_alerts} critical alerts, Forecast Accuracy: {forecast_acc}%.
        Clusters: {clusters_summary}.
        
        Format your response as JSON with exactly these keys: 'summary', 'insights', 'actions'.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-04-17',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json"
            )
        )
        
        import json
        report_data = json.loads(response.text)
        return {
            "summary": report_data.get("summary", "N/A"),
            "insights": report_data.get("insights", "N/A"),
            "actions": report_data.get("actions", "N/A")
        }
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

def send_restock_email(product_id, store_id, units):
    """
    Sends a restock alert via SMTP (Mailtrap or Gmail).
    """
    # Prefer Production Gmail if provided, fallback to Mailtrap Sandbox
    smtp_host = os.getenv("GMAIL_SMTP_HOST") or os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("GMAIL_SMTP_PORT") or os.getenv("SMTP_PORT") or 587)
    smtp_user = os.getenv("GMAIL_SMTP_USER") or os.getenv("SMTP_USER")
    smtp_pass = os.getenv("GMAIL_SMTP_PASS") or os.getenv("SMTP_PASS")
    
    from_email = os.getenv("ALERT_FROM_EMAIL", "alerts@retailmind.com")
    to_email = os.getenv("ALERT_TO_EMAIL", "manager@retailmind.com")

    if not all([smtp_host, smtp_user, smtp_pass]):
        print(f"SMTP Config Missing. SIMULATED EMAIL: Restock {units} units of {product_id} at Store {store_id}")
        return False

    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = f"CRITICAL RESTOCK ALERT: {product_id} at Store {store_id}"
    message["From"] = from_email
    message["To"] = to_email

    html_content = f"""
    <html>
    <body>
        <h2>Critical Restock Needed</h2>
        <p>Product <strong>{product_id}</strong> at Store <strong>{store_id}</strong> is understocked.</p>
        <p>Recommended restock quantity: <strong>~{units} units</strong></p>
        <hr/>
        <p><small>RetailMind Autonomous Agent Action</small></p>
    </body>
    </html>
    """
    message.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if "gmail" in smtp_host:
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_email, message.as_string())
        print(f"✓ SMTP Alert successfully sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ SMTP Error: {e}")
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
    message["From"] = from_email
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
                Forecast Accuracy: {metrics.get('forecastAccuracy', 0)}%
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
            if "gmail" in smtp_host:
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_email, message.as_string())
        print(f"✓ Executive Summary successfully sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Report Email Failed: {e}")
        return False
