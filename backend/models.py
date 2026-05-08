from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum, Boolean, Date, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .database import Base


class SentimentLabel(str, enum.Enum):
    positive = "positive"
    neutral  = "neutral"
    negative = "negative"


class TrainingStatus(str, enum.Enum):
    pending   = "pending"
    running   = "running"
    completed = "completed"
    failed    = "failed"


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    username      = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    sentiment_results = relationship("SentimentResult", back_populates="user")
    training_runs     = relationship("TrainingRun", back_populates="user")


class Ticker(Base):
    __tablename__ = "tickers"

    id          = Column(Integer, primary_key=True, index=True)
    symbol      = Column(String(10), unique=True, index=True, nullable=False)
    company_name = Column(String, nullable=True)
    sector      = Column(String, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    transcripts       = relationship("Transcript", back_populates="ticker")
    sentiment_results = relationship("SentimentResult", back_populates="ticker")
    stock_prices      = relationship("StockPrice", back_populates="ticker")


class Transcript(Base):
    __tablename__ = "transcripts"

    id         = Column(Integer, primary_key=True, index=True)
    ticker_id  = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    year       = Column(Integer, nullable=False)
    quarter    = Column(Integer, nullable=False)
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticker            = relationship("Ticker", back_populates="transcripts")
    sentiment_results = relationship("SentimentResult", back_populates="transcript")


class SentimentResult(Base):
    __tablename__ = "sentiment_results"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    ticker_id     = Column(Integer, ForeignKey("tickers.id"), nullable=True)
    transcript_id = Column(Integer, ForeignKey("transcripts.id"), nullable=True)
    input_text    = Column(Text, nullable=False)
    label         = Column(Enum(SentimentLabel), nullable=False)
    score_positive = Column(Float, nullable=False)
    score_neutral  = Column(Float, nullable=False)
    score_negative = Column(Float, nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    user       = relationship("User", back_populates="sentiment_results")
    ticker     = relationship("Ticker", back_populates="sentiment_results")
    transcript = relationship("Transcript", back_populates="sentiment_results")


class StockPrice(Base):
    __tablename__ = "stock_prices"
    __table_args__ = (UniqueConstraint("ticker_id", "date", name="uq_ticker_date"),)

    id        = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    date      = Column(Date, nullable=False, index=True)
    open      = Column(Float, nullable=True)
    high      = Column(Float, nullable=True)
    low       = Column(Float, nullable=True)
    close     = Column(Float, nullable=False)
    volume    = Column(BigInteger, nullable=True)

    ticker = relationship("Ticker", back_populates="stock_prices")


class TrainingSample(Base):
    __tablename__ = "training_samples"

    id       = Column(Integer, primary_key=True, index=True)
    sentence = Column(Text, nullable=False)
    label    = Column(Integer, nullable=False)


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    status        = Column(Enum(TrainingStatus), default=TrainingStatus.pending)
    epochs        = Column(Integer, default=5)
    batch_size    = Column(Integer, default=16)
    learning_rate = Column(Float, default=2e-5)
    test_accuracy = Column(Float, nullable=True)
    test_f1       = Column(Float, nullable=True)
    log_output    = Column(Text, nullable=True)
    started_at    = Column(DateTime(timezone=True), nullable=True)
    finished_at   = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="training_runs")
