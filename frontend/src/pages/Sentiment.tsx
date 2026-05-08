import { useState, useEffect } from 'react'
import { Send } from 'lucide-react'
import Card from '../components/Card'
import { analyzeSentiment, getSentimentResults } from '../api/sentiment'
import { getTickers } from '../api/tickers'

const LABEL_COLOR: Record<string, string> = { positive: '#28B098', neutral: '#2497F9', negative: '#e05c5c' }
const LABEL_BG: Record<string, string>    = { positive: '#28B09822', neutral: '#2497F922', negative: '#e05c5c22' }

export default function Sentiment() {
  const [text, setText] = useState('')
  const [ticker, setTicker] = useState('')
  const [tickers, setTickers] = useState<any[]>([])
  const [results, setResults] = useState<any[]>([])
  const [latest, setLatest] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = () => getSentimentResults().then((r) => setResults(r.data))
  useEffect(() => {
    getTickers().then((r) => setTickers(r.data))
    load()
  }, [])

  const analyze = async () => {
    if (!text.trim()) return
    setError('')
    setLoading(true)
    try {
      const r = await analyzeSentiment(text, ticker || undefined)
      setLatest(r.data)
      setText('')
      load()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Analysis failed. Is the model trained?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">Sentiment Analysis</h2>
        <p className="text-sm mt-1" style={{ color: '#456E8A' }}>Analyze financial text using fine-tuned FinBERT</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        {/* Input */}
        <Card>
          <h3 className="text-sm font-semibold text-white mb-4">Analyze Text</h3>
          {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            className="w-full px-4 py-3 rounded-xl text-white text-sm outline-none resize-none mb-3"
            style={{ background: '#214055', border: '1px solid rgba(255,255,255,0.08)' }}
            placeholder="Paste an earnings call excerpt, forward-looking statement, or any financial text..."
          />
          <div className="flex gap-3">
            <select
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="flex-1 px-3 py-2 rounded-lg text-sm outline-none"
              style={{ background: '#214055', border: '1px solid rgba(255,255,255,0.08)', color: ticker ? '#fff' : '#456E8A' }}
            >
              <option value="">Ticker (optional)</option>
              {tickers.map((t) => <option key={t.id} value={t.symbol}>{t.symbol}</option>)}
            </select>
            <button
              onClick={analyze}
              disabled={loading || !text.trim()}
              className="btn-gradient px-5 py-2 rounded-lg text-white text-sm font-medium flex items-center gap-2 disabled:opacity-60"
            >
              <Send size={14} /> {loading ? 'Analyzing...' : 'Analyze'}
            </button>
          </div>
        </Card>

        {/* Result */}
        {latest && (
          <Card>
            <h3 className="text-sm font-semibold text-white mb-4">Result</h3>
            <div className="flex items-center gap-3 mb-5">
              <span
                className="px-4 py-1.5 rounded-full text-sm font-semibold capitalize"
                style={{ background: LABEL_BG[latest.label], color: LABEL_COLOR[latest.label] }}
              >
                {latest.label}
              </span>
            </div>
            <p className="text-xs mb-5 leading-relaxed" style={{ color: '#456E8A' }}>"{latest.input_text.slice(0, 120)}..."</p>
            <div className="space-y-3">
              {[
                { label: 'Positive', key: 'score_positive', color: '#28B098' },
                { label: 'Neutral',  key: 'score_neutral',  color: '#2497F9' },
                { label: 'Negative', key: 'score_negative', color: '#e05c5c' },
              ].map(({ label, key, color }) => (
                <div key={key}>
                  <div className="flex justify-between text-xs mb-1">
                    <span style={{ color: '#456E8A' }}>{label}</span>
                    <span className="font-medium" style={{ color }}>{(latest[key] * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-2 rounded-full" style={{ background: '#214055' }}>
                    <div className="h-2 rounded-full transition-all" style={{ width: `${latest[key] * 100}%`, background: color }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* History */}
      <Card>
        <h3 className="text-sm font-semibold text-white mb-4">Analysis History</h3>
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {results.length === 0 && <p className="text-sm" style={{ color: '#456E8A' }}>No analyses yet.</p>}
          {results.map((r) => (
            <div key={r.id} className="flex items-start justify-between gap-4 p-3 rounded-xl" style={{ background: '#214055' }}>
              <p className="text-xs flex-1 leading-relaxed" style={{ color: '#abc' }}>
                {r.input_text.slice(0, 100)}...
              </p>
              <span
                className="shrink-0 text-xs px-2 py-0.5 rounded-full font-medium capitalize"
                style={{ background: LABEL_BG[r.label], color: LABEL_COLOR[r.label] }}
              >
                {r.label}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
