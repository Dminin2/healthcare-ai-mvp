const TOKEN_KEY = 'haw_demo_token'

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY)
}

function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export async function login(email, password) {
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'ログインに失敗しました')
  }
  const data = await res.json()
  setToken(data.access_token)
}

async function authFetch(path, options = {}) {
  const headers = { Authorization: `Bearer ${getToken()}` }
  if (options.body != null) {
    headers['Content-Type'] = 'application/json'
  }
  return fetch(path, { ...options, headers: { ...headers, ...options.headers } })
}

export async function getAdvice(date) {
  const res = await authFetch(`/advice/${date}`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error('アドバイスの取得に失敗しました')
  return res.json()
}

export async function getSummary() {
  const res = await authFetch('/summary/last7d')
  if (!res.ok) throw new Error('サマリーの取得に失敗しました')
  return res.json()
}

export async function postDailyState(payload) {
  const res = await authFetch('/ingest/daily_state', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '送信に失敗しました')
  }
  return res.json()
}
