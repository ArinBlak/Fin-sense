"""
Seed script — loads all CSV files into PostgreSQL via SQLAlchemy ORM.

Run from project root:
    python -m backend.data.seed
"""

import sys
import logging
from pathlib import Path
from datetime import date

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"

PRICES_CSV      = DATA_DIR / "prices_AAPL.csv"
TRANSCRIPTS_CSV = DATA_DIR / "transcripts_AAPL.csv"
PHRASEBANK_CSV  = DATA_DIR / "financial_phrasebank.csv"

# ── DB setup ──────────────────────────────────────────────────────────────────
from backend.database import engine, Base, SessionLocal
from backend import models

log.info("Creating tables if not exist...")
Base.metadata.create_all(bind=engine)
log.info("Tables ready.")

db = SessionLocal()


def _get_or_create_ticker(symbol: str, company_name: str = None) -> models.Ticker:
    ticker = db.query(models.Ticker).filter(models.Ticker.symbol == symbol.upper()).first()
    if not ticker:
        ticker = models.Ticker(symbol=symbol.upper(), company_name=company_name)
        db.add(ticker)
        db.commit()
        db.refresh(ticker)
        log.info(f"  Created ticker: {ticker.symbol} (id={ticker.id})")
    else:
        log.info(f"  Ticker already exists: {ticker.symbol} (id={ticker.id})")
    return ticker


# ── 1. Stock Prices ───────────────────────────────────────────────────────────
def seed_prices():
    log.info("=" * 55)
    log.info("Seeding stock prices from prices_AAPL.csv ...")
    if not PRICES_CSV.exists():
        log.warning(f"  File not found: {PRICES_CSV} — skipping")
        return

    # yfinance CSV has 3 meta-rows before data; skip rows 1 and 2,
    # keep row 0 as header (Price, Close, High, Low, Open, Volume)
    df = pd.read_csv(PRICES_CSV, skiprows=[1, 2])
    df.rename(columns={"Price": "Date"}, inplace=True)
    df.dropna(subset=["Date"], inplace=True)
    df = df[df["Date"].str.match(r"\d{4}-\d{2}-\d{2}", na=False)].copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    for col in ["Close", "High", "Low", "Open", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    log.info(f"  Rows parsed: {len(df)}")
    log.info(f"  Date range : {df['Date'].min()} → {df['Date'].max()}")

    ticker = _get_or_create_ticker("AAPL", "Apple Inc.")

    inserted = 0
    skipped  = 0
    for _, row in df.iterrows():
        exists = db.query(models.StockPrice).filter(
            models.StockPrice.ticker_id == ticker.id,
            models.StockPrice.date == row["Date"],
        ).first()
        if exists:
            skipped += 1
            continue
        db.add(models.StockPrice(
            ticker_id=ticker.id,
            date=row["Date"],
            open=row.get("Open"),
            high=row.get("High"),
            low=row.get("Low"),
            close=row["Close"],
            volume=int(row["Volume"]) if pd.notna(row.get("Volume")) else None,
        ))
        inserted += 1

    db.commit()
    log.info(f"  Inserted: {inserted} | Skipped (duplicate): {skipped}")


# ── 2. Transcripts ────────────────────────────────────────────────────────────
def seed_transcripts():
    log.info("=" * 55)
    log.info("Seeding transcripts from transcripts_AAPL.csv ...")
    if not TRANSCRIPTS_CSV.exists():
        log.warning(f"  File not found: {TRANSCRIPTS_CSV} — skipping")
        return

    df = pd.read_csv(TRANSCRIPTS_CSV)
    log.info(f"  Rows parsed: {len(df)}")

    ticker = _get_or_create_ticker("AAPL", "Apple Inc.")

    inserted = 0
    skipped  = 0
    for _, row in df.iterrows():
        exists = db.query(models.Transcript).filter(
            models.Transcript.ticker_id == ticker.id,
            models.Transcript.year      == int(row["year"]),
            models.Transcript.quarter   == int(row["quarter"]),
        ).first()
        if exists:
            skipped += 1
            continue
        db.add(models.Transcript(
            ticker_id=ticker.id,
            year=int(row["year"]),
            quarter=int(row["quarter"]),
            text=str(row["text"]),
        ))
        inserted += 1

    db.commit()
    log.info(f"  Inserted: {inserted} | Skipped (duplicate): {skipped}")


# ── 3. Financial PhraseBank ───────────────────────────────────────────────────
def seed_phrasebank():
    log.info("=" * 55)
    log.info("Seeding Financial PhraseBank from financial_phrasebank.csv ...")
    if not PHRASEBANK_CSV.exists():
        log.warning(f"  File not found: {PHRASEBANK_CSV} — skipping")
        return

    df = pd.read_csv(PHRASEBANK_CSV)
    log.info(f"  Rows parsed : {len(df)}")
    log.info(f"  Columns     : {list(df.columns)}")

    existing = db.query(models.TrainingSample).count()
    if existing >= len(df):
        log.info(f"  Already seeded ({existing} rows in DB) — skipping")
        return

    db.query(models.TrainingSample).delete()
    db.commit()

    records = [
        models.TrainingSample(sentence=str(row["sentence"]), label=int(row["label"]))
        for _, row in df.iterrows()
    ]
    db.bulk_save_objects(records)
    db.commit()
    log.info(f"  Inserted: {len(records)}")


# ── Run all ───────────────────────────────────────────────────────────────────
try:
    seed_prices()
    seed_transcripts()
    seed_phrasebank()
    log.info("=" * 55)
    log.info("Seeding complete.")

    # Summary
    log.info("── DB row counts ──────────────────────────────────────")
    log.info(f"  tickers          : {db.query(models.Ticker).count()}")
    log.info(f"  stock_prices     : {db.query(models.StockPrice).count()}")
    log.info(f"  transcripts      : {db.query(models.Transcript).count()}")
    log.info(f"  training_samples : {db.query(models.TrainingSample).count()}")
    log.info(f"  sentiment_results: {db.query(models.SentimentResult).count()}")
    log.info(f"  training_runs    : {db.query(models.TrainingRun).count()}")
finally:
    db.close()
