from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .database import engine, Base
from .routes import auth, tickers, transcripts, sentiment, training

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FinSense API",
    description="Earnings Call Sentiment Analysis using FinBERT",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tickers.router)
app.include_router(transcripts.router)
app.include_router(sentiment.router)
app.include_router(training.router)


@app.api_route("/", methods=["GET", "HEAD"], tags=["Health"])
def root():
    return {"status": "ok", "service": "FinSense API", "version": "1.0.0"}


@app.api_route("/health", methods=["GET", "HEAD"], tags=["Health"])
def health():
    return {"status": "healthy"}