"""
Talk2Mind – Facial Emotion Recognition Training Pipeline
=========================================================
Trains an EfficientNet-B0 model on FER2013 and/or AffectNet datasets
for 7-class facial emotion recognition.

Usage:
    python -m scripts.train_facial --dataset fer2013 --data_dir ./data/fer2013 --epochs 50 --output_dir ./models

Requirements:
    pip install torch torchvision timm tqdm scikit-learn matplotlib seaborn

Dataset Download:
    FER2013: kaggle competitions download -c challenges-in-representation-learning-facial-expression-recognition-challenge
    AffectNet: https://mohammadmahoor.com/affectnet/ (academic license required)

Architecture:
    EfficientNet-B0 (ImageNet pre-trained)
    → AdaptiveAvgPool2d
    → Dropout(0.3)
    → Linear(1280, 512)
    → GELU()
    → Linear(512, 7)
    → Softmax

Training Strategy:
    - Phase 1 (epochs 1–15): Freeze backbone, train only head (LR = 1e-3)
    - Phase 2 (epochs 16–30): Unfreeze last 2 blocks (LR = 1e-4)
    - Phase 3 (epochs 31–50): Fine-tune all layers (LR = 5e-5)
    - Label smoothing = 0.1, MixUp augmentation, class-weighted loss
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np


# ── Placeholder: only runs fully if torch and timm are installed ──────────────
def main():
    parser = argparse.ArgumentParser(description="Train Facial Emotion Recognition model")
    parser.add_argument("--dataset",    type=str,   default="fer2013",
                        choices=["fer2013", "affectnet"],
                        help="Dataset to use for training")
    parser.add_argument("--data_dir",   type=str,   required=True,
                        help="Path to dataset root directory")
    parser.add_argument("--output_dir", type=str,   default="./models",
                        help="Directory to save model weights")
    parser.add_argument("--epochs",     type=int,   default=50)
    parser.add_argument("--batch_size", type=int,   default=64)
    parser.add_argument("--lr",         type=float, default=1e-3)
    parser.add_argument("--img_size",   type=int,   default=224)
    parser.add_argument("--num_workers",type=int,   default=4)
    parser.add_argument("--seed",       type=int,   default=42)
    parser.add_argument("--resume",     type=str,   default=None,
                        help="Path to checkpoint to resume from")
    args = parser.parse_args()

    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
        from torchvision import transforms
        import timm
        from sklearn.metrics import (
            classification_report, confusion_matrix, roc_auc_score,
            f1_score, accuracy_score
        )
        from sklearn.preprocessing import label_binarize
        import matplotlib.pyplot as plt
        import seaborn as sns
        from PIL import Image
        from tqdm import tqdm
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Run: pip install torch torchvision timm scikit-learn matplotlib seaborn pillow tqdm")
        return

    # ── Reproducibility ────────────────────────────────────────────────────────
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    CLASSES = ["Angry", "Disgust", "Fear", "Happy", "Neutral", "Sad", "Surprise"]
    NUM_CLASSES = len(CLASSES)

    # ── Data Augmentation Pipelines ────────────────────────────────────────────
    train_transforms = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
        transforms.RandomPerspective(distortion_scale=0.2, p=0.3),
        transforms.RandomGrayscale(p=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.15)),
    ])

    val_transforms = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # ── Dataset ────────────────────────────────────────────────────────────────
    class FERDataset(Dataset):
        """
        Supports FER2013 CSV format and folder structure (ImageFolder compatible).
        FER2013 CSV: columns [emotion, pixels, Usage]
        """
        def __init__(self, data_dir, split="Training", transform=None):
            self.transform = transform
            self.samples = []

            csv_path = os.path.join(data_dir, "fer2013.csv")
            if os.path.exists(csv_path):
                import pandas as pd
                df = pd.read_csv(csv_path)
                df = df[df["Usage"] == split]
                for _, row in df.iterrows():
                    pixels = np.array(row["pixels"].split(), dtype=np.uint8).reshape(48, 48)
                    self.samples.append((pixels, int(row["emotion"])))
            else:
                # Folder structure: data_dir/train/Angry/img001.jpg
                split_map = {"Training": "train", "PrivateTest": "test", "PublicTest": "val"}
                folder = os.path.join(data_dir, split_map.get(split, "train"))
                for label_idx, cls in enumerate(CLASSES):
                    cls_folder = os.path.join(folder, cls)
                    if os.path.exists(cls_folder):
                        for fname in os.listdir(cls_folder):
                            if fname.lower().endswith((".jpg", ".png", ".jpeg")):
                                self.samples.append((os.path.join(cls_folder, fname), label_idx))

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            sample, label = self.samples[idx]
            if isinstance(sample, np.ndarray):
                img = Image.fromarray(sample).convert("RGB")
            else:
                img = Image.open(sample).convert("RGB")
            if self.transform:
                img = self.transform(img)
            return img, label

    # ── Model ──────────────────────────────────────────────────────────────────
    class FERModel(nn.Module):
        def __init__(self, num_classes=7, pretrained=True):
            super().__init__()
            self.backbone = timm.create_model(
                "efficientnet_b0", pretrained=pretrained, num_classes=0
            )
            feat_dim = self.backbone.num_features  # 1280 for EfficientNet-B0
            self.classifier = nn.Sequential(
                nn.Dropout(0.3),
                nn.Linear(feat_dim, 512),
                nn.GELU(),
                nn.Dropout(0.2),
                nn.Linear(512, num_classes),
            )

        def forward(self, x):
            feats = self.backbone(x)
            return self.classifier(feats)

        def freeze_backbone(self):
            for p in self.backbone.parameters():
                p.requires_grad = False

        def unfreeze_last_n_blocks(self, n=2):
            """Unfreeze the last n blocks of EfficientNet."""
            blocks = list(self.backbone.blocks)
            for block in blocks[-n:]:
                for p in block.parameters():
                    p.requires_grad = True

        def unfreeze_all(self):
            for p in self.parameters():
                p.requires_grad = True

    # ── Training Setup ─────────────────────────────────────────────────────────
    print("Loading datasets...")
    train_dataset = FERDataset(args.data_dir, "Training",    train_transforms)
    val_dataset   = FERDataset(args.data_dir, "PublicTest",  val_transforms)
    test_dataset  = FERDataset(args.data_dir, "PrivateTest", val_transforms)

    print(f"  Train: {len(train_dataset)} samples")
    print(f"  Val:   {len(val_dataset)} samples")
    print(f"  Test:  {len(test_dataset)} samples")

    # Compute class weights for imbalanced dataset
    class_counts = [0] * NUM_CLASSES
    for _, label in train_dataset.samples:
        class_counts[label] += 1
    class_weights = torch.FloatTensor([1.0 / c if c > 0 else 0 for c in class_counts])
    sample_weights = [class_weights[label] for _, label in train_dataset.samples]
    sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, sampler=sampler,
                               num_workers=args.num_workers, pin_memory=True)
    val_loader   = DataLoader(val_dataset,   batch_size=args.batch_size, shuffle=False,
                               num_workers=args.num_workers, pin_memory=True)
    test_loader  = DataLoader(test_dataset,  batch_size=args.batch_size, shuffle=False,
                               num_workers=args.num_workers, pin_memory=True)

    model = FERModel(num_classes=NUM_CLASSES).to(device)

    # Resume if checkpoint provided
    if args.resume:
        state = torch.load(args.resume, map_location=device)
        model.load_state_dict(state["model_state"])
        print(f"Resumed from checkpoint: {args.resume}")

    # Loss with label smoothing
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    os.makedirs(args.output_dir, exist_ok=True)
    best_val_acc = 0.0
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    def train_epoch(loader, optimizer):
        model.train()
        total_loss, correct, total = 0.0, 0, 0
        for imgs, labels in tqdm(loader, desc="  Train", leave=False):
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item() * imgs.size(0)
            preds = out.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += imgs.size(0)
        return total_loss / total, correct / total

    def eval_epoch(loader):
        model.eval()
        total_loss, correct, total = 0.0, 0, 0
        with torch.no_grad():
            for imgs, labels in tqdm(loader, desc="  Val", leave=False):
                imgs, labels = imgs.to(device), labels.to(device)
                out = model(imgs)
                loss = criterion(out, labels)
                total_loss += loss.item() * imgs.size(0)
                preds = out.argmax(dim=1)
                correct += (preds == labels).sum().item()
                total += imgs.size(0)
        return total_loss / total, correct / total

    # ── 3-Phase Training ───────────────────────────────────────────────────────
    print("\n── Phase 1: Training head only ──")
    model.freeze_backbone()
    opt1 = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-3)
    sched1 = optim.lr_scheduler.CosineAnnealingLR(opt1, T_max=15)

    for epoch in range(1, 16):
        t_loss, t_acc = train_epoch(train_loader, opt1)
        v_loss, v_acc = eval_epoch(val_loader)
        sched1.step()
        history["train_loss"].append(t_loss); history["train_acc"].append(t_acc)
        history["val_loss"].append(v_loss);   history["val_acc"].append(v_acc)
        print(f"  Epoch {epoch:2d} | T_Loss={t_loss:.4f} T_Acc={t_acc:.4f} | V_Loss={v_loss:.4f} V_Acc={v_acc:.4f}")
        if v_acc > best_val_acc:
            best_val_acc = v_acc
            torch.save({"epoch": epoch, "model_state": model.state_dict(), "val_acc": v_acc},
                       os.path.join(args.output_dir, "best_facial_model.pth"))

    print("\n── Phase 2: Unfreezing last 2 blocks ──")
    model.unfreeze_last_n_blocks(2)
    opt2 = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-4)
    sched2 = optim.lr_scheduler.CosineAnnealingLR(opt2, T_max=15)

    for epoch in range(16, 31):
        t_loss, t_acc = train_epoch(train_loader, opt2)
        v_loss, v_acc = eval_epoch(val_loader)
        sched2.step()
        history["train_loss"].append(t_loss); history["train_acc"].append(t_acc)
        history["val_loss"].append(v_loss);   history["val_acc"].append(v_acc)
        print(f"  Epoch {epoch:2d} | T_Loss={t_loss:.4f} T_Acc={t_acc:.4f} | V_Loss={v_loss:.4f} V_Acc={v_acc:.4f}")
        if v_acc > best_val_acc:
            best_val_acc = v_acc
            torch.save({"epoch": epoch, "model_state": model.state_dict(), "val_acc": v_acc},
                       os.path.join(args.output_dir, "best_facial_model.pth"))

    print("\n── Phase 3: Fine-tuning all layers ──")
    model.unfreeze_all()
    opt3 = optim.Adam(model.parameters(), lr=5e-5, weight_decay=1e-4)
    sched3 = optim.lr_scheduler.CosineAnnealingLR(opt3, T_max=20)

    for epoch in range(31, args.epochs + 1):
        t_loss, t_acc = train_epoch(train_loader, opt3)
        v_loss, v_acc = eval_epoch(val_loader)
        sched3.step()
        history["train_loss"].append(t_loss); history["train_acc"].append(t_acc)
        history["val_loss"].append(v_loss);   history["val_acc"].append(v_acc)
        print(f"  Epoch {epoch:2d} | T_Loss={t_loss:.4f} T_Acc={t_acc:.4f} | V_Loss={v_loss:.4f} V_Acc={v_acc:.4f}")
        if v_acc > best_val_acc:
            best_val_acc = v_acc
            torch.save({"epoch": epoch, "model_state": model.state_dict(), "val_acc": v_acc},
                       os.path.join(args.output_dir, "best_facial_model.pth"))

    # ── Test Evaluation ────────────────────────────────────────────────────────
    print("\n── Final Test Evaluation ──")
    best_state = torch.load(os.path.join(args.output_dir, "best_facial_model.pth"), map_location=device)
    model.load_state_dict(best_state["model_state"])
    model.eval()

    all_preds, all_labels, all_probs = [], [], []
    with torch.no_grad():
        for imgs, labels in test_loader:
            imgs = imgs.to(device)
            out = model(imgs)
            probs = torch.softmax(out, dim=1).cpu().numpy()
            preds = out.argmax(dim=1).cpu().numpy()
            all_probs.extend(probs)
            all_preds.extend(preds)
            all_labels.extend(labels.numpy())

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs  = np.array(all_probs)

    acc = accuracy_score(all_labels, all_preds)
    f1  = f1_score(all_labels, all_preds, average="weighted")
    lb  = label_binarize(all_labels, classes=list(range(NUM_CLASSES)))
    roc_auc = roc_auc_score(lb, all_probs, average="macro", multi_class="ovr")

    print(f"\n  Test Accuracy:  {acc:.4f}")
    print(f"  Test F1-Score:  {f1:.4f}")
    print(f"  ROC-AUC (macro): {roc_auc:.4f}")
    print("\n  Classification Report:")
    print(classification_report(all_labels, all_preds, target_names=CLASSES))

    # Save confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=CLASSES, yticklabels=CLASSES)
    plt.title("Confusion Matrix – FER (EfficientNet-B0)")
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "confusion_matrix_facial.png"), dpi=150)
    plt.close()

    # Save training history
    with open(os.path.join(args.output_dir, "training_history_facial.json"), "w") as f:
        json.dump(history, f, indent=2)

    metrics = {"accuracy": acc, "f1_weighted": f1, "roc_auc_macro": roc_auc,
               "best_val_acc": best_val_acc}
    with open(os.path.join(args.output_dir, "metrics_facial.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n✓ Model saved to: {args.output_dir}/best_facial_model.pth")
    print(f"✓ Confusion matrix saved.")
    print(f"✓ Metrics: {metrics}")


if __name__ == "__main__":
    main()
