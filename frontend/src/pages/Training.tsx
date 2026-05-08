import { useState, useEffect, useRef } from 'react'
import { Play, RefreshCw } from 'lucide-react'
import Card from '../components/Card'
import { startTraining, getTrainingRuns, getTrainingRun } from '../api/training'

const STATUS_COLOR: Record<string, string> = { pending: '#2497F9', running: '#f59e0b', completed: '#28B098', failed: '#e05c5c' }

export default function Training() {
  const [runs, setRuns] = useState<any[]>([])
  const [form, setForm] = useState({ epochs: 5, batch_size: 16, learning_rate: 0.00002 })
  const [activeRun, setActiveRun] = useState<any>(null)
  const [error, setError] = useState('')
  const [launching, setLaunching] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadRuns = () => getTrainingRuns().then((r) => setRuns(r.data)).catch(() => {})

  useEffect(() => {
    loadRuns()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    if (activeRun && (activeRun.status === 'pending' || activeRun.status === 'running')) {
      pollRef.current = setInterval(async () => {
        const r = await getTrainingRun(activeRun.id)
        setActiveRun(r.data)
        if (r.data.status === 'completed' || r.data.status === 'failed') {
          clearInterval(pollRef.current!)
          loadRuns()
        }
      }, 5000)
    }
  }, [activeRun?.id, activeRun?.status])

  const launch = async () => {
    setError('')
    setLaunching(true)
    try {
      const r = await startTraining(form)
      setActiveRun(r.data)
      loadRuns()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to start training')
    } finally {
      setLaunching(false)
    }
  }

  const inputClass = "px-3 py-2 rounded-lg text-white text-sm outline-none w-full"
  const inputStyle = { background: '#214055', border: '1px solid rgba(255,255,255,0.08)' }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">Training</h2>
        <p className="text-sm mt-1" style={{ color: '#456E8A' }}>Fine-tune FinBERT on Financial PhraseBank</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        {/* Config */}
        <Card>
          <h3 className="text-sm font-semibold text-white mb-4">Launch Training Run</h3>
          {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
          <div className="space-y-4">
            {[
              { label: 'Epochs', key: 'epochs', type: 'number', min: 1, max: 20 },
              { label: 'Batch Size', key: 'batch_size', type: 'number', min: 4, max: 64 },
              { label: 'Learning Rate', key: 'learning_rate', type: 'number', step: 0.000001 },
            ].map(({ label, key, ...rest }) => (
              <div key={key}>
                <label className="block text-xs font-medium mb-2" style={{ color: '#456E8A' }}>{label}</label>
                <input
                  {...rest}
                  className={inputClass}
                  style={inputStyle}
                  value={(form as any)[key]}
                  onChange={(e) => setForm({ ...form, [key]: parseFloat(e.target.value) })}
                />
              </div>
            ))}
            <button
              onClick={launch}
              disabled={launching || activeRun?.status === 'running' || activeRun?.status === 'pending'}
              className="btn-gradient w-full py-3 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <Play size={15} /> {launching ? 'Launching...' : 'Start Training'}
            </button>
          </div>
        </Card>

        {/* Active run */}
        {activeRun && (
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">Run #{activeRun.id}</h3>
              <div className="flex items-center gap-2">
                {(activeRun.status === 'pending' || activeRun.status === 'running') && (
                  <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: STATUS_COLOR[activeRun.status] }} />
                )}
                <span className="text-xs font-medium capitalize" style={{ color: STATUS_COLOR[activeRun.status] }}>
                  {activeRun.status}
                </span>
              </div>
            </div>
            <div className="space-y-3 text-sm">
              {[
                ['Epochs', activeRun.epochs],
                ['Batch Size', activeRun.batch_size],
                ['Learning Rate', activeRun.learning_rate],
                ...(activeRun.test_accuracy != null ? [['Test Accuracy', `${(activeRun.test_accuracy * 100).toFixed(2)}%`]] : []),
                ...(activeRun.test_f1 != null ? [['Macro F1', activeRun.test_f1.toFixed(4)]] : []),
              ].map(([k, v]) => (
                <div key={String(k)} className="flex justify-between">
                  <span style={{ color: '#456E8A' }}>{k}</span>
                  <span className="text-white font-medium">{v}</span>
                </div>
              ))}
            </div>
            {activeRun.log_output && (
              <div className="mt-4">
                <p className="text-xs font-medium mb-2" style={{ color: '#456E8A' }}>Log output (last entries)</p>
                <pre className="text-xs rounded-lg p-3 overflow-auto max-h-40 leading-relaxed" style={{ background: '#081F30', color: '#28B098' }}>
                  {activeRun.log_output.split('\n').slice(-20).join('\n')}
                </pre>
              </div>
            )}
          </Card>
        )}
      </div>

      {/* Run history */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">Run History</h3>
          <button onClick={loadRuns} className="p-1.5 rounded-lg hover:bg-white/10" style={{ color: '#456E8A' }}><RefreshCw size={14} /></button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ color: '#456E8A', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                {['ID', 'Status', 'Epochs', 'Accuracy', 'F1', 'Started'].map((h) => (
                  <th key={h} className="text-left pb-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {runs.length === 0 && <tr><td colSpan={6} className="py-8 text-center" style={{ color: '#456E8A' }}>No runs yet</td></tr>}
              {runs.map((r) => (
                <tr key={r.id} className="cursor-pointer hover:bg-white/5" onClick={() => setActiveRun(r)}>
                  <td className="py-3 text-white">#{r.id}</td>
                  <td className="py-3">
                    <span className="text-xs font-medium capitalize" style={{ color: STATUS_COLOR[r.status] }}>{r.status}</span>
                  </td>
                  <td className="py-3 text-white">{r.epochs}</td>
                  <td className="py-3 text-white">{r.test_accuracy != null ? `${(r.test_accuracy * 100).toFixed(2)}%` : '—'}</td>
                  <td className="py-3 text-white">{r.test_f1 != null ? r.test_f1.toFixed(4) : '—'}</td>
                  <td className="py-3" style={{ color: '#456E8A' }}>{r.started_at ? new Date(r.started_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
