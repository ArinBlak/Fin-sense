import client from './client'

export const getTickers = () => client.get('/tickers')
export const createTicker = (data: { symbol: string; company_name?: string; sector?: string }) =>
  client.post('/tickers', data)
export const updateTicker = (id: number, data: { company_name?: string; sector?: string }) =>
  client.put(`/tickers/${id}`, data)
export const deleteTicker = (id: number) => client.delete(`/tickers/${id}`)
