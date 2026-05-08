import { useState, useEffect } from 'react'
import { Download, ChevronDown, ChevronUp } from 'lucide-react'
import Card from '../components/Card'
import client from '../api/client'
import { getTickers } from '../api/tickers'

export default function Transcripts() {
  const [transcripts, setTranscripts] = useState<any[]>([])
  const [tickers, setTickers] = useState<any[]>([])
  const [symbol, setSymbol] = useState('')
  const [years, setYears] = useState([2022, 2023, 2024])
  const [expanded, setExpanded] = useState<number | null>(null)
  const [fetching, setFetching] = useState(false)
  const [msg, setMsg] = useState('')

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
          {transcripts.map((t) => (
            <div key={t.id} className="rounded-xl overflow-hidden" style={{ background: '#214055' }}>
              <button
                className="w-full flex items-center justify-between px-4 py-3 text-sm"
                onClick={() => setExpanded(expanded === t.id ? null : t.id)}
              >
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-white">Q{t.quarter} {t.year}</span>
                  <span className="text-xs" style={{ color: '#456E8A' }}>Ticker #{t.ticker_id}</span>
                </div>
                {expanded === t.id ? <ChevronUp size={14} style={{ color: '#456E8A' }} /> : <ChevronDown size={14} style={{ color: '#456E8A' }} />}
              </button>
              {expanded === t.id && (
                <div className="px-4 pb-4 border-t border-white/5">
                  <p className="text-xs leading-relaxed mt-3" style={{ color: '#abc' }}>
                    {t.text.slice(0, 600)}...
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
