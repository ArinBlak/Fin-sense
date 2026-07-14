from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import re
import requests as http
import logging

from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

log = logging.getLogger(__name__)

router = APIRouter(prefix="/sentiment", tags=["Sentiment"])

HF_API_URL = "https://api-inference.huggingface.co/models/Arindam3453/finsense-finbert"

# ── Local pipeline (lazy-loaded, cached at module level) ──────────────────────
_local_pipeline = None
_LOCAL_MODEL_PATH = (
    os.path.dirname(__file__) + "/../../training/finbert_finetuned/best"
)


def _get_local_pipeline():
    """Load the fine-tuned FinBERT model from disk once and cache it."""
    global _local_pipeline
    if _local_pipeline is not None:
        return _local_pipeline

    model_path = os.path.abspath(_LOCAL_MODEL_PATH)
    if not os.path.isdir(model_path):
        return None

    try:
        from transformers import pipeline
        log.info("Loading local FinBERT model from %s", model_path)
        _local_pipeline = pipeline(
            "text-classification",
            model=model_path,
            tokenizer=model_path,
            top_k=None,          # return scores for all labels
            device=-1,           # CPU; MPS/CUDA picked automatically if available
        )
        log.info("Local FinBERT model loaded successfully.")
    except Exception as exc:
        log.warning("Could not load local model: %s", exc)
        _local_pipeline = None

    return _local_pipeline


def _local_predict(text: str) -> Optional[dict]:
    """Run inference using the local pipeline. Returns None if unavailable."""
    pipe = _get_local_pipeline()
    if pipe is None:
        return None
    try:
        raw = pipe(text[:512], truncation=True)  # respect BERT's token limit
        # raw is a list of [{"label": ..., "score": ...}, ...]
        scores = {item["label"]: item["score"] for item in raw[0]}
        label = max(scores, key=scores.get)
        return {
            "label":          label,
            "score_negative": scores.get("negative", 0.0),
            "score_neutral":  scores.get("neutral",  0.0),
            "score_positive": scores.get("positive", 0.0),
        }
    except Exception as exc:
        log.warning("Local inference failed: %s", exc)
        return None


# ── HF Inference API ──────────────────────────────────────────────────────────
def _hf_predict(text: str) -> Optional[dict]:
    """Try the Hugging Face Inference API. Returns None on non-fatal errors."""
    token = os.getenv("HF_TOKEN", "")
    if not token:
        return None   # no token -> skip HF, fall through to local

    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = http.post(HF_API_URL, headers=headers, json={"inputs": text}, timeout=30)
    except Exception as exc:
        log.warning("HF API request failed: %s", exc)
        return None

    if resp.status_code in (503, 429, 502):
        log.warning("HF API returned %s -- falling back to local model", resp.status_code)
        return None
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


def _predict(text: str) -> dict:
    """
    Run sentiment inference. Strategy:
    1. Try HF Inference API (skipped if HF_TOKEN is absent).
    2. Fall back to local fine-tuned model on disk.
    3. Raise 503 if neither is available.
    """
    result = _hf_predict(text) or _local_predict(text)
    if result is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Sentiment model unavailable. "
                "Set HF_TOKEN to use the Hugging Face API, or run training to generate a local model."
            ),
        )
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────
def _split_into_chunks(text: str, max_chars: int = 1500) -> List[str]:
    """
    Split text into chunks of at most max_chars characters, breaking on sentence
    boundaries where possible. ~1500 chars is approx 300 tokens, safely below
    FinBERT's 512-token limit.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks: List[str] = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = sent
        else:
            current = (current + " " + sent).strip() if current else sent
    if current:
        chunks.append(current.strip())
    # Guard against edge case: single sentence longer than max_chars
    final: List[str] = []
    for chunk in chunks:
        if len(chunk) > max_chars:
            for i in range(0, len(chunk), max_chars):
                final.append(chunk[i:i + max_chars])
        else:
            final.append(chunk)
    return [c for c in final if c]


# ── Routes ────────────────────────────────────────────────────────────────────
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


@router.post(
    "/transcript/{transcript_id}",
    response_model=schemas.TranscriptAnalysisOut,
    status_code=201,
    summary="Analyze an entire stored transcript",
)
def analyze_transcript(
    transcript_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Split a full earnings-call transcript into chunks, run FinBERT on each,
    average the scores, and persist a single aggregated SentimentResult.
    """
    transcript = db.query(models.Transcript).filter(
        models.Transcript.id == transcript_id
    ).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    chunks = _split_into_chunks(transcript.text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Transcript text is empty")

    # Run inference on every chunk
    chunk_results = []
    for chunk in chunks:
        try:
            chunk_results.append(_predict(chunk))
        except HTTPException:
            raise   # propagate 503 / 502 immediately
        except Exception as exc:
            log.warning("Chunk inference error (skipping): %s", exc)

    if not chunk_results:
        raise HTTPException(status_code=503, detail="Inference failed on all chunks")

    # Aggregate: simple mean across chunks
    avg_pos = sum(r["score_positive"] for r in chunk_results) / len(chunk_results)
    avg_neu = sum(r["score_neutral"]  for r in chunk_results) / len(chunk_results)
    avg_neg = sum(r["score_negative"] for r in chunk_results) / len(chunk_results)
    scores_map = {"positive": avg_pos, "neutral": avg_neu, "negative": avg_neg}
    agg_label = max(scores_map, key=scores_map.__getitem__)

    # Persist as a single SentimentResult
    record = models.SentimentResult(
        user_id=current_user.id,
        ticker_id=transcript.ticker_id,
        transcript_id=transcript_id,
        input_text=transcript.text[:2000],   # store a preview (first 2000 chars)
        label=agg_label,
        score_positive=round(avg_pos, 4),
        score_neutral=round(avg_neu, 4),
        score_negative=round(avg_neg, 4),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Return extended schema with chunk_count
    out = schemas.TranscriptAnalysisOut.model_validate(record)
    out.chunk_count = len(chunk_results)
    return out


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
