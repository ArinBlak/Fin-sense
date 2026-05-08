import { useEffect, useState } from 'react'
import { Plus, Trash2, Pencil, X, Check } from 'lucide-react'
import Card from '../components/Card'
import { getTickers, createTicker, updateTicker, deleteTicker } from '../api/tickers'

interface Ticker { id: number; symbol: string; company_name?: string; sector?: string }

export default function Tickers() {
  const [tickers, setTickers] = useState<Ticker[]>([])
  const [form, setForm] = useState({ symbol: '', company_name: '', sector: '' })
  const [editId, setEditId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ company_name: '', sector: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const load = () => getTickers().then((r) => setTickers(r.data))
  useEffect(() => { load() }, [])

  const add = async () => {
    if (!form.symbol) return
    setError('')
    setLoading(true)
    try {
      await createTicker(form)
      setForm({ symbol: '', company_name: '', sector: '' })
      load()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to add ticker')
    } finally {
      setLoading(false)
    }
  }

  const save = async (id: number) => {
    await updateTicker(id, editForm)
    setEditId(null)
    load()
  }

  const remove = async (id: number) => {
    await deleteTicker(id)
    load()
  }

  const inputClass = "px-3 py-2 rounded-lg text-white text-sm outline-none w-full"
  const inputStyle = { background: '#214055', border: '1px solid rgba(255,255,255,0.08)' }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">Tickers</h2>
        <p className="text-sm mt-1" style={{ color: '#456E8A' }}>Manage the stocks you're tracking</p>
      </div>

      {/* Add form */}
      <Card className="mb-6">
        <h3 className="text-sm font-semibold text-white mb-4">Add Ticker</h3>
        {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          {[
            { key: 'symbol', ph: 'AAPL *' },
            { key: 'company_name', ph: 'Company Name' },
            { key: 'sector', ph: 'Sector' },
          ].map(({ key, ph }) => (
            <input
              key={key}
              className={inputClass}
              style={inputStyle}
              placeholder={ph}
              value={(form as any)[key]}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            />
          ))}
          <button
            onClick={add}
            disabled={loading}
            className="btn-gradient px-4 py-2 rounded-lg text-white text-sm font-medium flex items-center gap-2 justify-center disabled:opacity-60"
          >
            <Plus size={15} /> Add
          </button>
        </div>
      </Card>

      {/* Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ color: '#456E8A', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <th className="text-left pb-3 font-medium">Symbol</th>
                <th className="text-left pb-3 font-medium">Company</th>
                <th className="text-left pb-3 font-medium">Sector</th>
                <th className="text-right pb-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {tickers.length === 0 && (
                <tr><td colSpan={4} className="py-8 text-center" style={{ color: '#456E8A' }}>No tickers yet</td></tr>
              )}
              {tickers.map((t) => (
                <tr key={t.id}>
                  <td className="py-3">
                    <span className="font-semibold px-2 py-1 rounded-lg text-xs" style={{ background: '#2497F922', color: '#2497F9' }}>
                      {t.symbol}
                    </span>
                  </td>
                  <td className="py-3 text-white">
                    {editId === t.id
                      ? <input className={inputClass} style={inputStyle} value={editForm.company_name} onChange={(e) => setEditForm({ ...editForm, company_name: e.target.value })} />
                      : t.company_name || <span style={{ color: '#456E8A' }}>—</span>}
                  </td>
                  <td className="py-3 text-white">
                    {editId === t.id
                      ? <input className={inputClass} style={inputStyle} value={editForm.sector} onChange={(e) => setEditForm({ ...editForm, sector: e.target.value })} />
                      : t.sector || <span style={{ color: '#456E8A' }}>—</span>}
                  </td>
                  <td className="py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {editId === t.id ? (
                        <>
                          <button onClick={() => save(t.id)} className="p-1.5 rounded-lg hover:bg-white/10" style={{ color: '#28B098' }}><Check size={14} /></button>
                          <button onClick={() => setEditId(null)} className="p-1.5 rounded-lg hover:bg-white/10" style={{ color: '#456E8A' }}><X size={14} /></button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => { setEditId(t.id); setEditForm({ company_name: t.company_name || '', sector: t.sector || '' }) }} className="p-1.5 rounded-lg hover:bg-white/10" style={{ color: '#456E8A' }}><Pencil size={14} /></button>
                          <button onClick={() => remove(t.id)} className="p-1.5 rounded-lg hover:bg-white/10 text-red-400"><Trash2 size={14} /></button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
