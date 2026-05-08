from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import torch
import numpy as np

from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/sentiment", tags=["Sentiment"])

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "training" / "finbert_finetuned" / "best"

_tokenizer = None
_model     = None


def _load_model():
    global _tokenizer, _model
    if _model is None:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        if not MODEL_PATH.exists():
            raise RuntimeError(f"Fine-tuned model not found at {MODEL_PATH}. Run training first.")
        _tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH))
        _model     = AutoModelForSequenceClassification.from_pretrained(str(MODEL_PATH))
        _model.eval()


def _predict(text: str) -> dict:
    _load_model()
    inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=128, padding=True)
    with torch.no_grad():
        logits = _model(**inputs).logits
    probs  = torch.softmax(logits, dim=-1).squeeze().numpy()
    labels = ["negative", "neutral", "positive"]
    label  = labels[int(np.argmax(probs))]
    return {
        "label":          label,
        "score_negative": float(probs[0]),
        "score_neutral":  float(probs[1]),
        "score_positive": float(probs[2]),
    }


@router.post("", response_model=schemas.SentimentOut, status_code=201)
def analyze_sentiment(
    payload: schemas.SentimentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        result = _predict(payload.text)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    ticker_id = None
    if payload.ticker_symbol:
        ticker = db.query(models.Ticker).filter(
            models.Ticker.symbol == payload.ticker_symbol.upper()
        ).first()
        if ticker:
            ticker_id = ticker.id

    record = models.SentimentResult(
        user_id=current_user.id,
        ticker_id=ticker_id,
        transcript_id=payload.transcript_id,
        input_text=payload.text,
        label=result["label"],
        score_positive=result["score_positive"],
        score_neutral=result["score_neutral"],
        score_negative=result["score_negative"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=List[schemas.SentimentOut])
def list_results(
    ticker_id: int = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.SentimentResult).filter(
        models.SentimentResult.user_id == current_user.id
    )
    if ticker_id:
        q = q.filter(models.SentimentResult.ticker_id == ticker_id)
    return q.offset(skip).limit(limit).all()


@router.get("/{result_id}", response_model=schemas.SentimentOut)
def get_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    r = db.query(models.SentimentResult).filter(
        models.SentimentResult.id == result_id,
        models.SentimentResult.user_id == current_user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Result not found")
    return r


@router.delete("/{result_id}", status_code=204)
def delete_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    r = db.query(models.SentimentResult).filter(
        models.SentimentResult.id == result_id,
        models.SentimentResult.user_id == current_user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Result not found")
    db.delete(r)
    db.commit()
