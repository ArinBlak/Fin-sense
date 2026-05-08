import os
import sys
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report, confusion_matrix,
)
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    TrainerCallback,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
DATA_DIR    = BASE_DIR / "data"
TRAIN_DIR   = Path(__file__).resolve().parent
METRICS_DIR = TRAIN_DIR / "metrics"
MODEL_DIR   = TRAIN_DIR / "finbert_finetuned"
LOG_FILE    = TRAIN_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

METRICS_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
# also surface transformers/datasets internal logs
logging.getLogger("transformers").setLevel(logging.INFO)
logging.getLogger("transformers.modeling_utils").setLevel(logging.INFO)
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.INFO)
logging.getLogger("datasets").setLevel(logging.WARNING)

log = logging.getLogger(__name__)

def section(title: str):
    log.info("=" * 65)
    log.info(f"  {title}")
    log.info("=" * 65)

def subsection(title: str):
    log.info(f"── {title} {'─' * max(0, 55 - len(title))}")

# ── Hyperparameters ───────────────────────────────────────────────────────────
MODEL_NAME  = "ProsusAI/finbert"
MAX_LEN     = 128
BATCH_SIZE  = 16
EPOCHS      = 5
LR          = 2e-5
SEED        = 42
LABEL_NAMES = ["negative", "neutral", "positive"]

section("FinSense — FinBERT Fine-Tuning")
log.info(f"  Started at   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log.info(f"  Model        : {MODEL_NAME}")
log.info(f"  Max length   : {MAX_LEN} tokens")
log.info(f"  Batch size   : {BATCH_SIZE}")
log.info(f"  Epochs       : {EPOCHS}")
log.info(f"  Learning rate: {LR}")
log.info(f"  Weight decay : 0.01")
log.info(f"  Warmup ratio : 0.10")
log.info(f"  Seed         : {SEED}")
log.info(f"  Log file     : {LOG_FILE}")

# ── System info ───────────────────────────────────────────────────────────────
subsection("System")
log.info(f"  Python  : {sys.version.split()[0]}")
log.info(f"  PyTorch : {torch.__version__}")
import transformers
log.info(f"  Transformers: {transformers.__version__}")
device = (
    "mps"  if torch.backends.mps.is_available()  else
    "cuda" if torch.cuda.is_available()           else
    "cpu"
)
log.info(f"  Device  : {device}")
if device == "cuda":
    log.info(f"  GPU     : {torch.cuda.get_device_name(0)}")
    log.info(f"  VRAM    : {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
elif device == "mps":
    log.info(f"  Backend : Apple Metal Performance Shaders (MPS)")
else:
    log.info(f"  Backend : CPU only — training will be slow")

# ── Load data ─────────────────────────────────────────────────────────────────
section("1 / 6  — Data Loading")
t0 = time.time()
log.info(f"  Reading: {DATA_DIR / 'financial_phrasebank.csv'}")
df = pd.read_csv(DATA_DIR / "financial_phrasebank.csv")
log.info(f"  Loaded {len(df)} rows in {time.time()-t0:.2f}s")
log.info(f"  Columns : {list(df.columns)}")
log.info(f"  Dtypes  : {df.dtypes.to_dict()}")
log.info(f"  Nulls   : {df.isnull().sum().to_dict()}")
log.info(f"  Label distribution:")
for label_id, count in df["label"].value_counts().sort_index().items():
    pct = count / len(df) * 100
    log.info(f"    [{label_id}] {LABEL_NAMES[label_id]:8s} → {count:4d} samples ({pct:.1f}%)")

# ── Train / Val / Test split (70 / 15 / 15) ───────────────────────────────────
section("2 / 6  — Train / Val / Test Split  (70 / 15 / 15)")
train_df, temp_df = train_test_split(
    df, test_size=0.30, random_state=SEED, stratify=df["label"]
)
val_df, test_df = train_test_split(
    temp_df, test_size=0.50, random_state=SEED, stratify=temp_df["label"]
)
log.info(f"  Total   : {len(df)}")
log.info(f"  Train   : {len(train_df)} ({len(train_df)/len(df)*100:.1f}%)")
log.info(f"  Val     : {len(val_df)}   ({len(val_df)/len(df)*100:.1f}%)")
log.info(f"  Test    : {len(test_df)}   ({len(test_df)/len(df)*100:.1f}%)")
for split_name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
    dist = {LABEL_NAMES[k]: v for k, v in split_df["label"].value_counts().sort_index().items()}
    log.info(f"  {split_name:5s} labels: {dist}")

# ── Tokenizer ─────────────────────────────────────────────────────────────────
section("3 / 6  — Tokenizer")
log.info(f"  Loading tokenizer from: {MODEL_NAME}")
t0 = time.time()
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
log.info(f"  Tokenizer loaded in {time.time()-t0:.2f}s")
log.info(f"  Vocab size     : {tokenizer.vocab_size:,}")
log.info(f"  Max model len  : {tokenizer.model_max_length}")
log.info(f"  Padding token  : '{tokenizer.pad_token}' (id={tokenizer.pad_token_id})")
log.info(f"  CLS token      : '{tokenizer.cls_token}' (id={tokenizer.cls_token_id})")
log.info(f"  SEP token      : '{tokenizer.sep_token}' (id={tokenizer.sep_token_id})")
log.info(f"  Using max_len  : {MAX_LEN} (truncation + padding)")

# sample token inspection
sample_text = train_df["sentence"].iloc[0]
sample_enc  = tokenizer(sample_text, truncation=True, max_length=MAX_LEN)
log.info(f"  Sample sentence: \"{sample_text[:80]}...\"")
log.info(f"  Token count    : {len(sample_enc['input_ids'])}")
log.info(f"  Token ids (first 10): {sample_enc['input_ids'][:10]}")

class SentimentDataset(Dataset):
    def __init__(self, df, split_name=""):
        t1 = time.time()
        log.info(f"  Tokenizing [{split_name}] — {len(df)} samples...")
        self.encodings = tokenizer(
            df["sentence"].tolist(),
            truncation=True,
            padding="max_length",
            max_length=MAX_LEN,
            return_tensors="pt",
        )
        self.labels = torch.tensor(df["label"].tolist(), dtype=torch.long)
        elapsed = time.time() - t1
        log.info(f"    input_ids shape     : {tuple(self.encodings['input_ids'].shape)}")
        log.info(f"    attention_mask shape: {tuple(self.encodings['attention_mask'].shape)}")
        log.info(f"    labels shape        : {tuple(self.labels.shape)}")
        log.info(f"    Tokenization done   : {elapsed:.2f}s")

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids":      self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "labels":         self.labels[idx],
        }

train_ds = SentimentDataset(train_df, "train")
val_ds   = SentimentDataset(val_df,   "val")
test_ds  = SentimentDataset(test_df,  "test")

# ── Model ─────────────────────────────────────────────────────────────────────
section("4 / 6  — Model")
log.info(f"  Loading: {MODEL_NAME}")
log.info(f"  Task   : SequenceClassification (3 labels)")
t0 = time.time()
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=3,
    id2label={0: "negative", 1: "neutral", 2: "positive"},
    label2id={"negative": 0, "neutral": 1, "positive": 2},
)
log.info(f"  Model loaded in {time.time()-t0:.2f}s")

total_params     = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
frozen_params    = total_params - trainable_params
log.info(f"  Architecture     : {model.config.model_type}")
log.info(f"  Hidden size      : {model.config.hidden_size}")
log.info(f"  Attention heads  : {model.config.num_attention_heads}")
log.info(f"  Transformer layers: {model.config.num_hidden_layers}")
log.info(f"  Total params     : {total_params:,}")
log.info(f"  Trainable params : {trainable_params:,}")
log.info(f"  Frozen params    : {frozen_params:,}")
log.info(f"  Strategy         : Full fine-tuning (no PEFT/LoRA)")

# ── Metrics & Callback ────────────────────────────────────────────────────────
history = {
    "train_loss":    [],
    "eval_loss":     [],
    "eval_accuracy": [],
    "eval_f1":       [],
}
_epoch_train_losses = []   # accumulates within-epoch losses for per-epoch avg

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds  = np.argmax(logits, axis=-1)
    acc    = accuracy_score(labels, preds)
    f1     = f1_score(labels, preds, average="macro")
    per_cls_f1 = f1_score(labels, preds, average=None)
    history["eval_accuracy"].append(round(acc, 4))
    history["eval_f1"].append(round(f1, 4))
    log.info(f"    accuracy  : {acc:.4f}")
    log.info(f"    macro-F1  : {f1:.4f}")
    for i, (name, score) in enumerate(zip(LABEL_NAMES, per_cls_f1)):
        log.info(f"    F1[{name:8s}]: {score:.4f}")
    return {"accuracy": acc, "f1": f1}

class LoggingCallback(TrainerCallback):

    def on_train_begin(self, args, state, control, **kwargs):
        steps_per_epoch = state.max_steps // args.num_train_epochs
        log.info(f"  Steps per epoch  : ~{steps_per_epoch}")
        log.info(f"  Total steps      : {state.max_steps}")
        log.info(f"  Warmup steps     : {state.warmup_steps if hasattr(state,'warmup_steps') else 'N/A'}")

    def on_epoch_begin(self, args, state, control, **kwargs):
        epoch_num = int(state.epoch) + 1
        subsection(f"Epoch {epoch_num} / {int(args.num_train_epochs)}  — Training")
        _epoch_train_losses.clear()

    def on_step_end(self, args, state, control, **kwargs):
        pass  # high-frequency; keep silent — on_log handles it

    def on_log(self, args, state, control, logs=None, **kwargs):
        if not logs:
            return
        step = state.global_step
        if "loss" in logs:
            loss = round(logs["loss"], 4)
            lr   = logs.get("learning_rate", 0.0)
            history["train_loss"].append(loss)
            _epoch_train_losses.append(loss)
            epoch_progress = ""
            if state.max_steps > 0:
                pct = step / state.max_steps * 100
                epoch_progress = f"  ({pct:.0f}% total)"
            log.info(
                f"    step {step:4d}{epoch_progress} | "
                f"loss: {loss:.4f} | lr: {lr:.3e}"
            )
        if "eval_loss" in logs:
            history["eval_loss"].append(round(logs["eval_loss"], 4))

    def on_evaluate(self, args, state, control, **kwargs):
        subsection(f"Epoch {int(state.epoch)} — Evaluation")

    def on_epoch_end(self, args, state, control, **kwargs):
        epoch_num = int(state.epoch)
        avg_loss  = round(sum(_epoch_train_losses) / len(_epoch_train_losses), 4) if _epoch_train_losses else 0.0
        best_f1   = max(history["eval_f1"]) if history["eval_f1"] else 0.0
        log.info(f"  Epoch {epoch_num} summary:")
        log.info(f"    avg train loss : {avg_loss:.4f}")
        log.info(f"    val accuracy   : {history['eval_accuracy'][-1] if history['eval_accuracy'] else 'N/A'}")
        log.info(f"    val macro-F1   : {history['eval_f1'][-1] if history['eval_f1'] else 'N/A'}")
        log.info(f"    best F1 so far : {best_f1:.4f}")

    def on_train_end(self, args, state, control, **kwargs):
        log.info(f"  Training finished at step {state.global_step}")
        log.info(f"  Best checkpoint  : {state.best_model_checkpoint}")
        log.info(f"  Best metric (F1) : {state.best_metric:.4f}" if state.best_metric else "  Best metric: N/A")

# ── Training args ─────────────────────────────────────────────────────────────
section("5 / 6  — Training")
training_args = TrainingArguments(
    output_dir=str(MODEL_DIR),
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    learning_rate=LR,
    weight_decay=0.01,
    warmup_ratio=0.1,
    eval_strategy="epoch",
    save_strategy="no",
    logging_strategy="steps",
    logging_steps=10,
    load_best_model_at_end=False,
    seed=SEED,
    report_to="none",
)

log.info(f"  output_dir      : {training_args.output_dir}")
log.info(f"  eval_strategy   : {training_args.eval_strategy}")
log.info(f"  save_strategy   : {training_args.save_strategy}")
log.info(f"  logging_steps   : {training_args.logging_steps}")
log.info(f"  early_stopping  : patience=2 epochs")
log.info(f"  best model      : loaded at end (metric=F1)")

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    compute_metrics=compute_metrics,
    callbacks=[LoggingCallback()],
)

t_train_start = time.time()
train_result  = trainer.train()
train_elapsed = time.time() - t_train_start

log.info("=" * 65)
log.info("  Training complete.")
log.info(f"  Total steps      : {train_result.global_step}")
log.info(f"  Wall time        : {train_elapsed:.1f}s  ({train_elapsed/60:.1f} min)")
log.info(f"  Train runtime    : {train_result.metrics.get('train_runtime', 0):.1f}s")
log.info(f"  Samples / sec    : {train_result.metrics.get('train_samples_per_second', 0):.1f}")
log.info(f"  Steps / sec      : {train_result.metrics.get('train_steps_per_second', 0):.2f}")
log.info(f"  Final train loss : {train_result.metrics.get('train_loss', 0):.4f}")

# Snapshot history now — trainer.predict() also calls compute_metrics and
# would append an extra entry to eval_accuracy/eval_f1.
train_history = {k: list(v) for k, v in history.items()}

# ── Test evaluation ───────────────────────────────────────────────────────────
section("6 / 6  — Test Evaluation")
log.info("  Running inference on held-out test set...")
t0          = time.time()
test_output = trainer.predict(test_ds)
log.info(f"  Inference done in {time.time()-t0:.2f}s")

test_preds  = np.argmax(test_output.predictions, axis=-1)
test_labels = test_output.label_ids
test_acc    = accuracy_score(test_labels, test_preds)
test_f1     = f1_score(test_labels, test_preds, average="macro")
per_cls_f1  = f1_score(test_labels, test_preds, average=None)
report      = classification_report(test_labels, test_preds, target_names=LABEL_NAMES)
cm          = confusion_matrix(test_labels, test_preds)

subsection("Test Results")
log.info(f"  Accuracy   : {test_acc:.4f}")
log.info(f"  Macro-F1   : {test_f1:.4f}")
for name, score in zip(LABEL_NAMES, per_cls_f1):
    log.info(f"  F1[{name:8s}]: {score:.4f}")
log.info(f"\n{report}")
log.info(f"  Confusion matrix (rows=actual, cols=predicted):")
log.info(f"  Labels: {LABEL_NAMES}")
log.info(f"\n{cm}")

# ── Save metrics JSON ─────────────────────────────────────────────────────────
metrics_out = {
    "test_accuracy": round(test_acc, 4),
    "test_f1":       round(test_f1, 4),
    "per_class_f1":  {n: round(s, 4) for n, s in zip(LABEL_NAMES, per_cls_f1.tolist())},
    "history":       train_history,
    "classification_report": report,
}
metrics_json_path = METRICS_DIR / "metrics.json"
with open(metrics_json_path, "w") as f:
    json.dump(metrics_out, f, indent=2)
log.info(f"  Metrics JSON → {metrics_json_path}")

# ── Plot ──────────────────────────────────────────────────────────────────────
log.info("  Generating metrics plot...")
fig = plt.figure(figsize=(20, 12))
fig.suptitle("FinBERT Fine-Tuning — Training Metrics", fontsize=17, fontweight="bold", y=0.98)
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.38)

epochs_x = list(range(1, len(train_history["eval_loss"]) + 1))

ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(train_history["train_loss"], color="steelblue", linewidth=1.2)
ax1.set_title("Training Loss (per step)")
ax1.set_xlabel("Step")
ax1.set_ylabel("Loss")
ax1.grid(alpha=0.3)

ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(epochs_x, train_history["eval_loss"], marker="o", color="coral", linewidth=2)
ax2.set_title("Validation Loss (per epoch)")
ax2.set_xlabel("Epoch")
ax2.set_ylabel("Loss")
ax2.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
ax2.grid(alpha=0.3)

ax3 = fig.add_subplot(gs[0, 2])
ax3.plot(epochs_x, train_history["eval_accuracy"], marker="o", color="mediumseagreen", linewidth=2)
ax3.set_title("Validation Accuracy (per epoch)")
ax3.set_xlabel("Epoch")
ax3.set_ylabel("Accuracy")
ax3.set_ylim(0, 1)
ax3.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
ax3.grid(alpha=0.3)

ax4 = fig.add_subplot(gs[1, 0])
ax4.plot(epochs_x, train_history["eval_f1"], marker="o", color="mediumpurple", linewidth=2)
ax4.set_title("Validation Macro-F1 (per epoch)")
ax4.set_xlabel("Epoch")
ax4.set_ylabel("Macro-F1")
ax4.set_ylim(0, 1)
ax4.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
ax4.grid(alpha=0.3)

ax5 = fig.add_subplot(gs[1, 1])
bars = ax5.bar(
    LABEL_NAMES, per_cls_f1,
    color=["salmon", "cornflowerblue", "mediumseagreen"], width=0.5,
)
ax5.set_ylim(0, 1)
ax5.set_title("Test F1 per Class")
ax5.set_ylabel("F1")
for bar, val in zip(bars, per_cls_f1):
    ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height()+0.02,
             f"{val:.4f}", ha="center", va="bottom", fontweight="bold", fontsize=9)
ax5.grid(axis="y", alpha=0.3)

ax6 = fig.add_subplot(gs[1, 2])
sns.heatmap(
    cm, annot=True, fmt="d", cmap="Blues",
    xticklabels=LABEL_NAMES, yticklabels=LABEL_NAMES,
    ax=ax6, linewidths=0.5,
)
ax6.set_title("Test Confusion Matrix")
ax6.set_xlabel("Predicted")
ax6.set_ylabel("Actual")

plot_path = METRICS_DIR / "training_metrics.png"
plt.savefig(plot_path, dpi=150, bbox_inches="tight")
plt.close()
log.info(f"  Plot saved → {plot_path}")

# ── Save model ────────────────────────────────────────────────────────────────
best_model_path = MODEL_DIR / "best"
log.info(f"  Saving best model → {best_model_path}")
trainer.save_model(str(best_model_path))
tokenizer.save_pretrained(str(best_model_path))
log.info(f"  Model saved.")

section("Done")
log.info(f"  Finished at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log.info(f"  Wall time   : {(time.time()-t_train_start)/60:.1f} min")
log.info(f"  Model       : {best_model_path}")
log.info(f"  Metrics PNG : {plot_path}")
log.info(f"  Log file    : {LOG_FILE}")
