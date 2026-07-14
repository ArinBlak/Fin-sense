import { useEffect, useState } from 'react'
import { TrendingUp, Activity, Brain, BarChart2 } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ComposedChart, Line, Scatter, CartesianGrid,
} from 'recharts'
import Card from '../components/Card'
import { getTickers, getTickerPrices } from '../api/tickers'
import { getSentimentResults } from '../api/sentiment'
import { getLatestRun } from '../api/training'
import { useAuth } from '../context/AuthContext'

const LABEL_COLOR: Record<string, string> = {
  positive: '#28B098',
  neutral:  '#2497F9',
  negative: '#e05c5c',
}

// Custom dot for sentiment scatter on the price chart
const SentimentDot = (props: any) => {
  const { cx, cy, payload } = props
  if (!payload?.sentimentLabel) return null
  const color = LABEL_COLOR[payload.sentimentLabel] || '#888'
  return (
    <circle
      cx={cx}
      cy={cy}
      r={6}
      fill={color}
      stroke="#081F30"
      strokeWidth={2}
    />
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const [tickers, setTickers] = useState<any[]>([])
  const [results, setResults] = useState<any[]>([])
  const [latestRun, setLatestRun] = useState<any>(null)

  // Correlation chart state
  const [selectedTickerId, setSelectedTickerId] = useState<number | null>(null)
  const [priceData, setPriceData] = useState<any[]>([])
  const [priceLoading, setPriceLoading] = useState(false)

  useEffect(() => {
    getTickers().then((r) => {
      setTickers(r.data)
      // Auto-select first ticker
      if (r.data.length > 0) setSelectedTickerId(r.data[0].id)
    }).catch(() => {})
    getSentimentResults().then((r) => setResults(r.data)).catch(() => {})
    getLatestRun().then((r) => setLatestRun(r.data)).catch(() => {})
  }, [])

  // Fetch prices whenever the selected ticker changes
  useEffect(() => {
    if (!selectedTickerId) { setPriceData([]); return }
    setPriceLoading(true)
    getTickerPrices(selectedTickerId)
      .then((r) => {
        // Merge sentiment events onto price rows by date
        const sentimentByDate: Record<string, any> = {}
        results
          .filter((res) => res.ticker_id === selectedTickerId && res.transcript_id != null)
          .forEach((res) => {
            const d = res.created_at?.split('T')[0]
            if (d) sentimentByDate[d] = res
          })

        const merged = (r.data as any[]).map((p: any) => ({
          date: p.date,
          close: parseFloat(p.close.toFixed(2)),
          // Attach the sentiment event closest to this date (if any)
          sentimentLabel: sentimentByDate[p.date]?.label ?? null,
          sentimentScore: sentimentByDate[p.date]?.score_positive ?? null,
        }))
        setPriceData(merged)
      })
      .catch(() => setPriceData([]))
      .finally(() => setPriceLoading(false))
  }, [selectedTickerId, results])

  const sentimentCounts = results.reduce(
    (acc, r) => { acc[r.label] = (acc[r.label] || 0) + 1; return acc },
    { positive: 0, neutral: 0, negative: 0 } as Record<string, number>
  )

  const chartData = results.slice(-20).map((r, i) => ({
    i: i + 1,
    positive: r.score_positive,
    neutral: r.score_neutral,
    negative: r.score_negative,
  }))

  const stats = [
    { label: 'Tracked Tickers', value: tickers.length, icon: TrendingUp, color: '#2497F9' },
    { label: 'Analyses Run',    value: results.length, icon: Activity,   color: '#28B098' },
    { label: 'Positive',  value: sentimentCounts.positive, icon: TrendingUp, color: '#28B098' },
    { label: 'Negative',  value: sentimentCounts.negative, icon: Activity,   color: '#e05c5c' },
  ]

  const selectedTicker = tickers.find((t) => t.id === selectedTickerId)
  const sentimentDotData = priceData.filter((p) => p.sentimentLabel)

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white">Welcome back, {user?.username} 👋</h2>
        <p className="text-sm mt-1" style={{ color: '#456E8A' }}>Here's your FinSense overview</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm" style={{ color: '#456E8A' }}>{label}</span>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: color + '22' }}>
                <Icon size={16} style={{ color }} />
              </div>
            </div>
            <p className="text-3xl font-bold text-white">{value}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        {/* Sentiment chart */}
        <Card className="xl:col-span-2">
          <h3 className="text-sm font-semibold text-white mb-4">Recent Sentiment Scores</h3>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData}>
                <defs>
                  {[['pos', '#28B098'], ['neu', '#2497F9'], ['neg', '#e05c5c']].map(([k, c]) => (
                    <linearGradient key={k} id={k} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={c} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={c} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <XAxis dataKey="i" tick={{ fill: '#456E8A', fontSize: 11 }} />
                <YAxis tick={{ fill: '#456E8A', fontSize: 11 }} domain={[0, 1]} />
                <Tooltip contentStyle={{ background: '#214055', border: 'none', borderRadius: 8, color: '#fff', fontSize: 12 }} />
                <Area type="monotone" dataKey="positive" stroke="#28B098" fill="url(#pos)" strokeWidth={2} />
                <Area type="monotone" dataKey="neutral"  stroke="#2497F9" fill="url(#neu)" strokeWidth={2} />
                <Area type="monotone" dataKey="negative" stroke="#e05c5c" fill="url(#neg)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center" style={{ color: '#456E8A' }}>
              No sentiment data yet. Run an analysis to see results.
            </div>
          )}
        </Card>

        {/* Latest training run */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Brain size={16} style={{ color: '#28B098' }} />
            <h3 className="text-sm font-semibold text-white">Latest Training Run</h3>
          </div>
          {latestRun ? (
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span style={{ color: '#456E8A' }}>Status</span>
                <span className="font-medium capitalize" style={{ color: latestRun.status === 'completed' ? '#28B098' : latestRun.status === 'failed' ? '#e05c5c' : '#2497F9' }}>
                  {latestRun.status}
                </span>
              </div>
              {latestRun.test_accuracy != null && (
                <div className="flex justify-between text-sm">
                  <span style={{ color: '#456E8A' }}>Accuracy</span>
                  <span className="font-semibold text-white">{(latestRun.test_accuracy * 100).toFixed(2)}%</span>
                </div>
              )}
              {latestRun.test_f1 != null && (
                <div className="flex justify-between text-sm">
                  <span style={{ color: '#456E8A' }}>Macro F1</span>
                  <span className="font-semibold text-white">{latestRun.test_f1.toFixed(4)}</span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span style={{ color: '#456E8A' }}>Epochs</span>
                <span className="text-white">{latestRun.epochs}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm" style={{ color: '#456E8A' }}>No training runs yet.</p>
          )}
        </Card>
      </div>

      {/* Stock Price + Sentiment Correlation */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BarChart2 size={16} style={{ color: '#2497F9' }} />
            <h3 className="text-sm font-semibold text-white">Stock Price vs. Sentiment Events</h3>
          </div>
          {tickers.length > 0 && (
            <select
              value={selectedTickerId ?? ''}
              onChange={(e) => setSelectedTickerId(Number(e.target.value))}
              className="px-3 py-1.5 rounded-lg text-sm outline-none"
              style={{ background: '#214055', border: '1px solid rgba(255,255,255,0.08)', color: '#fff' }}
            >
              {tickers.map((t) => (
                <option key={t.id} value={t.id}>{t.symbol}</option>
              ))}
            </select>
          )}
        </div>

        {tickers.length === 0 && (
          <div className="h-[240px] flex items-center justify-center" style={{ color: '#456E8A' }}>
            Add tickers to see stock price data.
          </div>
        )}

        {tickers.length > 0 && priceLoading && (
          <div className="h-[240px] flex items-center justify-center" style={{ color: '#456E8A' }}>
            Loading price data…
          </div>
        )}

        {tickers.length > 0 && !priceLoading && priceData.length === 0 && (
          <div className="h-[240px] flex items-center justify-center text-center" style={{ color: '#456E8A' }}>
            <div>
              <p>No price data for {selectedTicker?.symbol} yet.</p>
              <p className="text-xs mt-1">Price history is fetched automatically when you add a ticker.</p>
            </div>
          </div>
        )}

        {!priceLoading && priceData.length > 0 && (
          <>
            {/* Legend for scatter dots */}
            <div className="flex items-center gap-5 mb-3 text-xs" style={{ color: '#456E8A' }}>
              <span className="font-medium text-white">{selectedTicker?.symbol} — 3yr Close Price</span>
              {(['positive', 'neutral', 'negative'] as const).map((l) => (
                <span key={l} className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: LABEL_COLOR[l] }} />
                  {l.charAt(0).toUpperCase() + l.slice(1)} call
                </span>
              ))}
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={priceData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#456E8A', fontSize: 10 }}
                  tickFormatter={(v) => v?.slice(0, 7) ?? ''}
                  interval={Math.floor(priceData.length / 6)}
                />
                <YAxis
                  tick={{ fill: '#456E8A', fontSize: 10 }}
                  tickFormatter={(v) => `$${v}`}
                  width={55}
                />
                <Tooltip
                  contentStyle={{ background: '#214055', border: 'none', borderRadius: 8, color: '#fff', fontSize: 12 }}
                  formatter={(value: any, name?: any) => {
                    if (name === 'close') return [`$${value}`, 'Close']
                    return [value, name]
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="close"
                  stroke="#2497F9"
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 4, fill: '#2497F9' }}
                />
                {/* Render a Scatter layer just for sentiment-tagged points */}
                <Scatter
                  data={sentimentDotData}
                  dataKey="close"
                  shape={<SentimentDot />}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </>
        )}
      </Card>
    </div>
  )
}
