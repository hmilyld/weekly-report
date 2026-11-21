import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// 单元测试专用配置：不加载 PWA 插件，避免构建期逻辑干扰测试。
// 业务代码与 vite.config.js 保持无关，测试只覆盖纯逻辑与组件渲染。
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
  },
})
