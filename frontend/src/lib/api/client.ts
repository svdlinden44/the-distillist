import { useAuthStore } from '@/store/authStore'
import { ApiError } from './types'

/** In dev, prefer same-origin `/api` (Vite proxy → http://127.0.0.1:8000). A copied production `.env`
 *  with `VITE_API_BASE_URL=https://…` bypasses the proxy and breaks local API access. Opt out with
 *  `VITE_ALLOW_REMOTE_API_IN_DEV=true` when you intentionally hit a remote API from `npm run dev`.
 */
function resolveApiBaseUrl(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '')
  const allowRemote =
    import.meta.env.VITE_ALLOW_REMOTE_API_IN_DEV === 'true' ||
    import.meta.env.VITE_ALLOW_REMOTE_API_IN_DEV === '1'
  if (import.meta.env.DEV && raw && !allowRemote) {
    if (typeof console !== 'undefined' && console.warn) {
      console.warn(
        '[api] DEV: ignoring VITE_API_BASE_URL so requests use the Vite proxy (/api → http://127.0.0.1:8000). ' +
          'Unset it in frontend/.env or set VITE_ALLOW_REMOTE_API_IN_DEV=true to use the configured URL.',
      )
    }
    return ''
  }
  if (raw) return raw

  // Production SPA hosts: API lives on api.* subdomain (Railway backend service).
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    if (host === 'thedistillist.com' || host === 'www.thedistillist.com') {
      return 'https://api.thedistillist.com'
    }
  }
  return ''
}

const BASE_URL = resolveApiBaseUrl()

function buildRequestUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  if (!BASE_URL) {
    return new URL(p, window.location.origin).toString()
  }
  if (BASE_URL.startsWith('http://') || BASE_URL.startsWith('https://')) {
    return `${BASE_URL}${p}`
  }
  // e.g. api.example.com (no scheme) — treat as host
  return `https://${BASE_URL.replace(/^\/*/, '')}${p}`
}

function parseApiErrorMessage(body: Record<string, unknown>, fallback: string): string {
  const d = body.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d.length) {
    const first = d[0] as Record<string, unknown>
    if (typeof first?.msg === 'string') return first.msg as string
  }
  if (typeof body.message === 'string') return body.message
  const keys = Object.keys(body).filter((k) => k !== 'detail')
  for (const k of keys) {
    const v = body[k]
    if (Array.isArray(v) && typeof v[0] === 'string') return `${k}: ${v[0]}`
    if (typeof v === 'string') return v
  }
  return fallback
}

type QueryPrimitive = string | number | boolean | undefined

export async function request<T>(
  path: string,
  init: RequestInit & {
    params?: Record<string, QueryPrimitive | QueryPrimitive[]>
    auth?: boolean
  } = {},
): Promise<T> {
  const { params, auth = true, ...fetchInit } = init

  const urlObj = new URL(buildRequestUrl(path))
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v === undefined) return
      if (Array.isArray(v)) {
        v.forEach((item) => {
          if (item === undefined || item === '') return
          urlObj.searchParams.append(k, String(item))
        })
      } else {
        urlObj.searchParams.set(k, String(v))
      }
    })
  }
  const url = urlObj.toString()

  const token = useAuthStore.getState().token
  const headers = new Headers(fetchInit.headers)
  const body = fetchInit.body
  const isFormData =
    typeof FormData !== 'undefined' && body instanceof FormData
  if (!isFormData && body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (auth && token) headers.set('Authorization', `Bearer ${token}`)

  let res: Response
  try {
    res = await fetch(url, { ...fetchInit, headers })
  } catch (e) {
    const msg =
      e instanceof TypeError && e.message === 'Failed to fetch'
        ? 'Could not reach the API. Check your connection, or try again in a moment.'
        : e instanceof Error
          ? e.message
          : 'Network error'
    throw new ApiError(0, 'NETWORK', msg)
  }

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as Record<string, unknown>
    const message = parseApiErrorMessage(body, res.statusText)
    const code =
      typeof body.code === 'string'
        ? body.code
        : typeof body.detail === 'string'
          ? 'DETAIL'
          : 'UNKNOWN'
    throw new ApiError(res.status, code, message)
  }

  const text = await res.text()
  if (!text.trim()) {
    return undefined as T
  }
  try {
    return JSON.parse(text) as T
  } catch {
    return undefined as T
  }
}

/** Authenticated fetch for non-JSON bodies (blobs). Throws {@link ApiError} on HTTP errors. */
export async function fetchWithAuth(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<Response> {
  const { auth = true, ...fetchInit } = init
  const urlObj = new URL(buildRequestUrl(path))
  const url = urlObj.toString()

  const token = useAuthStore.getState().token
  const headers = new Headers(fetchInit.headers)
  const body = fetchInit.body
  const isFormData =
    typeof FormData !== 'undefined' && body instanceof FormData
  if (!isFormData && body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (auth && token) headers.set('Authorization', `Bearer ${token}`)

  let res: Response
  try {
    res = await fetch(url, { ...fetchInit, headers })
  } catch (e) {
    const msg =
      e instanceof TypeError && e.message === 'Failed to fetch'
        ? 'Could not reach the API. Check your connection, or try again in a moment.'
        : e instanceof Error
          ? e.message
          : 'Network error'
    throw new ApiError(0, 'NETWORK', msg)
  }

  if (!res.ok) {
    const bodyJson = (await res.json().catch(() => ({}))) as Record<string, unknown>
    const message = parseApiErrorMessage(bodyJson, res.statusText)
    const code =
      typeof bodyJson.code === 'string'
        ? bodyJson.code
        : typeof bodyJson.detail === 'string'
          ? 'DETAIL'
          : 'UNKNOWN'
    throw new ApiError(res.status, code, message)
  }

  return res
}
