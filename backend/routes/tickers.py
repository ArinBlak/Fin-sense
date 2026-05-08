from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/tickers", tags=["Tickers"])


@router.post("", response_model=schemas.TickerOut, status_code=201)
def create_ticker(
    payload: schemas.TickerCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    if db.query(models.Ticker).filter(models.Ticker.symbol == payload.symbol.upper()).first():
        raise HTTPException(status_code=400, detail="Ticker already exists")
    ticker = models.Ticker(**payload.model_dump())
    ticker.symbol = ticker.symbol.upper()
    db.add(ticker)
    db.commit()
    db.refresh(ticker)
    return ticker


@router.get("", response_model=List[schemas.TickerOut])
def list_tickers(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return db.query(models.Ticker).offset(skip).limit(limit).all()


@router.get("/{ticker_id}", response_model=schemas.TickerOut)
def get_ticker(
    ticker_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    ticker = db.query(models.Ticker).filter(models.Ticker.id == ticker_id).first()
    if not ticker:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return ticker


@router.put("/{ticker_id}", response_model=schemas.TickerOut)
def update_ticker(
    ticker_id: int,
    payload: schemas.TickerUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    ticker = db.query(models.Ticker).filter(models.Ticker.id == ticker_id).first()
    if not ticker:
        raise HTTPException(status_code=404, detail="Ticker not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(ticker, field, value)
    db.commit()
    db.refresh(ticker)
    return ticker


@router.delete("/{ticker_id}", status_code=204)
def delete_ticker(
    ticker_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    ticker = db.query(models.Ticker).filter(models.Ticker.id == ticker_id).first()
    if not ticker:
        raise HTTPException(status_code=404, detail="Ticker not found")
    db.delete(ticker)
    db.commit()
