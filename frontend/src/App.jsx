import { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts'
import { get } from './api'

const CUTOFFS = [
  { v: 6, label: '06:00 UTC' }, { v: 9, label: '09:00 UTC (default)' },
  { v: 10, label: '10:00 UTC' }, { v: 12, label: '12:00 UTC' },
]
const mw = (n) => (n == null ? '–' : Math.round(n).toLocaleString() + ' MW')
const hhmm = (iso) => iso.slice(11, 16)

function Kpi({ label, value, hint }) {
  return (
    <div className="card kpi">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  )
}

function Panel({ title, desc, children, h = 280 }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <p className="d">{desc}</p>
      <div style={{ height: h }}>{children}</div>
    </div>
  )
}

function useApi(path) {
  const [state, set] = useState({ data: null, error: null, loading: true })
  useEffect(() => {
    let live = true
    set((s) => ({ ...s, loading: true, error: null }))
    get(path)
      .then((data) => live && set({ data, error: null, loading: false }))
      .catch((e) => live && set({ data: null, error: e.message, loading: false }))
    return () => { live = false }
  }, [path])
  return state
}

function DecisionView({ cutoff }) {
  const [day, setDay] = useState('2026-01-15')
  const fc = useApi(`/api/forecast?day=${day}&cutoff=${cutoff}`)
  const acc = useApi(`/api/accuracy?cutoff=${cutoff}`)
  const bias = acc.data?.summary.bias ?? 0

  const rows = useMemo(
    () => (fc.data?.points || []).map((p) => ({
      t: hhmm(p.startTime), forecast: p.forecast, actual: p.actual,
      adjusted: p.forecast - bias,
    })), [fc.data, bias])

  const pubs = (fc.data?.points || []).map((p) => p.publishTime).sort()
  const dayMae = useMemo(() => {
    const e = (fc.data?.points || []).filter((p) => p.error != null).map((p) => Math.abs(p.error))
    return e.length ? e.reduce((a, b) => a + b, 0) / e.length : null
  }, [fc.data])
  const avg = rows.length ? rows.reduce((a, r) => a + r.forecast, 0) / rows.length : null
  const peak = rows.length ? Math.max(...rows.map((r) => r.forecast)) : null
  const low = rows.length ? Math.min(...rows.map((r) => r.forecast)) : null
  const days = Array.from({ length: 31 }, (_, i) => `2026-01-${String(i + 1).padStart(2, '0')}`)

  return (
    <>
      <div className="controls">
        <label>Delivery day
          <select value={day} onChange={(e) => setDay(e.target.value)}>
            {days.map((d) => <option key={d}>{d}</option>)}
          </select>
        </label>
      </div>
      {fc.error && <p className="err">{fc.error}</p>}
      <div className="grid">
        <Kpi label="Avg forecast wind" value={mw(avg)} hint="Day-ahead view at cutoff" />
        <Kpi label="Peak / low" value={`${mw(peak)} / ${mw(low)}`} />
        <Kpi label="Forecast published" value={pubs.length ? hhmm(pubs[0]) + ' UTC' : '–'}
             hint={pubs.length ? pubs[0].slice(0, 10) + ' (latest before cutoff)' : ''} />
        <Kpi label="Day's actual MAE" value={mw(dayMae)} hint="Hindsight check on this day" />
      </div>
      <div className="card insight">
        <b>For the buyer:</b> on {day}, the latest forecast available at the {cutoff}:00 UTC cutoff
        the day before averaged <b>{mw(avg)}</b> of wind. In January 2026 this forecast ran on
        average <b>{mw(bias)}</b> above actual generation, so a bias-adjusted planning figure
        is about <b>{mw(avg == null ? null : avg - bias)}</b>. Plan thermal purchases against that
        lower number, with a buffer of roughly the typical error.
        <div className="muted">Bias adjustment uses January averages (in-sample), for illustration.</div>
      </div>
      <Panel title="Wind generation: forecast vs actual"
             desc="Hourly, national GB wind (MW). Dashed line = forecast minus historical January bias.">
        <ResponsiveContainer>
          <LineChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="t" interval={2} fontSize={12} />
            <YAxis fontSize={12} tickFormatter={(v) => (v / 1000).toFixed(0) + 'k'} />
            <Tooltip formatter={(v) => mw(v)} />
            <Legend />
            <Line dataKey="forecast" name="Forecast" stroke="#2563eb" dot={false} strokeWidth={2} />
            <Line dataKey="adjusted" name="Bias-adjusted" stroke="#d97706" dot={false} strokeDasharray="5 4" />
            <Line dataKey="actual" name="Actual" stroke="#059669" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </Panel>
    </>
  )
}

function histogram(errors, width = 500) {
  if (!errors.length) return []
  const lo = Math.floor(Math.min(...errors) / width) * width
  const hi = Math.ceil(Math.max(...errors) / width) * width
  const bins = []
  for (let s = lo; s < hi; s += width) bins.push({ bin: s, label: `${s}`, count: 0 })
  errors.forEach((e) => { bins[Math.min(Math.floor((e - lo) / width), bins.length - 1)].count++ })
  return bins
}

function AccuracyView({ cutoff }) {
  const acc = useApi(`/api/accuracy?cutoff=${cutoff}`)
  const hor = useApi('/api/accuracy/by-horizon?bin_h=4&max_h=48')
  if (acc.error) return <p className="err">{acc.error}</p>
  if (!acc.data) return <p className="muted">Loading…</p>

  const { summary: s, daily, errors } = acc.data
  const meanActual = daily.reduce((a, d) => a + d.mean_actual, 0) / daily.length
  const pct = (100 * s.bias) / meanActual
  const hist = histogram(errors)
  const within = (n) => Math.round((100 * errors.filter((e) => Math.abs(e) <= n).length) / errors.length)

  return (
    <>
      <div className="grid">
        <Kpi label="MAE" value={mw(s.mae)} hint="Typical absolute miss" />
        <Kpi label="RMSE" value={mw(s.rmse)} hint="Penalises large misses" />
        <Kpi label="Bias" value={(s.bias > 0 ? '+' : '') + mw(s.bias)} hint="Forecast minus actual" />
        <Kpi label="MAPE" value={s.mape.toFixed(1) + '%'} hint={`${s.n} hours evaluated`} />
      </div>
      <div className="card insight">
        <b>What this means:</b> forecasts available at the {cutoff}:00 UTC cutoff on the day before
        over-predicted wind by about <b>{mw(s.bias)}</b> on average ({pct.toFixed(0)}% of mean
        actual output). Only {within(1000)}% of hours were within ±1,000 MW and {within(2500)}% within ±2,500 MW.
        Buyers relying on the raw forecast would systematically under-buy thermal power.
      </div>
      <div className="two">
        <Panel title="Daily mean absolute error" desc="Which days were hardest to forecast (MW).">
          <ResponsiveContainer>
            <BarChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="day" tickFormatter={(d) => d.slice(8)} fontSize={11} />
              <YAxis fontSize={12} />
              <Tooltip formatter={(v) => mw(v)} />
              <Bar dataKey="mae" name="MAE" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Error by forecast lead time"
               desc="MAE and bias by hours between publication and target. Accuracy degrades with lead time.">
          <ResponsiveContainer>
            <BarChart data={hor.data || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="horizon_bin" tickFormatter={(h) => `${h}-${h + 4}h`} fontSize={11} />
              <YAxis fontSize={12} />
              <Tooltip formatter={(v) => mw(v)} />
              <Legend />
              <Bar dataKey="mae" name="MAE" fill="#2563eb" />
              <Bar dataKey="bias" name="Bias" fill="#d97706" />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Distribution of errors" desc="Forecast minus actual, 500 MW bins. Right-shifted = over-forecast.">
          <ResponsiveContainer>
            <BarChart data={hist}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" fontSize={11} />
              <YAxis fontSize={12} />
              <Tooltip />
              <ReferenceLine x="0" stroke="#14213d" />
              <Bar dataKey="count" name="Hours" fill="#059669" />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>
    </>
  )
}

export default function App() {
  const [tab, setTab] = useState('decision')
  const [cutoff, setCutoff] = useState(9)
  return (
    <div className="wrap">
      <header>
        <div>
          <h1>Day-ahead wind forecast monitor</h1>
          <div className="sub">GB national wind · Elexon WINDFOR vs FUELHH · January 2026 delivery days</div>
        </div>
        <label className="muted">Decision cutoff (day before)
          <select value={cutoff} onChange={(e) => setCutoff(Number(e.target.value))}>
            {CUTOFFS.map((c) => <option key={c.v} value={c.v}>{c.label}</option>)}
          </select>
        </label>
      </header>
      <div className="tabs">
        <button className={'tab ' + (tab === 'decision' ? 'on' : '')} onClick={() => setTab('decision')}>Decision view</button>
        <button className={'tab ' + (tab === 'accuracy' ? 'on' : '')} onClick={() => setTab('accuracy')}>Forecast accuracy</button>
      </div>
      {tab === 'decision' ? <DecisionView cutoff={cutoff} /> : <AccuracyView cutoff={cutoff} />}
    </div>
  )
}