import os
import sys
import asyncio
import logging
import pandas as pd
import numpy as np
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add the backend directory to sys.path for flexible execution
sys.path.append(os.path.dirname(__file__))

# Load environment variables from the same directory as this file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from step1_ingestion import load_and_preprocess_data
from step2_clustering import perform_clustering, predict_membership
from step3_classification import train_svm_classifier, predict_state, get_svm_signals
from step4_reasoning import run_shap_analysis, run_sarima_forecasting, AdvancedReasoningEngine
from step5_action import generate_manager_report
import uvicorn

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Smart Retail Demand & Anomaly Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

global_state = {
    "is_ready": False,
    "metrics": {
        "totalProducts": 0, "totalProductsChange": "--",
        "criticalAlerts": 0, "criticalAlertsChange": "--",
        "forecastAccuracy": 0, "forecastAccuracyChange": "--",
        "emailsSent": "0", "emailsSentChange": "--"
    },
    "shapImportance": {"labels": ["mean_sales", "std_sales", "promo_impact"], "values": [0.3, 0.2, 0.1]},
    "sarimaForecast": {"labels": [], "values": []},
    "clusters": [],
    "actionLog": [],
    "report": {},
    "data_cache": None,
    "svm_model": None,
    "scaler": None,
    # Phase 2 Advanced State
    "centroids": None,
    "cluster_shap_means": {},
    "reasoning_engine": AdvancedReasoningEngine(),
    "drift_signals": {"svm_gap_history": [], "centroid_movement": 0.0},
    "zone_shap_reliability": [],
    "last_outcome": "Steady",
    "react_telemetry": {
        "score": 0.0, "reliability": 0.0, "path": "Initializing", "action": "Please wait...",
        "s_severity": 0, "mu": 0.0, "gap": 0.0, "arima_trend": 0.0
    },
    "live_oil_price": 75.0,
    "egypt_telemetry": {
        "egp_rate": 52.5,
        "cbe": {"inflation": 32.5, "interest_rate": 27.25},
        "weather": {"temp": 33, "condition": "Sunny"},
        "is_peak": False
    },
    "agent_thoughts": "initializing..."
}


@app.on_event("startup")
async def startup_event():
    async def continuous_scraper():
        from step1_ingestion import fetch_egp_rate, fetch_cbe_metrics, fetch_egypt_weather
        while True:
            await asyncio.sleep(20)  # Poll every 20 secs for market metrics
            try:
                global_state["egypt_telemetry"]["egp_rate"] = fetch_egp_rate()
                global_state["egypt_telemetry"]["cbe"] = fetch_cbe_metrics()
                global_state["egypt_telemetry"]["weather"] = fetch_egypt_weather()
            except Exception:
                pass
                
    asyncio.create_task(run_full_pipeline())
    asyncio.create_task(continuous_scraper())


async def run_full_pipeline():
    while True:
        logging.info("Starting ADVANCED pipeline execution (Training Cycle)...")
        try:
            df, egypt_signals = load_and_preprocess_data(sample_size=100000) 
            global_state["data_cache"] = df
            global_state["egypt_telemetry"] = egypt_signals

            # --- TRAINING CYCLE (Offline) ---
            clustered_df, scaler_c, centroids_c = perform_clustering(df)
            global_state["scaler"] = scaler_c
            global_state["centroids"] = centroids_c
            
            svm_model, acc = train_svm_classifier(clustered_df, scaler_c)
            global_state["svm_model"] = svm_model
            
            features = ['mean_sales', 'std_sales', 'promo_impact']
            X_train_scaled = scaler_c.transform(clustered_df[features].values)
            
            # Calculate cluster-mean SHAP vectors for Implicit RAG
            print("Calculating Experience Store (SHAP Vectors)...")
            sample_size = min(30, len(X_train_scaled))

            X_experience = X_train_scaled[:sample_size]
            # Store background for Live Cycle Zone 4 stability
            global_state["reasoning_engine"].shap_background = X_experience
            shap_experience = run_shap_analysis(svm_model, X_experience, return_raw=True)
            
            # -- RAG INDEXING ---
            labels_experience = clustered_df['cluster_state'].values[:sample_size]
            global_state["reasoning_engine"].build_explicit_rag(X_experience, shap_experience, labels_experience)
            
            # Calculate Cluster Means for Implicit RAG
            for lbl in ['Normal', 'At-Risk', 'Critical']:
                label_mask = np.array([lbl == x for x in labels_experience])
                if any(label_mask) and len(label_mask) == shap_experience.shape[0]:
                    global_state["cluster_shap_means"][lbl] = np.mean(shap_experience[label_mask], axis=0)
                else:
                    global_state["cluster_shap_means"][lbl] = np.array([0.1, 0.1, 0.1])

            # --- LIVE PREDICTION CYCLE (Online) ---
            # Rotate through unique product families so Zone 6 shows variety
            logging.info("Switching to LIVE PREDICTION CYCLE...")
            unique_families = clustered_df['family'].unique()
            cycle_idx = len(global_state["actionLog"]) % len(unique_families)
            chosen_family = unique_families[cycle_idx]
            family_rows = clustered_df[clustered_df['family'] == chosen_family]
            target_sample = family_rows.iloc[0:1]  # Take first row of that family
            logging.info(f"[Live Cycle] Analyzing family: {chosen_family} ({cycle_idx+1}/{len(unique_families)})")
            X_new_scaled = scaler_c.transform(target_sample[features].values)
            
            mu, pred_cluster = predict_membership(X_new_scaled, centroids_c)
            pred_state, confidence, gap = get_svm_signals(svm_model, X_new_scaled)
            # Dynamic Forecast: Analyze current family from RAW df (ensures 'date' column is present)
            forecast_df = df[df['family'] == chosen_family]
            forecast_vals, drift_sarima = run_sarima_forecasting(forecast_df, days=30)
            trend = np.mean(np.diff(forecast_vals))
            
            target_mean_shap = global_state["cluster_shap_means"].get(pred_state, np.array([0.1, 0.2, 0.3]))
            
            # --- GRADIENT SEVERITY CALCULATION ---
            base_s = 2.0 if pred_state=='Critical' else 1.0 if pred_state=='At-Risk' else 0.0
            # If Normal, granular is 0.0 to 0.4. If At-Risk/Critical, granular is Base to Base+0.9
            if pred_state == 'Normal':
                granular_severity = (1.0 - confidence) * 0.4
            else:
                granular_severity = base_s + (confidence * 0.95)
            granular_severity = round(float(granular_severity), 2)
            
            # Pass captured background for diagnostic stability (resolves Zone 4 identical bars)
            current_shap = run_shap_analysis(
                svm_model, 
                X_new_scaled, 
                background_data=global_state["reasoning_engine"].shap_background
            )
            
            react_result = global_state["reasoning_engine"].react_loop(
                X_new_scaled[0], current_shap, 
                granular_severity,
                gap, mu[0], trend, target_mean_shap,
                egypt_meta=global_state["egypt_telemetry"]
            )
            
            # 3. ACT: Execute based on path
            global_state["react_telemetry"] = react_result
            global_state["agent_thoughts"] = react_result.get('thoughts', 'Steady state observed.')
            action_path = react_result.get('path', 'Monitor')
            best_action = react_result.get('action', 'No Action')
            
            # Map dominant feature for transparency
            dom_idx = react_result.get('dominant_feature_idx', 0)
            dom_feature = features[dom_idx] if dom_idx < len(features) else "None"
            react_result['dominant_feature'] = dom_feature

            import datetime
            live_time = datetime.datetime.now().strftime('%I:%M:%S %p')
            global_state["actionLog"].append({
                "timestamp": live_time,
                "product": str(target_sample['family'].values[0]),
                "path": action_path,
                "action": best_action,
                "dominant_feature": dom_feature,
                "shap_values": [round(float(x), 4) for x in current_shap] if isinstance(current_shap, np.ndarray) else [0,0,0],
                "shap_feature_names": features,
                "weights": react_result.get('weights', {}),
                "rag_consensus": react_result.get('rag_consensus', 0),
                "rag_similarity": react_result.get('rag_similarity', 0),
                "score": react_result.get('score', 0.5),
                "telemetry": react_result,
                "thoughts": global_state["agent_thoughts"]
            })

            # Trigger SMTP Email Alert for all Actions
            from step5_action import send_action_email
            send_action_email(
                product_id=str(target_sample['family'].values[0]),
                store_id=str(target_sample['store_nbr'].values[0]),
                units=50,
                action=best_action,
                context=react_result
            )

            # --- DUAL-SIGNAL DRIFT DETECTION ---
            # Signal 1: SVM Gap Decay
            global_state["drift_signals"]["svm_gap_history"].append(gap)
            if len(global_state["drift_signals"]["svm_gap_history"]) > 7:
                global_state["drift_signals"]["svm_gap_history"].pop(0)
            gap_ma = np.mean(global_state["drift_signals"]["svm_gap_history"])

            # Signal 2: SHAP Magnitude Collapse
            dom_shap_magnitude = float(np.max(np.abs(current_shap))) if isinstance(current_shap, np.ndarray) else 0.1
            if "shap_magnitude_history" not in global_state["drift_signals"]:
                global_state["drift_signals"]["shap_magnitude_history"] = []
            global_state["drift_signals"]["shap_magnitude_history"].append(dom_shap_magnitude)
            if len(global_state["drift_signals"]["shap_magnitude_history"]) > 7:
                global_state["drift_signals"]["shap_magnitude_history"].pop(0)
            shap_ma = np.mean(global_state["drift_signals"]["shap_magnitude_history"])

            # Drift condition: SVM certainty decayed OR SHAP explanations collapsed
            svm_drift = len(global_state["drift_signals"]["svm_gap_history"]) >= 7 and gap_ma < 0.15
            shap_drift = len(global_state["drift_signals"]["shap_magnitude_history"]) >= 7 and shap_ma < 0.02
            if svm_drift or shap_drift:
                drift_reason = "SVM Gap" if svm_drift else "SHAP Collapse"
                logging.warning(f"[ARL] Drift detected via {drift_reason} (SVM_MA={round(gap_ma,3)}, SHAP_MA={round(shap_ma,4)}). Re-clustering will trigger on next cycle.")
                global_state["drift_signals"]["svm_gap_history"].clear()
                global_state["drift_signals"]["shap_magnitude_history"].clear()
            
            # Populate monitoring zones
            num_products = int(len(clustered_df))
            critical_alerts = int(len(clustered_df[clustered_df['cluster_state'] == 'Critical']))
            
            global_state["metrics"] = {
                "totalProducts": num_products,
                "totalProductsChange": "Zone 1: Healthy",
                "criticalAlerts": critical_alerts,
                "criticalAlertsChange": f"MA Gap: {round(gap_ma, 2)}",
                "forecastAccuracy": round(float(acc)*100, 1),
                "forecastAccuracyChange": f"Path: {action_path[:10]}...",
                "emailsSent": str(global_state.get("_emails_total", 0)),
                "emailsSentChange": "SMTP Enabled"
            }
            
            # SHAP: use real values if non-zero, otherwise use cluster mean approx
            shap_vals = [float(x) for x in current_shap][:len(features)] if isinstance(current_shap, np.ndarray) else None
            if not shap_vals or max(abs(v) for v in shap_vals) < 0.001:
                # Fallback to cluster mean distances as proxy for importance
                cluster_mean = global_state["cluster_shap_means"].get(pred_state, np.array([0.35, 0.25, 0.15]))
                shap_vals = [round(float(x), 4) for x in cluster_mean[:len(features)]]
                logging.warning(f"[SHAP] KernelSHAP near-zero — using cluster mean proxy: {shap_vals}")
            global_state["shapImportance"] = {"labels": features, "values": shap_vals}
            global_state["sarimaForecast"] = { "labels": [str(i) for i in range(1, 31)], "values": [float(x) for x in forecast_vals] }
            
            global_state["clusters"] = []
            for _, row in clustered_df.sample(min(100, len(clustered_df))).iterrows():
                global_state["clusters"].append({"x": float(row['mean_sales']), "y": float(row['std_sales']), "status": str(row['cluster_state'])})

            # 4. Integrate Gemini Summary (Quota Optimization: Every 3 cycles or on Critical)
            cycle_count = global_state.get("_cycle_count", 0) + 1
            global_state["_cycle_count"] = cycle_count
            
            should_report = (cycle_count % 3 == 0) or ("High-Priority" in best_action) or ("Audit" in best_action)
            
            if should_report:
                clusters_summary = f"{len([c for c in clustered_df['cluster_state'].unique() if c != 'Stable'])} dynamic clusters detected."
                report = generate_manager_report(
                    total_products=len(df),
                    critical_alerts=global_state["metrics"]["criticalAlerts"],
                    forecast_acc=global_state["metrics"]["forecastAccuracy"],
                    clusters_summary=clusters_summary
                )
                global_state["reports_cache"] = report
                
                # --- EMAIL REPORTING ---
                from step5_action import send_executive_summary_email
                email_ok = send_executive_summary_email(report, global_state["metrics"])
                if email_ok:
                    global_state["_emails_total"] = global_state.get("_emails_total", 0) + 1
            else:
                logging.info(f"Reporting skipped for cycle {cycle_count} to conserve quota.")

            global_state["is_ready"] = True
            logging.info("Training Cycle Complete. Reporting live data...")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logging.error(f"Pipeline Failed: {e}")
            
        await asyncio.sleep(15) # Sped up from 5 minutes for dynamic visual dashboard demo

@app.get("/")
def read_root():
    return {"status": "running", "pipeline_ready": global_state["is_ready"]}

@app.get("/api/dashboard_data")
def get_dashboard_data():
    if not global_state["is_ready"]:
        return {"error": "Pipeline assembling data, please try again in 30 seconds."}
    
    return {
        "metrics": global_state["metrics"],
        "shapImportance": global_state["shapImportance"],
        "sarimaForecast": global_state["sarimaForecast"],
        "clusters": global_state["clusters"],
        "actionLog": global_state["actionLog"],
        # Advanced Zones Meta
        "telemetry": global_state["react_telemetry"],
        "outcome": global_state["last_outcome"],
        "live_oil_price": global_state["live_oil_price"],
        "egypt": global_state["egypt_telemetry"],
        "thoughts": global_state["agent_thoughts"],
        "report": global_state.get("reports_cache", {})
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=True)
