import client from './client'

export const startTraining = (data: { epochs: number; batch_size: number; learning_rate: number }) =>
  client.post('/training', data)

export const getTrainingRuns = () => client.get('/training')
export const getTrainingRun = (id: number) => client.get(`/training/${id}`)
export const getLatestRun = () => client.get('/training/latest')
