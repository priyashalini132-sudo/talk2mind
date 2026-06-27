import sys
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, accuracy_score
from sklearn.preprocessing import label_binarize

# Adjust path to find app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

def train_facial_model():
    print("\n==============================================")
    print("Training Facial Emotion Recognition Model...")
    print("==============================================")
    
    # 7 Classes: Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral
    classes = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]
    
    # Generate synthetic features representing FER2013/AffectNet feature statistics
    # Features: aspect_ratio, mean_intensity, std_intensity, eye_ratio, mouth_ratio
    np.random.seed(42)
    num_samples = 2000
    
    X_list = []
    y_list = []
    
    # Generate feature distributions per class to simulate real emotion boundaries
    for class_idx, label in enumerate(classes):
        samples_per_class = num_samples // len(classes)
        
        # Default baseline
        aspect = np.random.normal(1.0, 0.05, samples_per_class)
        mean = np.random.normal(0.5, 0.1, samples_per_class)
        std = np.random.normal(0.2, 0.05, samples_per_class)
        
        if label == "Happy":
            # High mouth aspect (smile)
            eye = np.random.normal(1.0, 0.03, samples_per_class)
            mouth = np.random.normal(1.15, 0.05, samples_per_class)
        elif label == "Surprise":
            # Extremely high mouth aspect (mouth open) and high intensity std
            eye = np.random.normal(1.05, 0.03, samples_per_class)
            mouth = np.random.normal(1.3, 0.08, samples_per_class)
            std = np.random.normal(0.28, 0.05, samples_per_class)
        elif label == "Angry":
            # Low eye ratio (squinted eyes)
            eye = np.random.normal(0.92, 0.03, samples_per_class)
            mouth = np.random.normal(0.98, 0.04, samples_per_class)
        elif label == "Sad":
            # Low mouth ratio
            eye = np.random.normal(0.97, 0.04, samples_per_class)
            mouth = np.random.normal(0.92, 0.04, samples_per_class)
        elif label == "Fear":
            # Squinted eyes and higher standard deviation (tensed muscles)
            eye = np.random.normal(0.95, 0.04, samples_per_class)
            mouth = np.random.normal(1.05, 0.05, samples_per_class)
            std = np.random.normal(0.24, 0.04, samples_per_class)
        elif label == "Disgust":
            # High eye squint, low mouth opening
            eye = np.random.normal(0.93, 0.03, samples_per_class)
            mouth = np.random.normal(0.95, 0.03, samples_per_class)
        else: # Neutral
            eye = np.random.normal(1.0, 0.02, samples_per_class)
            mouth = np.random.normal(1.0, 0.02, samples_per_class)
            
        features = np.column_stack([aspect, mean, std, eye, mouth])
        X_list.append(features)
        y_list.append(np.full(samples_per_class, class_idx))
        
    X = np.vstack(X_list)
    y = np.concatenate(y_list)
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Fit Random Forest classifier
    model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    model.fit(X_train, y_train)
    
    # Cross Validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=5)
    print(f"5-Fold Cross-Validation Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    # Evaluate
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    print(f"Test Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=classes))
    
    # Calculate Multi-Class ROC-AUC
    y_test_bin = label_binarize(y_test, classes=range(len(classes)))
    auc = roc_auc_score(y_test_bin, y_pred_proba, multi_class="ovr")
    print(f"ROC-AUC Score (One-vs-Rest): {auc:.4f}")
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Save Model
    model_path = os.path.join(settings.MODEL_DIR, "facial_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"\nFacial model successfully saved to: {model_path}")

def train_speech_model():
    print("\n==============================================")
    print("Training Speech Emotion Recognition Model...")
    print("==============================================")
    
    # 8 Classes: Angry, Calm, Disgust, Fear, Happy, Neutral, Sad, Surprise (RAVDESS format)
    classes = ["Angry", "Calm", "Disgust", "Fear", "Happy", "Neutral", "Sad", "Surprise"]
    
    # Generate 18 features: rms, zcr, pitch, tempo, 13 mfccs
    np.random.seed(42)
    num_samples = 2400
    
    X_list = []
    y_list = []
    
    # Define emotional profile features (mean shifts) to make learning realistic
    for class_idx, label in enumerate(classes):
        samples_per_class = num_samples // len(classes)
        
        # Base features (18 dimensions)
        feats = np.random.normal(loc=0.0, scale=0.5, size=(samples_per_class, 18))
        
        # Modify specific acoustics (rms: index 0, zcr: index 1, pitch: index 2, tempo: index 3)
        if label == "Angry":
            feats[:, 0] += 0.8  # Very loud
            feats[:, 1] += 0.4  # High zero crossing rate (sharp voice)
            feats[:, 2] += 0.6  # High pitch
            feats[:, 3] += 0.8  # Rapid tempo
        elif label == "Happy":
            feats[:, 0] += 0.4  # Loud
            feats[:, 2] += 0.5  # High pitch
            feats[:, 3] += 0.6  # Fast tempo
        elif label == "Sad":
            feats[:, 0] -= 0.6  # Very quiet
            feats[:, 2] -= 0.4  # Low pitch
            feats[:, 3] -= 0.7  # Slow tempo
        elif label == "Calm":
            feats[:, 0] -= 0.4  # Quiet
            feats[:, 2] -= 0.2  # Normal low pitch
            feats[:, 3] -= 0.4  # Slow tempo
        elif label == "Fear":
            feats[:, 0] -= 0.1  # Medium-low loudness
            feats[:, 1] += 0.5  # Jittery (high ZCR)
            feats[:, 2] += 0.8  # High pitch (screechy/trembling)
            feats[:, 3] += 0.5  # Fast tempo
        elif label == "Surprise":
            feats[:, 0] += 0.5  # High sudden energy
            feats[:, 2] += 0.7  # High pitch shift
            feats[:, 3] += 0.2  # Moderate tempo
            
        X_list.append(feats)
        y_list.append(np.full(samples_per_class, class_idx))
        
    X = np.vstack(X_list)
    y = np.concatenate(y_list)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # MLP neural network classifier (simulating deep speech architecture)
    model = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=200, random_state=42)
    model.fit(X_train, y_train)
    
    # Cross Validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=5)
    print(f"5-Fold Cross-Validation Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    # Evaluate
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    print(f"Test Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=classes))
    
    # Calculate Multi-Class ROC-AUC
    y_test_bin = label_binarize(y_test, classes=range(len(classes)))
    auc = roc_auc_score(y_test_bin, y_pred_proba, multi_class="ovr")
    print(f"ROC-AUC Score (One-vs-Rest): {auc:.4f}")
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Save Model
    model_path = os.path.join(settings.MODEL_DIR, "speech_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"\nSpeech model successfully saved to: {model_path}")

if __name__ == "__main__":
    # Ensure models dir exists
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    train_facial_model()
    train_speech_model()
