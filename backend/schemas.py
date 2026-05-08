from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from .models import SentimentLabel, TrainingStatus


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Ticker ────────────────────────────────────────────────────────────────────
class TickerCreate(BaseModel):
    symbol: str = Field(max_length=10)
    company_name: Optional[str] = None
    sector: Optional[str] = None

class TickerUpdate(BaseModel):
    company_name: Optional[str] = None
    sector: Optional[str] = None

class TickerOut(BaseModel):
    id: int
    symbol: str
    company_name: Optional[str]
    sector: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Transcript ─────────────────────────────────────────────────────────────────
class TranscriptFetchRequest(BaseModel):
    symbol: str
    years: list[int] = Field(default=[2022, 2023, 2024])

class TranscriptOut(BaseModel):
    id: int
    ticker_id: int
    year: int
    quarter: int
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Sentiment ─────────────────────────────────────────────────────────────────
class SentimentRequest(BaseModel):
    text: str = Field(min_length=1)
    ticker_symbol: Optional[str] = None
    transcript_id: Optional[int] = None

class SentimentOut(BaseModel):
    id: int
    input_text: str
    label: SentimentLabel
    score_positive: float
    score_neutral: float
    score_negative: float
    ticker_id: Optional[int]
    transcript_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Training ──────────────────────────────────────────────────────────────────
class TrainingRequest(BaseModel):
    epochs: int = Field(default=5, ge=1, le=20)
    batch_size: int = Field(default=16, ge=4, le=64)
    learning_rate: float = Field(default=2e-5, gt=0)

class TrainingRunOut(BaseModel):
    id: int
    status: TrainingStatus
    epochs: int
    batch_size: int
    learning_rate: float
    test_accuracy: Optional[float]
    test_f1: Optional[float]
    log_output: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
