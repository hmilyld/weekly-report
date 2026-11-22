import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import Button from '../Button'

describe('Button', () => {
  it('renders its label as an outline button by default', () => {
    render(<Button>保存</Button>)
    const button = screen.getByRole('button', { name: '保存' })

    expect(button).toHaveClass('btn', 'btn-outline')
    expect(button).toBeEnabled()
    expect(button).toHaveAttribute('type', 'button')
  })

  it('applies variant, size and block modifiers', () => {
    render(
      <Button variant="primary" size="sm" block>
        生成周报
      </Button>,
    )
    const button = screen.getByRole('button', { name: '生成周报' })

    expect(button).toHaveClass('btn-primary', 'btn-sm', 'btn-block')
  })

  it('disables itself and marks aria-busy while loading', () => {
    render(<Button loading>生成中</Button>)
    const button = screen.getByRole('button', { name: '生成中' })

    expect(button).toBeDisabled()
    expect(button).toHaveAttribute('aria-busy', 'true')
  })

  it('keeps icon-only buttons labelled for screen readers', () => {
    render(
      <Button iconOnly aria-label="删除">
        ×
      </Button>,
    )
    const button = screen.getByRole('button', { name: '删除' })

    expect(button).toHaveClass('btn-icon')
  })

  it('passes extra attributes through to the native button', () => {
    render(
      <Button type="submit" disabled title="不可用">
        提交
      </Button>,
    )
    const button = screen.getByRole('button', { name: '提交' })

    expect(button).toBeDisabled()
    expect(button).toHaveAttribute('type', 'submit')
    expect(button).toHaveAttribute('title', '不可用')
  })
})
