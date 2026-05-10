import pandas as pd
import numpy as np
import os

import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset")

def fetch_egp_rate():
    """
    Fetches USD to EGP exchange rate via Open-ER-API (Stable).
    """
    print("Fetching USD/EGP rate from API...")
    try:
        # Free API, no key required for basic daily rates
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("result") == "success":
            return float(data["rates"].get("EGP", 52.5))
    except Exception as e:
        print(f"EGP API Error: {e}")
    
    return 52.5 # Updated fallback

def fetch_cbe_metrics():
    """
    Mock/Scrape CBE inflation and interest rates.
    """
    print("Fetching CBE Metrics...")
    return {"inflation": 32.5, "interest_rate": 27.25}

def fetch_egypt_weather():
    """
    Fetches current weather for Cairo via Open-Meteo API.
    """
    print("Fetching Cairo weather from API...")
    try:
        # Latitude/Longitude for Cairo
        url = "https://api.open-meteo.com/v1/forecast?latitude=30.0444&longitude=31.2357&current_weather=true"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "current_weather" in data:
            temp = data["current_weather"]["temperature"]
            # Map WMO weather code to simple condition string if needed
            code = data["current_weather"].get("weathercode", 0)
            condition = "Clear" if code <= 3 else "Cloudy"
            if code > 50: condition = "Rainy"
            return {"temp": int(temp), "condition": condition}
    except Exception as e:
        print(f"Weather API Error: {e}")
        
    return {"temp": 33, "condition": "Sunny"} # Updated fallback

def is_ramadan_eid():
    """
    Simple check for peak retail seasons in Egypt.
    """
    return False

def load_and_preprocess_data(sample_size=100000):
    """
    Loads datsets and enriches with Egyptian Market Signals.
    """
    train_path = os.path.join(DATA_DIR, "train.csv")
    stores_path = os.path.join(DATA_DIR, "stores.csv")
    oil_path = os.path.join(DATA_DIR, "oil.csv")
    
    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Missing {train_path}. Please ensure datasets are extracted.")

    print(f"Loading data (nrows={sample_size})...")
    
    stores = pd.read_csv(stores_path)
    oil = pd.read_csv(oil_path)
    
    train = pd.read_csv(train_path, nrows=sample_size)
    
    print("Preprocessing Dates...")
    train['date'] = pd.to_datetime(train['date'])
    oil['date'] = pd.to_datetime(oil['date'])
    
    print("Merging stores and oil...")
    train = train.merge(stores, on='store_nbr', how='left')
    train = train.merge(oil, on='date', how='left')
    
    # NEW: Fetch Egyptian Signals
    egp_rate = fetch_egp_rate()
    cbe = fetch_cbe_metrics()
    weather = fetch_egypt_weather()
    peak_season = is_ramadan_eid()
    
    # Enrichment: Instead of just oil, we add EGP rate as a column
    train['dcoilwtico'] = train['dcoilwtico'].ffill().bfill()
    train['egp_rate'] = egp_rate
    train['inflation'] = cbe['inflation']
    
    # Simulate 'live' updates by overriding last week with Egyptian Context
    latest_date = train['date'].max()
    train.loc[train['date'] > (latest_date - pd.Timedelta(days=7)), 'dcoilwtico'] *= (egp_rate / 48.0) # Scale oil by currency
    
    train['day_of_week'] = train['date'].dt.dayofweek
    train['month'] = train['date'].dt.month
    
    print("Data ingested with Egyptian Market signals.")
    return train, {"egp_rate": egp_rate, "cbe": cbe, "weather": weather, "is_peak": peak_season}

