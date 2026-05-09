from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os
import requests as http

from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/sentiment", tags=["Sentiment"])

HF_API_URL = "https://api-inference.huggingface.co/models/Arindam3453/finsense-finbert"


def _predict(text: str) -> dict:
    token = os.getenv("HF_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = http.post(HF_API_URL, headers=headers, json={"inputs": text}, timeout=30)
    if resp.status_code == 503:
        raise HTTPException(status_code=503, detail="Model is loading on HF, retry in ~20s")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"HF Inference API error: {resp.text}")
    scores = {item["label"]: item["score"] for item in resp.json()[0]}
    label  = max(scores, key=scores.get)
    return {
        "label":          label,
        "score_negative": scores.get("negative", 0.0),
        "score_neutral":  scores.get("neutral",  0.0),
        "score_positive": scores.get("positive", 0.0),
    }


@router.post("", response_model=schemas.SentimentOut, status_code=201)
def analyze_sentiment(
    payload: schemas.SentimentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = _predict(payload.text)

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
