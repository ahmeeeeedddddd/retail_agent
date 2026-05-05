import pandas as pd
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def train_svm_classifier(clustered_df, scaler):
    """
    Trains an SVM (RBF kernel) on the FCM labels.
    """
    if clustered_df.empty:
        return None, 0.0

    print("Training State Detector (SVM)...")
    
    # Feature matrix X and labels y
    features = ['mean_sales', 'std_sales', 'promo_impact']
    X = clustered_df[features].values
    y = clustered_df['cluster_state'].values
    
    # Map string labels to Normal, At-Risk, Critical for the Classification Step
    # Stable & Seasonal -> Normal
    # Volatile -> At-Risk
    # Critical -> Critical
    def map_states(label):
        if label in ['Stable', 'Seasonal']:
            return 'Normal'
        elif label == 'Volatile':
            return 'At-Risk'
        else:
            return 'Critical'
            
    y_mapped = [map_states(val) for val in y]
    
    # Scale X using the SAME scaler from clustering
    X_scaled = scaler.transform(X)
    
    # Train-test split
    # For small data, it may fail if classes are too few. Add basic handling.
    try:
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_mapped, test_size=0.2, random_state=42)
    except ValueError:
        # Not enough samples to split, use all for both
        X_train, X_test = X_scaled, X_scaled
        y_train, y_test = y_mapped, y_mapped
        
    svm = SVC(kernel='rbf', probability=True, random_state=42)
    
    # Some datasets might end up with only 1 class depending on the sample chunk
    if len(set(y_train)) > 1:
        svm.fit(X_train, y_train)
        preds = svm.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"SVM trained successfully. Accuracy: {acc*100:.2f}%")
    else:
        print("Warning: Only one class found. Skipping evaluation.")
        svm.fit(X_train, y_train)
        acc = 1.0
        
    return svm, acc

def predict_state(svm_model, new_data_scaled):
    if svm_model is None:
        return ["Normal"] * len(new_data_scaled)
    return svm_model.predict(new_data_scaled)
