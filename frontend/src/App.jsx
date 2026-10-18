
import { useState, useEffect } from 'react'
import {
  Activity, CheckCircle2, Copy, AlertTriangle,
  Send, Server, RefreshCw, Zap
} from 'lucide-react'

const initialEvent = {
  event_id: '',
  event_type: 'payment.completed',
  payload: '{\n  "amount": 1500,\n  "currency": "INR"\n}'
}

export default function App() {
  const [form, setForm] = useState(initialEvent)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [health, setHealth] = useState('Checking')
  useEffect(() => {
  checkHealth()
}, [])

  async function checkHealth() {
    try {
      const response = await fetch('/api/health')
      if (!response.ok) throw new Error()
      setHealth('Online')
    } catch {
      setHealth('Offline')
    }
  }

  async function submitEvent(e) {
    e.preventDefault()
    setError('')

    let payload
    try {
      payload = JSON.parse(form.payload)
      if (!payload || Array.isArray(payload) || typeof payload !== 'object') {
        throw new Error()
      }
    } catch {
      setError('Payload must be a valid JSON object.')
      return
    }

    setLoading(true)

    try {
      const response = await fetch('/api/webhooks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: form.event_id,
          event_type: form.event_type,
          payload
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Request failed')
      }

      setEvents(previous => [{
        id: form.event_id,
        type: form.event_type,
        status: data.status,
        time: new Date().toLocaleTimeString()
      }, ...previous])

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const processed = events.filter(e => e.status === 'processed').length
  const duplicates = events.filter(e => e.status === 'duplicate').length
  const accepted = events.filter(e => e.status === 'accepted').length

  const stats = [
    { label: 'Requests Submitted', value: events.length, icon: Activity },
    { label: 'Processed (Demo)', value: processed, icon: CheckCircle2 },
    { label: 'Duplicates Detected', value: duplicates, icon: Copy },
    { label: 'Queued (Full Mode)', value: accepted, icon: Zap }
  ]

  return (
    <div className="min-h-screen bg-[#090f1d] text-slate-100">
      <header className="border-b border-slate-800 bg-[#101827]">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-indigo-600 p-2">
              <Zap size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold">EventFlow</h1>
              <p className="text-xs text-slate-400">Event Processing Dashboard</p>
            </div>
          </div>
          <button
            onClick={checkHealth}
            className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm"
          >
            <Server size={16} />
            Backend: {health}
            <RefreshCw size={14} />
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-8 px-6 py-10">
        <section>
          <h2 className="text-3xl font-bold">Event Processing Overview</h2>
          <p className="mt-2 text-slate-400">
            Submit webhook events and inspect API responses in real time.
          </p>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map(stat => (
            <div key={stat.label} className="rounded-2xl border border-slate-800 bg-[#131e30] p-6">
              <stat.icon className="mb-4 text-indigo-400" size={25} />
              <p className="text-sm text-slate-400">{stat.label}</p>
              <p className="mt-2 text-3xl font-bold">{stat.value}</p>
            </div>
          ))}
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-[#131e30] p-6">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-semibold">
              <Send size={20} /> Submit Webhook Event
            </h3>

            <form onSubmit={submitEvent} className="space-y-5">
              <div>
                <label className="mb-2 block text-sm">Event ID</label>
                <input
                  required
                  value={form.event_id}
                  onChange={e => setForm({ ...form, event_id: e.target.value })}
                  placeholder="event_001"
                  className="w-full rounded-lg border border-slate-700 bg-[#090f1d] p-3 outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm">Event Type</label>
                <select
                  value={form.event_type}
                  onChange={e => setForm({ ...form, event_type: e.target.value })}
                  className="w-full rounded-lg border border-slate-700 bg-[#090f1d] p-3"
                >
                  <option value="payment.completed">payment.completed</option>
                  <option value="order.created">order.created</option>
                  <option value="user.registered">user.registered</option>
                  <option value="payment.failed">payment.failed</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm">JSON Payload</label>
                <textarea
                  rows={6}
                  value={form.payload}
                  onChange={e => setForm({ ...form, payload: e.target.value })}
                  className="w-full rounded-lg border border-slate-700 bg-[#090f1d] p-3 font-mono text-sm outline-none focus:border-indigo-500"
                />
              </div>

              {error && (
                <p className="flex items-center gap-2 text-sm text-red-400">
                  <AlertTriangle size={16} /> {error}
                </p>
              )}

              <button
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-3 font-semibold hover:bg-indigo-500 disabled:opacity-50"
              >
                <Send size={17} />
                {loading ? 'Submitting...' : 'Send Webhook'}
              </button>
            </form>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#131e30] p-6">
            <h3 className="mb-5 text-xl font-semibold">Recent Requests</h3>
            {events.length === 0 ? (
              <div className="flex h-64 flex-col items-center justify-center text-slate-500">
                <Activity size={44} className="mb-4" />
                <p>No requests submitted yet</p>
                <p className="mt-2 text-sm">Send a webhook to see its response.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {events.map((event, index) => (
                  <div key={index} className="flex items-center justify-between rounded-xl border border-slate-700 p-4">
                    <div>
                      <p className="font-medium">{event.id}</p>
                      <p className="text-xs text-slate-400">{event.type} · {event.time}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-medium ${
                      event.status === 'processed'
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : event.status === 'duplicate'
                        ? 'bg-amber-500/15 text-amber-400'
                        : 'bg-indigo-500/15 text-indigo-400'
                    }`}>
                      {event.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <footer className="border-t border-slate-800 pt-6 text-center text-sm text-slate-500">
          EventFlow · FastAPI · React · RabbitMQ · Redis · SQLite
          <p className="mt-2">
            Dashboard statistics reflect requests made in this browser session,
            not system-wide processing metrics.
          </p>
        </footer>
      </main>
    </div>
  )
}
