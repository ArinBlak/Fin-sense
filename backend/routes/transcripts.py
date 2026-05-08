from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/transcripts", tags=["Transcripts"])


def _fetch_and_store(symbol: str, years: list[int], db: Session):
    from earningscall import get_company
    ticker = db.query(models.Ticker).filter(models.Ticker.symbol == symbol.upper()).first()
    if not ticker:
        ticker = models.Ticker(symbol=symbol.upper())
        db.add(ticker)
        db.commit()
        db.refresh(ticker)

    company = get_company(symbol)
    for event in company.events():
        if event.year not in years:
            continue
        exists = db.query(models.Transcript).filter(
            models.Transcript.ticker_id == ticker.id,
            models.Transcript.year == event.year,
            models.Transcript.quarter == event.quarter,
        ).first()
        if exists:
            continue
        transcript = company.get_transcript(event=event)
        if not transcript:
            continue
        db.add(models.Transcript(
            ticker_id=ticker.id,
            year=event.year,
            quarter=event.quarter,
            text=transcript.text,
        ))
    db.commit()


@router.post("/fetch", status_code=202)
def fetch_transcripts(
    payload: schemas.TranscriptFetchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    background_tasks.add_task(_fetch_and_store, payload.symbol, payload.years, db)
    return {"message": f"Fetching transcripts for {payload.symbol.upper()} in background"}


@router.get("", response_model=List[schemas.TranscriptOut])
def list_transcripts(
    ticker_id: int = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    q = db.query(models.Transcript)
    if ticker_id:
        q = q.filter(models.Transcript.ticker_id == ticker_id)
    return q.offset(skip).limit(limit).all()


@router.get("/{transcript_id}", response_model=schemas.TranscriptOut)
def get_transcript(
    transcript_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    t = db.query(models.Transcript).filter(models.Transcript.id == transcript_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return t


@router.delete("/{transcript_id}", status_code=204)
def delete_transcript(
    transcript_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    t = db.query(models.Transcript).filter(models.Transcript.id == transcript_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transcript not found")
    db.delete(t)
    db.commit()
