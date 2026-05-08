import yfinance as yf
import pandas as pd
from datasets import load_dataset
from dotenv import load_dotenv
from earningscall import get_company

load_dotenv()

class FinSenseDataManager:
    def __init__(self):
        pass

    def get_transcripts(self, ticker, years):
        """Pulls earnings call transcripts via earningscall."""
        company = get_company(ticker)
        records = []
        for event in company.events():
            if event.year in years:
                transcript = company.get_transcript(event=event)
                if transcript:
                    records.append({
                        "ticker": ticker,
                        "year": event.year,
                        "quarter": event.quarter,
                        "text": transcript.text,
                    })
        if records:
            df = pd.DataFrame(records)
            df.to_csv(f"transcripts_{ticker}.csv", index=False)
            print(f"Saved {len(records)} transcripts to transcripts_{ticker}.csv")
        else:
            print(f"No transcripts found for {ticker}")
        return records

    def get_stock_history(self, ticker, start_date, end_date):
        """Pulls historical price data via yfinance."""
        data = yf.download(ticker, start=start_date, end=end_date)
        data.to_csv(f"prices_{ticker}.csv")
        print(f"Saved stock history to prices_{ticker}.csv")
        return data

    def load_training_data(self):
        """Loads the Financial PhraseBank for fine-tuning FinBERT."""
        print("Loading Financial PhraseBank dataset...")
        ds = load_dataset("takala/financial_phrasebank", "sentences_allagree", trust_remote_code=True)
        ds["train"].to_pandas().to_csv("financial_phrasebank.csv", index=False)
        print("Saved training data to financial_phrasebank.csv")
        return ds

# --- EXECUTION ---
manager = FinSenseDataManager()

# 1. Fetch Transcripts (Apple, 2022-2024)
transcripts = manager.get_transcripts("AAPL", years=[2022, 2023, 2024])

# 2. Fetch Stock Data
prices = manager.get_stock_history("AAPL", "2022-01-01", "2025-01-01")

# 3. Load Training Dataset
training_ds = manager.load_training_data()
