import { useEffect, useState } from 'react'
import { TrendingUp, Activity, Brain } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import Card from '../components/Card'
import { getTickers } from '../api/tickers'
import { getSentimentResults } from '../api/sentiment'
import { getLatestRun } from '../api/training'
import { useAuth } from '../context/AuthContext'

export default function Dashboard() {
  const { user } = useAuth()
  const [tickers, setTickers] = useState<any[]>([])
  const [results, setResults] = useState<any[]>([])
  const [latestRun, setLatestRun] = useState<any>(null)

  useEffect(() => {
    getTickers().then((r) => setTickers(r.data)).catch(() => {})
    getSentimentResults().then((r) => setResults(r.data)).catch(() => {})
    getLatestRun().then((r) => setLatestRun(r.data)).catch(() => {})
  }, [])

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

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Sentiment chart */}
        <Card className="xl:col-span-2">
          <h3 className="text-sm font-semibold text-white mb-4">Recent Sentiment Scores</h3>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData}>
                <defs>
                  {[['pos', '#28B098'], ['neu', '#2497F9'], ['neg', '#e05c5c']].map(([k, c]) => (
                    <linearGradient key={k} id={k} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={c} stopOpacity={0.3} />
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
    </div>
  )
}
