"""InLegalBERT fine-tuning for the intake issue-triage classifier.

Plain PyTorch training loop, no Trainer dependency. Checkpoint selection
uses the val split only; test and probe are never touched during training.
The device is auto-detected (CUDA, Apple MPS, or CPU), so the same code
runs locally and on a free Colab or Kaggle GPU.

Complaints are short, so inputs are truncated at MAX_LENGTH tokens; the
runner reports how many texts this actually affects.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, TensorDataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from src.intake.data import LABELS

MODEL_NAME = "law-ai/InLegalBERT"
MAX_LENGTH = 256
LABEL2ID: dict[str, int] = {label: i for i, label in enumerate(LABELS)}
ID2LABEL: dict[int, str] = {i: label for label, i in LABEL2ID.items()}


@dataclass(frozen=True)
class FinetuneConfig:
    """Hyperparameters for one fine-tune run. Reasonable defaults, untuned
    against test or probe."""

    model_name: str = MODEL_NAME
    max_length: int = MAX_LENGTH
    epochs: int = 4
    batch_size: int = 16
    lr: float = 2e-5
    weight_decay: float = 0.01
    warmup_frac: float = 0.1


def pick_device() -> torch.device:
    """Return the best available device: CUDA, then MPS, then CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def set_seed(seed: int) -> None:
    """Seed python, numpy, and torch for a reproducible run."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def encode(
    texts: list[str],
    labels: list[str] | None,
    tokenizer: AutoTokenizer,
    max_length: int = MAX_LENGTH,
) -> TensorDataset:
    """Tokenize texts (truncated at max_length) into a TensorDataset."""
    batch = tokenizer(
        texts,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_tensors="pt",
    )
    tensors = [batch["input_ids"], batch["attention_mask"]]
    if labels is not None:
        tensors.append(torch.tensor([LABEL2ID[l] for l in labels], dtype=torch.long))
    return TensorDataset(*tensors)


def count_truncated(texts: list[str], tokenizer: AutoTokenizer, max_length: int = MAX_LENGTH) -> int:
    """Count how many texts exceed max_length tokens before truncation."""
    lengths = [len(ids) for ids in tokenizer(texts, truncation=False)["input_ids"]]
    return sum(1 for n in lengths if n > max_length)


@torch.no_grad()
def predict(
    model: torch.nn.Module,
    tokenizer: AutoTokenizer,
    texts: list[str],
    device: torch.device,
    batch_size: int = 32,
    max_length: int = MAX_LENGTH,
) -> list[str]:
    """Predict class labels for texts with a fitted model."""
    model.eval()
    dataset = encode(texts, None, tokenizer, max_length)
    loader = DataLoader(dataset, batch_size=batch_size)
    preds: list[str] = []
    for input_ids, attention_mask in loader:
        logits = model(
            input_ids=input_ids.to(device), attention_mask=attention_mask.to(device)
        ).logits
        preds.extend(ID2LABEL[int(i)] for i in logits.argmax(dim=-1).cpu())
    return preds


def finetune(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    seed: int,
    config: FinetuneConfig = FinetuneConfig(),
) -> tuple[torch.nn.Module, AutoTokenizer, dict]:
    """Fine-tune InLegalBERT on train_df, selecting the epoch checkpoint
    with the best val macro-F1.

    Returns the best model (on device), the tokenizer, and a history dict
    with per-epoch val scores and the selected epoch.
    """
    set_seed(seed)
    device = pick_device()
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=len(LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    ).to(device)

    train_set = encode(
        train_df["text"].tolist(), train_df["label"].tolist(), tokenizer, config.max_length
    )
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        train_set, batch_size=config.batch_size, shuffle=True, generator=generator
    )
    total_steps = len(loader) * config.epochs
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.lr, weight_decay=config.weight_decay
    )
    scheduler = get_linear_schedule_with_warmup(
        optimizer, int(total_steps * config.warmup_frac), total_steps
    )

    val_texts = val_df["text"].tolist()
    val_labels = val_df["label"].tolist()
    best_state: dict | None = None
    best_f1 = -1.0
    best_epoch = -1
    history: list[float] = []

    for epoch in range(1, config.epochs + 1):
        model.train()
        for input_ids, attention_mask, labels in loader:
            optimizer.zero_grad()
            out = model(
                input_ids=input_ids.to(device),
                attention_mask=attention_mask.to(device),
                labels=labels.to(device),
            )
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
        val_pred = predict(model, tokenizer, val_texts, device, max_length=config.max_length)
        val_f1 = float(f1_score(val_labels, val_pred, average="macro"))
        history.append(round(val_f1, 4))
        if val_f1 > best_f1:
            best_f1 = val_f1
            best_epoch = epoch
            best_state = copy.deepcopy(
                {k: v.detach().cpu() for k, v in model.state_dict().items()}
            )

    assert best_state is not None
    model.load_state_dict(best_state)
    model.to(device)
    info = {
        "seed": seed,
        "best_epoch": best_epoch,
        "best_val_macro_f1": round(best_f1, 4),
        "val_macro_f1_by_epoch": history,
    }
    return model, tokenizer, info
