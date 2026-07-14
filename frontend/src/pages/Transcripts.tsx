import { useState, useEffect } from 'react'
import { Download, ChevronDown, ChevronUp, BarChart2, Loader } from 'lucide-react'
import Card from '../components/Card'
import client from '../api/client'
import { getTickers } from '../api/tickers'
import { analyzeTranscript } from '../api/sentiment'

const LABEL_COLOR: Record<string, string> = { positive: '#28B098', neutral: '#2497F9', negative: '#e05c5c' }
const LABEL_BG: Record<string, string>    = { positive: '#28B09822', neutral: '#2497F922', negative: '#e05c5c22' }

interface SentimentResult {
  id: number
  label: string
  score_positive: number
  score_neutral: number
  score_negative: number
  chunk_count: number
}

export default function Transcripts() {
  const [transcripts, setTranscripts] = useState<any[]>([])
  const [tickers, setTickers] = useState<any[]>([])
  const [symbol, setSymbol] = useState('')
  const [years, setYears] = useState([2022, 2023, 2024])
  const [expanded, setExpanded] = useState<number | null>(null)
  const [fetching, setFetching] = useState(false)
  const [msg, setMsg] = useState('')
  const [analyzing, setAnalyzing] = useState<Record<number, boolean>>({})
  const [sentimentMap, setSentimentMap] = useState<Record<number, SentimentResult>>({})
  const [analysisError, setAnalysisError] = useState<Record<number, string>>({})

  const load = () => client.get('/transcripts').then((r) => setTranscripts(r.data))
  useEffect(() => {
    load()
    getTickers().then((r) => setTickers(r.data))
  }, [])

  const fetch_ = async () => {
    if (!symbol) return
    setFetching(true)
    setMsg('')
    try {
      await client.post('/transcripts/fetch', { symbol, years })
      setMsg(`Fetching ${symbol} transcripts in background. Refresh in a moment.`)
      setTimeout(load, 5000)
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Failed to fetch')
    } finally {
      setFetching(false)
    }
  }

  const runAnalysis = async (transcriptId: number) => {
    setAnalyzing((prev) => ({ ...prev, [transcriptId]: true }))
    setAnalysisError((prev) => ({ ...prev, [transcriptId]: '' }))
    try {
      const r = await analyzeTranscript(transcriptId)
      setSentimentMap((prev) => ({ ...prev, [transcriptId]: r.data }))
    } catch (e: any) {
      setAnalysisError((prev) => ({
        ...prev,
        [transcriptId]: e.response?.data?.detail || 'Analysis failed. Is the model trained?',
      }))
    } finally {
      setAnalyzing((prev) => ({ ...prev, [transcriptId]: false }))
    }
  }

  const toggleYear = (y: number) =>
    setYears((prev) => prev.includes(y) ? prev.filter((x) => x !== y) : [...prev, y])

  const selectStyle = { background: '#214055', border: '1px solid rgba(255,255,255,0.08)', color: symbol ? '#fff' : '#456E8A' }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">Transcripts</h2>
        <p className="text-sm mt-1" style={{ color: '#456E8A' }}>Earnings call transcripts stored in the database</p>
      </div>

      <Card className="mb-6">
        <h3 className="text-sm font-semibold text-white mb-4">Fetch New Transcripts</h3>
        {msg && <p className="text-xs mb-3" style={{ color: '#28B098' }}>{msg}</p>}
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs mb-2" style={{ color: '#456E8A' }}>Ticker</label>
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className="px-3 py-2 rounded-lg text-sm outline-none" style={selectStyle}>
              <option value="">Select ticker</option>
              {tickers.map((t) => <option key={t.id} value={t.symbol}>{t.symbol}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs mb-2" style={{ color: '#456E8A' }}>Years</label>
            <div className="flex gap-2">
              {[2022, 2023, 2024].map((y) => (
                <button
                  key={y}
                  onClick={() => toggleYear(y)}
                  className="px-3 py-2 rounded-lg text-xs font-medium transition-all"
                  style={years.includes(y) ? { background: '#28B09833', color: '#28B098', border: '1px solid #28B09866' } : { background: '#214055', color: '#456E8A', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  {y}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={fetch_}
            disabled={fetching || !symbol}
            className="btn-gradient px-5 py-2 rounded-lg text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
          >
            <Download size={14} /> {fetching ? 'Queued...' : 'Fetch'}
          </button>
        </div>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-white mb-4">{transcripts.length} Transcripts</h3>
        <div className="space-y-3">
          {transcripts.length === 0 && <p className="text-sm" style={{ color: '#456E8A' }}>No transcripts yet.</p>}
          {transcripts.map((t) => {
            const sentiment = sentimentMap[t.id]
            const isAnalyzing = analyzing[t.id]
            const err = analysisError[t.id]
            return (
              <div key={t.id} className="rounded-xl overflow-hidden" style={{ background: '#214055' }}>
                <button
                  className="w-full flex items-center justify-between px-4 py-3 text-sm"
                  onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-white">Q{t.quarter} {t.year}</span>
                    <span className="text-xs" style={{ color: '#456E8A' }}>Ticker #{t.ticker_id}</span>
                    {/* Show sentiment badge in collapsed state too if already analyzed */}
                    {sentiment && expanded !== t.id && (
                      <span
                        className="text-xs px-2 py-0.5 rounded-full font-medium capitalize"
                        style={{ background: LABEL_BG[sentiment.label], color: LABEL_COLOR[sentiment.label] }}
                      >
                        {sentiment.label}
                      </span>
                    )}
                  </div>
                  {expanded === t.id ? <ChevronUp size={14} style={{ color: '#456E8A' }} /> : <ChevronDown size={14} style={{ color: '#456E8A' }} />}
                </button>

                {expanded === t.id && (
                  <div className="px-4 pb-4 border-t border-white/5">
                    {/* Transcript preview */}
                    <p className="text-xs leading-relaxed mt-3 mb-4" style={{ color: '#abc' }}>
                      {t.text.slice(0, 600)}...
                    </p>

                    {/* Analyze button */}
                    {!sentiment && (
                      <div className="mb-3">
                        {err && <p className="text-red-400 text-xs mb-2">{err}</p>}
                        <button
                          onClick={() => runAnalysis(t.id)}
                          disabled={isAnalyzing}
                          className="btn-gradient px-4 py-2 rounded-lg text-white text-xs font-medium flex items-center gap-2 disabled:opacity-60"
                        >
                          {isAnalyzing
                            ? <><Loader size={12} className="animate-spin" /> Analyzing…</>
                            : <><BarChart2 size={12} /> Analyze Sentiment</>}
                        </button>
                      </div>
                    )}

                    {/* Inline sentiment result */}
                    {sentiment && (
                      <div className="rounded-xl p-4 mt-2" style={{ background: '#15293A' }}>
                        <div className="flex items-center gap-3 mb-3">
                          <span
                            className="px-3 py-1 rounded-full text-xs font-semibold capitalize"
                            style={{ background: LABEL_BG[sentiment.label], color: LABEL_COLOR[sentiment.label] }}
                          >
                            {sentiment.label}
                          </span>
                          <span className="text-xs" style={{ color: '#456E8A' }}>
                            {sentiment.chunk_count} chunk{sentiment.chunk_count !== 1 ? 's' : ''} analyzed
                          </span>
                        </div>
                        <div className="space-y-2">
                          {[
                            { label: 'Positive', key: 'score_positive' as const, color: '#28B098' },
                            { label: 'Neutral',  key: 'score_neutral'  as const, color: '#2497F9' },
                            { label: 'Negative', key: 'score_negative' as const, color: '#e05c5c' },
                          ].map(({ label, key, color }) => (
                            <div key={key}>
                              <div className="flex justify-between text-xs mb-1">
                                <span style={{ color: '#456E8A' }}>{label}</span>
                                <span className="font-medium" style={{ color }}>{(sentiment[key] * 100).toFixed(1)}%</span>
                              </div>
                              <div className="h-1.5 rounded-full" style={{ background: '#214055' }}>
                                <div
                                  className="h-1.5 rounded-full transition-all duration-500"
                                  style={{ width: `${sentiment[key] * 100}%`, background: color }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                        <button
                          onClick={() => setSentimentMap((prev) => { const n = { ...prev }; delete n[t.id]; return n })}
                          className="mt-3 text-xs hover:underline"
                          style={{ color: '#456E8A' }}
                        >
                          Re-analyze
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}
