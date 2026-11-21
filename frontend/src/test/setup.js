// 让 Testing Library 的断言（toBeDisabled / toHaveAttribute 等）可用。
import '@testing-library/jest-dom/vitest'

// Node 25 默认暴露一个全局 localStorage 占位对象（未设置 --localstorage-file 时
// 没有任何方法），vitest 的 jsdom 环境会把它带到 window 上，导致 clear/removeItem
// 不存在。浏览器里 localStorage 必然可用，因此测试环境补一个等价的内存实现。
function createMemoryStorage() {
  const entries = new Map()
  return {
    get length() {
      return entries.size
    },
    key: (index) => [...entries.keys()][index] ?? null,
    getItem: (key) => (entries.has(String(key)) ? entries.get(String(key)) : null),
    setItem: (key, value) => {
      entries.set(String(key), String(value))
    },
    removeItem: (key) => {
      entries.delete(String(key))
    },
    clear: () => {
      entries.clear()
    },
  }
}

if (typeof globalThis.localStorage?.clear !== 'function') {
  Object.defineProperty(globalThis, 'localStorage', {
    value: createMemoryStorage(),
    configurable: true,
    writable: true,
  })
}
