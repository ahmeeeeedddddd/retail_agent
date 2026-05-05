import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
        import google.generativeai as genai
        
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        prompt = f"""
        You are an AI Manager for an e-commerce retail store. Give a clean, concise 3-part report.
        Data: {total_products} total products, {critical_alerts} critical alerts, Forecast Accuracy: {forecast_acc}%.
        Clusters: {clusters_summary}.
        
        Format your response EXACTLY as 3 paragraphs separated by double newlines without bold text or asterisks:
        1. Daily Summary (1-2 sentences)
        2. Cluster Insights (1-2 sentences)
        3. Recommended Actions (1-2 sentences)
        """
        response = model.generate_content(prompt)
        text = response.text.split('\n\n')
        
        summary = text[0].replace("Daily Summary: ", "").replace("1. ", "").strip() if len(text) > 0 else "N/A"
        insights = text[1].replace("Cluster Insights: ", "").replace("2. ", "").strip() if len(text) > 1 else "N/A"
        actions = text[2].replace("Recommended Actions: ", "").replace("3. ", "").strip() if len(text) > 2 else "N/A"
        
        return {
            "summary": summary,
            "insights": insights,
            "actions": actions
        }
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {
            "summary": f"Failed to generate report: {e}",
            "insights": "Please check your API key or permissions.",
            "actions": "Try again later."
        }

def send_restock_email(product_id, store_id, units):
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
    if not SENDGRID_API_KEY:
        print(f"SIMULATED EMAIL: Restock {units} units of {product_id} at Store {store_id}")
        return False

    message = Mail(
        from_email='alerts@retailmind.com',
        to_emails='manager@retailmind.com',
        subject=f'CRITICAL RESTOCK ALERT: {product_id} at Store {store_id}',
        html_content=f'<strong>Product {product_id} at Store {store_id} is critically understocked.</strong><br/>Immediate restock of ~{units} units recommended based on SARIMA negative trend.'
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent with status {response.status_code}")
        return True
    except Exception as e:
        print(f"SendGrid API Error: {e}")
        return False

def calculate_action_score(svm_confidence, shap_score_sum, sarima_trend_percent):
    score = (svm_confidence * 0.4) + (shap_score_sum * 0.3) + (sarima_trend_percent * 0.3)
    return score
