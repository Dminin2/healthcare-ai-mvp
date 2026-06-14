import { useState, useEffect } from 'react'
import { login, getAdvice, getSummary, postDailyState } from './api/client'
import './App.css'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD

const RISK_CONFIG = {
  ok:      { emoji: '✅', label: 'OK',      message: '体調・気象ともに良好',       cls: 'ok'      },
  caution: { emoji: '⚠️', label: 'Caution', message: 'いくつかのリスク要因があります', cls: 'caution' },
  danger:  { emoji: '🚨', label: 'Danger',  message: '健康リスクが高い状態です',    cls: 'danger'  },
}

const MOOD_OPTIONS = [
  { value: 2,  emoji: '😞', label: 'とても悪い' },
  { value: 4,  emoji: '😕', label: 'やや悪い'   },
  { value: 6,  emoji: '😐', label: '普通'        },
  { value: 8,  emoji: '🙂', label: 'やや良い'   },
  { value: 10, emoji: '😄', label: 'とても良い' },
]

const SYMPTOM_CODES = ['headache', 'fatigue', 'nausea', 'fever', 'sore_throat', 'body_ache', 'none']
const SYMPTOM_LABELS = {
  headache:   '頭痛',
  fatigue:    '倦怠感',
  nausea:     '吐き気',
  fever:      '発熱',
  sore_throat:'喉の痛み',
  body_ache:  '筋肉痛',
  none:       'なし',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function todayISO() {
  return new Date().toISOString().split('T')[0]
}

function formatDateJP(iso) {
  const d = new Date(iso + 'T00:00:00')
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}

function formatDateShort(iso) {
  if (iso === todayISO()) return '今日'
  const d = new Date(iso + 'T00:00:00')
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function moodEmoji(mood) {
  if (!mood) return null
  if (mood >= 9) return '😄'
  if (mood >= 7) return '🙂'
  if (mood >= 5) return '😐'
  if (mood >= 3) return '😕'
  return '😞'
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function DataMissing({ message }) {
  return (
    <div className="data-missing">
      {message || 'データが不足しています。気象データと健康データを投入してください。'}
    </div>
  )
}

function Skeleton() {
  return <div className="skeleton" aria-hidden="true" />
}

function RiskSection({ advice, loading }) {
  if (loading) return <Skeleton />
  if (!advice) return <DataMissing />
  const r = RISK_CONFIG[advice.overall_level] ?? RISK_CONFIG.ok
  return (
    <div className={`risk-card risk-${r.cls}`}>
      <div className="risk-label">{r.emoji} {r.label}</div>
      <div className="risk-sub">{r.message}</div>
      <div className="risk-score">リスクスコア：{advice.total_points} pt</div>
    </div>
  )
}

function AdviceSection({ advice, loading }) {
  if (loading) return <Skeleton />
  if (!advice) return <DataMissing message="データが不足しています。" />
  return (
    <div className="advice-card">
      <div className="advice-header">ℹ️ 本日のアドバイス</div>
      <p className="advice-text">{advice.advice}</p>
    </div>
  )
}

function TimelineSection({ summary, loading }) {
  if (loading) return <Skeleton />
  if (!summary) return <DataMissing message="サマリーの取得に失敗しました。" />
  return (
    <div className="timeline">
      {summary.map((day, i) => {
        const isLeft = i % 2 === 0
        const emoji = moodEmoji(day.daily_state?.mood)
        const label = formatDateShort(day.date)
        const hasWeather = !!day.weather
        const card = (
          <div className={`tl-card ${isLeft ? 'tl-card--left' : 'tl-card--right'}`}>
            <div className="tl-date">{label}</div>
            {emoji && <div className="tl-mood">{emoji}</div>}
            {hasWeather && (
              <div className="tl-weather">
                🌡 {day.weather.temp_max}° / {day.weather.temp_min}°
              </div>
            )}
            {!emoji && !hasWeather && (
              <div className="tl-nodata">データなし</div>
            )}
          </div>
        )
        return (
          <div key={day.date} className="tl-row">
            <div className="tl-side tl-side--left">{isLeft ? card : null}</div>
            <div className="tl-axis">
              <div className="tl-line" />
              <div className="tl-dot" />
              <div className="tl-line" />
            </div>
            <div className="tl-side tl-side--right">{!isLeft ? card : null}</div>
          </div>
        )
      })}
    </div>
  )
}

function StatusSection({ summary }) {
  const today = summary?.[0]
  return (
    <div className="status-wrap">
      <div className="status-card">
        <span className="status-icon">🌤</span>
        <div>
          <div className="status-label">気象データ</div>
          <div className="status-value">
            {today?.weather ? '✅ 取得済み' : '❌ データなし'}
          </div>
        </div>
      </div>
      <div className="status-card">
        <span className="status-icon">❤️</span>
        <div>
          <div className="status-label">健康指標</div>
          <div className="status-value">
            {today?.health_metrics ? '✅ 取得済み' : '❌ データなし'}
          </div>
        </div>
      </div>
    </div>
  )
}

function CheckInForm({ onSubmitSuccess }) {
  const [mood, setMood] = useState(null)
  const [symptoms, setSymptoms] = useState([])
  const [notes, setNotes] = useState('')
  const [state, setState] = useState('idle') // idle | loading | success | error
  const [errorMsg, setErrorMsg] = useState('')

  const toggleSymptom = (code) => {
    setSymptoms(prev => {
      if (code === 'none') {
        return prev.includes('none') ? [] : ['none']
      }
      const without = prev.filter(s => s !== 'none')
      return without.includes(code)
        ? without.filter(s => s !== code)
        : [...without, code]
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!mood) return
    setState('loading')
    try {
      await postDailyState({
        date: todayISO(),
        mood,
        symptoms: symptoms.length > 0 ? symptoms : ['none'],
        notes: notes.trim() || null,
      })
      setState('success')
      onSubmitSuccess()
    } catch (err) {
      setErrorMsg(err.message)
      setState('error')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="checkin-form">
      <div className="form-field">
        <div className="form-label">日付</div>
        <div className="form-date">{formatDateJP(todayISO())}</div>
      </div>

      <div className="form-field">
        <div className="form-label">気分</div>
        <div className="mood-grid">
          {MOOD_OPTIONS.map(opt => (
            <button
              key={opt.value}
              type="button"
              className={`mood-btn ${mood === opt.value ? 'mood-btn--selected' : ''}`}
              onClick={() => setMood(opt.value)}
            >
              <span className="mood-emoji">{opt.emoji}</span>
              <span className="mood-label">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="form-field">
        <div className="form-label">症状</div>
        <div className="symptoms-list">
          {SYMPTOM_CODES.map(code => (
            <label key={code} className="symptom-item">
              <input
                type="checkbox"
                checked={symptoms.includes(code)}
                onChange={() => toggleSymptom(code)}
              />
              {SYMPTOM_LABELS[code]}
            </label>
          ))}
        </div>
      </div>

      <div className="form-field">
        <div className="form-label">メモ</div>
        <textarea
          className="notes-textarea"
          placeholder="ここにメモを入力してください。"
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={3}
        />
      </div>

      {state === 'success' && (
        <div className="msg msg--success">体調データを送信しました ✅</div>
      )}
      {state === 'error' && (
        <div className="msg msg--error">{errorMsg || '送信に失敗しました。'}</div>
      )}

      <button
        type="submit"
        className="btn-submit"
        disabled={!mood || state === 'loading'}
      >
        {state === 'loading' ? '送信中...' : '送信する'}
      </button>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Main App
// ---------------------------------------------------------------------------

export default function App() {
  const [authState, setAuthState] = useState('loading') // loading | ok | error
  const [advice, setAdvice] = useState(undefined) // undefined=loading, null=404, obj=data
  const [summary, setSummary] = useState(undefined)

  const fetchData = () => {
    const today = todayISO()
    getAdvice(today)
      .then(setAdvice)
      .catch(() => setAdvice(null))
    getSummary()
      .then(setSummary)
      .catch(() => setSummary(null))
  }

  useEffect(() => {
    if (!DEMO_EMAIL || !DEMO_PASSWORD) {
      setAuthState('error')
      return
    }
    login(DEMO_EMAIL, DEMO_PASSWORD)
      .then(() => {
        setAuthState('ok')
        fetchData()
      })
      .catch(() => setAuthState('error'))
  }, [])

  if (authState === 'loading') {
    return <div className="fullpage-msg">ログイン中...</div>
  }

  if (authState === 'error') {
    return (
      <div className="fullpage-msg fullpage-msg--error">
        <p>デモユーザーでのログインに失敗しました。</p>
        <p className="fullpage-sub">
          環境変数 <code>VITE_DEMO_EMAIL</code> / <code>VITE_DEMO_PASSWORD</code> を確認してください。
        </p>
      </div>
    )
  }

  const adviceLoading = advice === undefined
  const summaryLoading = summary === undefined

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Health × Weather AI Advisor</h1>
        <a
          href="https://github.com/Dminin2/healthcare-ai"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-github"
        >
          GitHub
        </a>
      </header>

      <main className="app-main">
        {/* ── Left column ── */}
        <div className="col">
          <section className="section">
            <h2 className="section-title">今日のリスクレベル</h2>
            <RiskSection advice={advice} loading={adviceLoading} />
          </section>

          <section className="section">
            <h2 className="section-title">AIアドバイス</h2>
            <AdviceSection advice={advice} loading={adviceLoading} />
          </section>

          <section className="section">
            <h2 className="section-title">7日間サマリー</h2>
            <TimelineSection summary={summary} loading={summaryLoading} />
          </section>
        </div>

        {/* ── Right column ── */}
        <div className="col">
          <section className="section section--form">
            <h2 className="section-title">体調入力フォーム</h2>
            <CheckInForm onSubmitSuccess={fetchData} />
          </section>

          <section className="section">
            <h2 className="section-title">データ取得ステータス</h2>
            <StatusSection summary={summary} />
          </section>
        </div>
      </main>
    </div>
  )
}
