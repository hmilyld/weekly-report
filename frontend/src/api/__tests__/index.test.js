import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import api, {
  getCompletedTasks,
  getDailyReportsRange,
  revokeAllTokens,
  setReLoginHandler,
} from '../index'

// 用自定义 adapter 拦下请求，避免任何真实网络访问。
function stubAdapter(handler) {
  api.defaults.adapter = async (config) => handler(config)
}

function okResponse(data, config, status = 200) {
  return { data, status, statusText: 'OK', headers: {}, config }
}

describe('api client', () => {
  let reLogin

  beforeEach(() => {
    reLogin = vi.fn()
    setReLoginHandler(reLogin)
    localStorage.clear()
  })

  afterEach(() => {
    setReLoginHandler(null)
    vi.restoreAllMocks()
  })

  it('attaches the JWT from localStorage to every request', async () => {
    localStorage.setItem('token', 'jwt-abc')
    let seen
    stubAdapter((config) => {
      seen = config
      return okResponse({}, config)
    })

    await api.get('/users/me')
    expect(seen.headers.Authorization).toBe('Bearer jwt-abc')
  })

  it('sends no Authorization header without a token', async () => {
    let seen
    stubAdapter((config) => {
      seen = config
      return okResponse({}, config)
    })

    await api.get('/auth/status')
    expect(seen.headers.Authorization).toBeUndefined()
  })

  it('opens the re-login flow and rejects on 401', async () => {
    const error = new Error('unauthorized')
    error.response = { status: 401 }
    stubAdapter(() => {
      throw error
    })

    await expect(api.get('/users/me')).rejects.toBe(error)
    expect(reLogin).toHaveBeenCalledTimes(1)
  })

  it('does not open the re-login flow on 402 (wrong current password)', async () => {
    const error = new Error('wrong password')
    error.response = { status: 402 }
    stubAdapter(() => {
      throw error
    })

    await expect(api.post('/auth/change-password', {})).rejects.toBe(error)
    expect(reLogin).not.toHaveBeenCalled()
  })

  it('opens the re-login flow when the payload cannot be decrypted', async () => {
    stubAdapter((config) => okResponse({ _decryption_failed: true }, config))

    const res = await api.get('/daily/week/2026-11-02')
    expect(res.data._decryption_failed).toBe(true)
    expect(reLogin).toHaveBeenCalledTimes(1)
  })

  it('leaves a normal response untouched', async () => {
    stubAdapter((config) => okResponse({ content: '日报' }, config))

    const res = await api.get('/daily/week/2026-11-02')
    expect(res.data).toEqual({ content: '日报' })
    expect(reLogin).not.toHaveBeenCalled()
  })

  it('builds query strings for range and pagination endpoints', async () => {
    const urls = []
    stubAdapter((config) => {
      urls.push(config.url)
      return okResponse({}, config)
    })

    await getDailyReportsRange('2026-11-01', '2026-11-30')
    await getCompletedTasks(20, 40)

    expect(urls).toEqual([
      '/daily?start_date=2026-11-01&end_date=2026-11-30',
      '/tasks/completed?offset=20&limit=40',
    ])
  })

  it('revokes all tokens with a bare DELETE /tokens', async () => {
    let seen
    stubAdapter((config) => {
      seen = config
      return okResponse({}, config)
    })

    await revokeAllTokens()
    expect(seen.method).toBe('delete')
    expect(seen.url).toBe('/tokens')
  })
})
