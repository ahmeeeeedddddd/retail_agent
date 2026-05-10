import pandas as pd
import numpy as np
import skfuzzy as fuzz
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

def perform_clustering(df):
    """
    Takes preprocessed DataFrame from Step 1.
    Groups by store_nbr and family to extract features.
    Applies DBSCAN then Fuzzy C-Means (FCM).
    """
    if df.empty:
        return pd.DataFrame()

    print("Extracting features for clustering...")
    # Feature Engineering for clustering
    # Group by product family and store
    agg_df = df.groupby(['store_nbr', 'family']).agg(
        total_sales=('sales', 'sum'),
        mean_sales=('sales', 'mean'),
        std_sales=('sales', 'std'),
        promo_impact=('onpromotion', 'sum')
    ).reset_index()
    
    # Fill NaN from std calculation
    agg_df['std_sales'] = agg_df['std_sales'].fillna(0)
    
    # Select features for clustering
    features = ['mean_sales', 'std_sales', 'promo_impact']
    X = agg_df[features].values
    
    # Scale Data
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print("Running DBSCAN to identify outliers...")
    # 1. DBSCAN
    db = DBSCAN(eps=1.5, min_samples=3).fit(X_scaled)
    # Exclude noise (-1)
    core_mask = db.labels_ != -1
    
    # If too much noise, we gracefully fallback and include all for FCM.
    if sum(core_mask) < 20: 
        core_mask = np.ones(len(X_scaled), dtype=bool)

    X_core = X_scaled[core_mask]
    
    print("Running Fuzzy C-Means...")
    # 2. Fuzzy C-Means (FCM)
    # FCM in scikit-fuzzy requires transpose of data
    # n_centers = 4 (Stable, Seasonal, Volatile, Critical)
    cntr, u, u0, d, jm, p, fpc = fuzz.cluster.cmeans(
        X_core.T, c=4, m=2, error=0.005, maxiter=1000, init=None
    )
    
    # Cluster labels based on highest membership
    cluster_membership = np.argmax(u, axis=0)
    
    # Map raw numeric clusters to our semantic labels based on cluster centers' behavior.
    # Center shape: (4, 3) [mean_sales, std_sales, promo_impact]
    # Simple heuristic to assign semantic meaning:
    # Highest std_sales -> Volatile
    # Highest mean_sales & low std -> Stable
    # Low sales & promotion-dependent -> Seasonal (or vice versa)
    # We will just map them statically for this prototype to 0: Stable, 1: Seasonal, 2: Volatile, 3: Critical
    label_map = {0: 'Stable', 1: 'Seasonal', 2: 'Volatile', 3: 'Critical'}
    
    semantic_labels = [label_map.get(lbl, 'Stable') for lbl in cluster_membership]
    
    # Reconstruct dataframe with labels
    core_df = agg_df[core_mask].copy()
    core_df['cluster_state'] = semantic_labels
    
    # Return everything needed for the Training Cycle
    return core_df, scaler, cntr

def predict_membership(X_new_scaled, centroids):
    """
    Live Cycle: Serves new arrivals without re-running FCM.
    Calculates geometric membership (mu) to saved centroids.
    """
    # fuzz.cluster.cdist calculates distances from points to centroids
    # X_new_scaled shape: (n_samples, 3)
    # centroids shape: (4, 3)
    from scipy.spatial.distance import cdist
    try:
        d = cdist(X_new_scaled, centroids, metric='euclidean')

        # Calculate membership u based on distances d
        # Formula: u = 1 / (d^(2/(m-1)) * sum(1/d^(2/(m-1))))
        m = 2.0
        d_exponent = 2.0 / (m - 1)
        
        # Handle zero distances to avoid division by zero
        d = np.fmax(d, np.finfo(np.float64).eps)
        
        inv_d = 1.0 / (d ** d_exponent)
        u = inv_d / inv_d.sum(axis=1, keepdims=True)
        
        # μ (membership) is the max membership value for each sample
        mu = np.max(u, axis=1)
        predicted_cluster = np.argmax(u, axis=1)
        
        return mu, predicted_cluster
    except Exception as e:
        print(f"Membership prediction error: {e}")
        return np.array([0.5]), np.array([0])


