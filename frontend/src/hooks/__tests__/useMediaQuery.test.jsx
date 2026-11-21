import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

import useMediaQuery from '../useMediaQuery'

// jsdom has no matchMedia: hand the hook a stub that can emit change events.
function stubMatchMedia(initialMatches) {
  const listeners = new Set()
  const mql = {
    matches: initialMatches,
    media: '(max-width: 700px)',
    addEventListener: (event, handler) => {
      if (event === 'change') listeners.add(handler)
    },
    removeEventListener: (event, handler) => {
      if (event === 'change') listeners.delete(handler)
    },
  }
  window.matchMedia = vi.fn(() => mql)
  return {
    mql,
    emit(matches) {
      mql.matches = matches
      listeners.forEach((handler) => handler({ matches }))
    },
    listenerCount: () => listeners.size,
  }
}

describe('useMediaQuery', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('returns the initial match state', () => {
    stubMatchMedia(true)
    const { result } = renderHook(() => useMediaQuery('(max-width: 700px)'))

    expect(result.current).toBe(true)
    expect(window.matchMedia).toHaveBeenCalledWith('(max-width: 700px)')
  })

  it('follows change events from the media query list', () => {
    const media = stubMatchMedia(false)
    const { result } = renderHook(() => useMediaQuery('(max-width: 700px)'))
    expect(result.current).toBe(false)

    act(() => media.emit(true))
    expect(result.current).toBe(true)

    act(() => media.emit(false))
    expect(result.current).toBe(false)
  })

  it('subscribes once and unsubscribes on unmount', () => {
    const media = stubMatchMedia(true)
    const { unmount } = renderHook(() => useMediaQuery('(max-width: 700px)'))
    expect(media.listenerCount()).toBe(1)

    unmount()
    expect(media.listenerCount()).toBe(0)
  })

  it('re-subscribes when the query changes', () => {
    const media = stubMatchMedia(true)
    const { rerender, unmount } = renderHook(({ query }) => useMediaQuery(query), {
      initialProps: { query: '(max-width: 700px)' },
    })

    rerender({ query: '(min-width: 1200px)' })

    expect(media.listenerCount()).toBe(1)
    unmount()
    expect(media.listenerCount()).toBe(0)
  })
})
