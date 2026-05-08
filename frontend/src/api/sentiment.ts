import client from './client'

export const analyzeSentiment = (text: string, ticker_symbol?: string) =>
  client.post('/sentiment', { text, ticker_symbol })

export const getSentimentResults = (ticker_id?: number) =>
  client.get('/sentiment', { params: ticker_id ? { ticker_id } : {} })
