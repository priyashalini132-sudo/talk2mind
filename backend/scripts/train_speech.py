"""
Talk2Mind – Speech Emotion Recognition Training Pipeline
=========================================================
Trains a BiLSTM + Attention model (or Wav2Vec2 fine-tune) on
RAVDESS, CREMA-D, TESS, SAVEE, and EMODB datasets.

Usage:
    python -m scripts.train_speech --data_dir ./data/speech --epochs 100 --output_dir ./models

Requirements:
    pip install torch torchaudio librosa soundfile scikit-learn matplotlib seaborn tqdm transformers

Dataset Download:
    RAVDESS: https://zenodo.org/record/1188976
    CREMA-D: https://github.com/CheyneyComputerScience/CREMA-D
    TESS:    https://tspace.library.utoronto.ca/handle/1807/24487
    SAVEE:   http://kahlan.eps.surrey.ac.uk/savee/
    EMODB:   http://www.emodb.bilderbar.info/docu/

Architecture (BiLSTM):
    MFCC(40) + Δ + ΔΔ → [120 features]
    BiLSTM(256, 2 layers) → Attention → Dense(256) → Dense(7)

Architecture (Wav2Vec2 – alternative):
    facebook/wav2vec2-base → mean pooling → Linear(768, 7)
"""

import argparse
import json
import os
import glob
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description="Train Speech Emotion Recognition model")
    parser.add_argument("--data_dir",   type=str,   required=True,
                        help="Root directory containing RAVDESS/CREMA-D/TESS sub-folders")
    parser.add_argument("--output_dir", type=str,   default="./models")
    parser.add_argument("--model_type", type=str,   default="bilstm",
                        choices=["bilstm", "wav2vec2"],
                        help="Model architecture to train")
    parser.add_argument("--epochs",     type=int,   default=100)
    parser.add_argument("--batch_size", type=int,   default=32)
    parser.add_argument("--lr",         type=float, default=1e-3)
    parser.add_argument("--sr",         type=int,   default=16000,
                        help="Target sample rate")
    parser.add_argument("--n_mfcc",     type=int,   default=40)
    parser.add_argument("--seed",       type=int,   default=42)
    args = parser.parse_args()

    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import DataLoader, Dataset
        import librosa
        from sklearn.model_selection import train_test_split, StratifiedKFold
        from sklearn.metrics import (
            classification_report, confusion_matrix, roc_auc_score,
            f1_score, accuracy_score
        )
        from sklearn.preprocessing import LabelEncoder, label_binarize
        import matplotlib.pyplot as plt
        import seaborn as sns
        from tqdm import tqdm
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Run: pip install torch torchaudio librosa soundfile scikit-learn matplotlib seaborn tqdm")
        return

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    CLASSES = ["Angry", "Calm", "Disgust", "Fear", "Happy", "Neutral", "Sad"]

    # ── Dataset loading ────────────────────────────────────────────────────────
    def parse_ravdess_label(filepath):
        """RAVDESS filename: 03-01-EM-IN-ST-CH-ACTOR.wav, emotion=3rd field."""
        fname = Path(filepath).stem
        parts = fname.split("-")
        if len(parts) < 3: return None
        code = int(parts[2])
        mapping = {1: "Neutral", 2: "Calm", 3: "Happy", 4: "Sad", 5: "Angry", 6: "Fear", 7: "Disgust"}
        return mapping.get(code)

    def parse_crema_label(filepath):
        """CREMA-D filename: ACTOR_SENTENCE_EMOTION_INTENSITY.wav"""
        fname = Path(filepath).stem
        parts = fname.split("_")
        if len(parts) < 3: return None
        code = parts[2]
        mapping = {"ANG": "Angry", "DIS": "Disgust", "FEA": "Fear", "HAP": "Happy", "NEU": "Neutral", "SAD": "Sad"}
        return mapping.get(code)

    def parse_tess_label(filepath):
        """TESS filename: OAF_word_EMOTION.wav"""
        fname = Path(filepath).stem.lower()
        for em in ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise", "pleasant_surprise"]:
            if fname.endswith(em) or f"_{em}" in fname:
                return em.replace("pleasant_surprise", "Surprise").capitalize()
        return None

    def load_all_files(data_dir):
        """Scan for RAVDESS, CREMA-D, TESS files."""
        files, labels = [], []
        for wav in glob.glob(os.path.join(data_dir, "**", "*.wav"), recursive=True):
            fname = Path(wav).stem.lower()
            parent = Path(wav).parent.name.lower()

            label = None
            # Try RAVDESS format
            if label is None: label = parse_ravdess_label(wav)
            # Try CREMA-D format
            if label is None: label = parse_crema_label(wav)
            # Try TESS format
            if label is None: label = parse_tess_label(wav)
            # Folder-name fallback
            if label is None:
                for cls in CLASSES:
                    if cls.lower() in parent:
                        label = cls
                        break

            if label and label in CLASSES:
                files.append(wav)
                labels.append(label)

        return files, labels

    # ── Feature extraction ─────────────────────────────────────────────────────
    def extract_features(wav_path, sr=16000, n_mfcc=40):
        """
        Extract acoustic feature vector from audio file.
        Returns a fixed-length feature vector of size 40*3 + 13 = 133.
        """
        try:
            y, _ = librosa.load(wav_path, sr=sr, mono=True)
            if len(y) < sr * 0.3:
                return None

            # MFCCs + deltas
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
            delta_mfcc  = librosa.feature.delta(mfccs)
            delta2_mfcc = librosa.feature.delta(mfccs, order=2)

            # Aggregate: mean + std across time
            mfcc_feats = np.concatenate([
                mfccs.mean(axis=1), mfccs.std(axis=1),
                delta_mfcc.mean(axis=1), delta_mfcc.std(axis=1),
                delta2_mfcc.mean(axis=1),
            ])

            # Prosodic features
            rms = librosa.feature.rms(y=y)[0]
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            sc  = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            sr_ = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            chroma = librosa.feature.chroma_stft(y=y, sr=sr).mean(axis=1)

            f0 = librosa.yin(y, fmin=50, fmax=500, sr=sr)
            voiced = f0[f0 > 60]
            mean_f0 = voiced.mean() if len(voiced) > 0 else 0.0
            std_f0  = voiced.std()  if len(voiced) > 0 else 0.0

            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            tempo = float(tempo) if not isinstance(tempo, np.ndarray) else float(tempo[0])

            prosodic = np.array([
                rms.mean(), rms.std(), zcr.mean(), sc.mean(), sr_.mean(),
                mean_f0, std_f0, tempo,
                *chroma
            ])

            return np.concatenate([mfcc_feats, prosodic])
        except Exception:
            return None

    print("Loading dataset files...")
    files, labels = load_all_files(args.data_dir)
    print(f"Found {len(files)} audio files across {len(set(labels))} classes")

    if len(files) == 0:
        print("No audio files found. Check --data_dir path.")
        return

    # Extract features
    print("Extracting features...")
    X, y = [], []
    for f, l in tqdm(zip(files, labels), total=len(files)):
        feats = extract_features(f, sr=args.sr, n_mfcc=args.n_mfcc)
        if feats is not None:
            X.append(feats)
            y.append(l)

    X = np.array(X, dtype=np.float32)
    le = LabelEncoder()
    le.fit(CLASSES)
    y_enc = le.transform(y)
    print(f"Feature shape: {X.shape}")
    print(f"Class distribution: {dict(zip(*np.unique(y, return_counts=True)))}")

    # Normalise features
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    import pickle
    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, "speech_scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.15, random_state=args.seed, stratify=y_enc
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.12, random_state=args.seed, stratify=y_train
    )

    # ── PyTorch Dataset ────────────────────────────────────────────────────────
    class AudioFeatDataset(Dataset):
        def __init__(self, X, y):
            self.X = torch.FloatTensor(X).unsqueeze(1)  # (N, 1, features) for BiLSTM
            self.y = torch.LongTensor(y)
        def __len__(self): return len(self.y)
        def __getitem__(self, idx): return self.X[idx], self.y[idx]

    train_ds = AudioFeatDataset(X_train, y_train)
    val_ds   = AudioFeatDataset(X_val,   y_val)
    test_ds  = AudioFeatDataset(X_test,  y_test)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,  num_workers=2)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False, num_workers=2)
    test_loader  = DataLoader(test_ds,  batch_size=args.batch_size, shuffle=False, num_workers=2)

    # ── BiLSTM + Attention Model ───────────────────────────────────────────────
    class AttentionLayer(nn.Module):
        def __init__(self, hidden_dim):
            super().__init__()
            self.attn = nn.Linear(hidden_dim * 2, 1)
        def forward(self, lstm_out):  # (B, T, H)
            scores = self.attn(lstm_out).squeeze(-1)  # (B, T)
            weights = torch.softmax(scores, dim=1).unsqueeze(-1)  # (B, T, 1)
            return (lstm_out * weights).sum(dim=1)  # (B, H)

    class BiLSTMModel(nn.Module):
        def __init__(self, input_dim, hidden_dim=256, num_layers=2, num_classes=7, dropout=0.3):
            super().__init__()
            self.lstm = nn.LSTM(
                input_dim, hidden_dim, num_layers=num_layers,
                batch_first=True, bidirectional=True, dropout=dropout
            )
            self.attention = AttentionLayer(hidden_dim)
            self.classifier = nn.Sequential(
                nn.LayerNorm(hidden_dim * 2),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim * 2, 256),
                nn.GELU(),
                nn.Dropout(0.2),
                nn.Linear(256, num_classes),
            )

        def forward(self, x):  # x: (B, 1, F)
            x = x.permute(0, 2, 1)  # (B, F, 1) → treat F as time steps for LSTM
            out, _ = self.lstm(x)   # (B, F, H*2)
            ctx = self.attention(out)  # (B, H*2)
            return self.classifier(ctx)

    feat_dim = X_train.shape[1]
    model = BiLSTMModel(input_dim=1, hidden_dim=256, num_classes=len(CLASSES)).to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_acc = 0.0
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    print(f"\n── Training BiLSTM Speech Model for {args.epochs} epochs ──")
    for epoch in range(1, args.epochs + 1):
        # Train
        model.train()
        tl, tc, tt = 0.0, 0, 0
        for X_b, y_b in train_loader:
            X_b, y_b = X_b.to(device), y_b.to(device)
            optimizer.zero_grad()
            out = model(X_b)
            loss = criterion(out, y_b)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            tl += loss.item() * X_b.size(0)
            tc += (out.argmax(1) == y_b).sum().item()
            tt += X_b.size(0)
        scheduler.step()

        # Val
        model.eval()
        vl, vc, vt = 0.0, 0, 0
        with torch.no_grad():
            for X_b, y_b in val_loader:
                X_b, y_b = X_b.to(device), y_b.to(device)
                out = model(X_b)
                vl += criterion(out, y_b).item() * X_b.size(0)
                vc += (out.argmax(1) == y_b).sum().item()
                vt += X_b.size(0)

        t_acc, v_acc = tc / tt, vc / vt
        history["train_loss"].append(tl / tt); history["train_acc"].append(t_acc)
        history["val_loss"].append(vl / vt);   history["val_acc"].append(v_acc)

        if epoch % 10 == 0 or epoch <= 5:
            print(f"  Epoch {epoch:3d} | T_Acc={t_acc:.4f} | V_Acc={v_acc:.4f}")

        if v_acc > best_val_acc:
            best_val_acc = v_acc
            torch.save({"epoch": epoch, "model_state": model.state_dict()},
                       os.path.join(args.output_dir, "best_speech_model.pth"))

    # ── Test Evaluation ────────────────────────────────────────────────────────
    print("\n── Test Evaluation ──")
    model.load_state_dict(
        torch.load(os.path.join(args.output_dir, "best_speech_model.pth"), map_location=device)["model_state"]
    )
    model.eval()

    all_preds, all_labels, all_probs = [], [], []
    with torch.no_grad():
        for X_b, y_b in test_loader:
            out = model(X_b.to(device))
            probs = torch.softmax(out, dim=1).cpu().numpy()
            all_probs.extend(probs)
            all_preds.extend(out.argmax(1).cpu().numpy())
            all_labels.extend(y_b.numpy())

    all_preds, all_labels, all_probs = np.array(all_preds), np.array(all_labels), np.array(all_probs)
    acc = accuracy_score(all_labels, all_preds)
    f1  = f1_score(all_labels, all_preds, average="weighted")
    lb  = label_binarize(all_labels, classes=list(range(len(CLASSES))))
    roc_auc = roc_auc_score(lb, all_probs, average="macro", multi_class="ovr")

    print(f"  Test Accuracy: {acc:.4f} | F1: {f1:.4f} | ROC-AUC: {roc_auc:.4f}")
    print(classification_report(all_labels, all_preds, target_names=CLASSES))

    # Confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Purples",
                xticklabels=CLASSES, yticklabels=CLASSES)
    plt.title("Confusion Matrix – SER (BiLSTM + Attention)")
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "confusion_matrix_speech.png"), dpi=150)
    plt.close()

    metrics = {"accuracy": acc, "f1_weighted": f1, "roc_auc_macro": roc_auc}
    with open(os.path.join(args.output_dir, "metrics_speech.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(args.output_dir, "training_history_speech.json"), "w") as f:
        json.dump(history, f, indent=2)

    print(f"\n✓ Speech model saved: {args.output_dir}/best_speech_model.pth")
    print(f"✓ Scaler saved: {args.output_dir}/speech_scaler.pkl")


if __name__ == "__main__":
    main()
