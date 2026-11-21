import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { copyText } from '../clipboard'

function setClipboard(value) {
  Object.defineProperty(navigator, 'clipboard', { value, configurable: true })
}

describe('copyText', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    document.execCommand = vi.fn(() => true)
  })

  afterEach(() => {
    setClipboard(undefined)
    vi.restoreAllMocks()
  })

  it('uses the async clipboard API when available', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    setClipboard({ writeText })

    await expect(copyText('周报正文')).resolves.toBe(true)
    expect(writeText).toHaveBeenCalledWith('周报正文')
    expect(document.execCommand).not.toHaveBeenCalled()
  })

  it('falls back to execCommand when the clipboard API rejects', async () => {
    setClipboard({ writeText: vi.fn().mockRejectedValue(new Error('denied')) })

    await expect(copyText('fallback')).resolves.toBe(true)
    expect(document.execCommand).toHaveBeenCalledWith('copy')
    expect(document.body.querySelector('textarea')).toBeNull()
  })

  it('reports failure when the legacy copy is refused', async () => {
    setClipboard(undefined)
    document.execCommand = vi.fn(() => false)

    await expect(copyText('nope')).resolves.toBe(false)
  })

  it('reports failure instead of throwing when the DOM path breaks', async () => {
    setClipboard(undefined)
    document.execCommand = vi.fn(() => {
      throw new Error('boom')
    })

    await expect(copyText('nope')).resolves.toBe(false)
  })
})
