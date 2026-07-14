import client from './client'

export const analyzeSentiment = (text: string, ticker_symbol?: string) =>
  client.post('/sentiment', { text, ticker_symbol })

export const analyzeTranscript = (transcriptId: number) =>
  client.post<{ id: number; label: string; score_positive: number; score_neutral: number; score_negative: number; chunk_count: number }>(
    `/sentiment/transcript/${transcriptId}`
  )

export const getSentimentResults = (ticker_id?: number) =>
  client.get('/sentiment', { params: ticker_id ? { ticker_id } : {} })
