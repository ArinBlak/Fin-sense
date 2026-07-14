from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
import logging

from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

log = logging.getLogger(__name__)

router = APIRouter(prefix="/tickers", tags=["Tickers"])


# ── Stock price fetching (background task) ────────────────────────────────────
def _fetch_prices(symbol: str, ticker_id: int, db: Session):
    """Download historical stock prices from yfinance and upsert into stock_prices."""
    try:
        import yfinance as yf
        from datetime import datetime

        end_date   = datetime.utcnow().date()
        start_date = end_date - timedelta(days=3 * 365)   # ~3 years of history

        log.info("Fetching price history for %s (%s to %s)", symbol, start_date, end_date)
        df = yf.download(symbol, start=str(start_date), end=str(end_date), progress=False)

        if df.empty:
            log.warning("No price data returned for %s", symbol)
            return

        # yfinance may return MultiIndex columns when only one ticker is passed in
        # Flatten to simple column names
        if hasattr(df.columns, "levels"):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

        inserted = 0
        for row_date, row in df.iterrows():
            price_date = row_date.date() if hasattr(row_date, "date") else row_date
            exists = db.query(models.StockPrice).filter(
                models.StockPrice.ticker_id == ticker_id,
                models.StockPrice.date == price_date,
            ).first()
            if exists:
                continue
            db.add(models.StockPrice(
                ticker_id=ticker_id,
                date=price_date,
                open=float(row.get("Open"))   if row.get("Open")   is not None else None,
                high=float(row.get("High"))   if row.get("High")   is not None else None,
                low=float(row.get("Low"))     if row.get("Low")    is not None else None,
                close=float(row["Close"]),
                volume=int(row["Volume"])     if row.get("Volume") is not None else None,
            ))
            inserted += 1
        db.commit()
        log.info("Inserted %d price rows for %s", inserted, symbol)
    except Exception as exc:
        log.error("Price fetch failed for %s: %s", symbol, exc)


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post("", response_model=schemas.TickerOut, status_code=201)
def create_ticker(
    payload: schemas.TickerCreate,
    background_tasks: BackgroundTasks,
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
    # Kick off price download in the background so the response is instant
    background_tasks.add_task(_fetch_prices, ticker.symbol, ticker.id, db)
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


@router.get("/{ticker_id}/prices", response_model=List[schemas.StockPriceOut])
def get_ticker_prices(
    ticker_id: int,
    start: Optional[date] = None,
    end: Optional[date] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Return historical stock prices for a ticker, optionally filtered by date range."""
    ticker = db.query(models.Ticker).filter(models.Ticker.id == ticker_id).first()
    if not ticker:
        raise HTTPException(status_code=404, detail="Ticker not found")

    q = db.query(models.StockPrice).filter(models.StockPrice.ticker_id == ticker_id)
    if start:
        q = q.filter(models.StockPrice.date >= start)
    if end:
        q = q.filter(models.StockPrice.date <= end)
    return q.order_by(models.StockPrice.date.asc()).limit(limit).all()
