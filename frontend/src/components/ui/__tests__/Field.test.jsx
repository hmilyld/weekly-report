import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import Field from '../Field'

describe('Field', () => {
  it('wires the label to its control', () => {
    render(
      <Field label="模型地址">
        <input />
      </Field>,
    )

    const input = screen.getByLabelText('模型地址')
    expect(input).toBeInTheDocument()
    expect(input).not.toHaveAttribute('aria-invalid')
  })

  it('keeps an id the control already provides', () => {
    render(
      <Field label="用户名">
        <input id="custom-id" />
      </Field>,
    )

    expect(screen.getByLabelText('用户名')).toHaveAttribute('id', 'custom-id')
  })

  it('describes the control with the hint', () => {
    render(
      <Field label="模型名称" hint="例如 llama2">
        <input />
      </Field>,
    )

    const input = screen.getByLabelText('模型名称')
    const hint = screen.getByText('例如 llama2')
    expect(input).toHaveAttribute('aria-describedby', hint.id)
  })

  it('replaces the hint with an alert when invalid', () => {
    render(
      <Field label="密码" hint="至少 8 位" error="密码太短">
        <input />
      </Field>,
    )

    const input = screen.getByLabelText('密码')
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('密码太短')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', alert.id)
    expect(screen.queryByText('至少 8 位')).not.toBeInTheDocument()
  })

  it('marks optional fields without changing the label text', () => {
    render(
      <Field label="备注" optional>
        <textarea />
      </Field>,
    )

    expect(screen.getByLabelText(/备注/)).toBeInTheDocument()
    expect(screen.getByText('可选')).toBeInTheDocument()
  })

  it('renders without a label when none is given', () => {
    const { container } = render(
      <Field>
        <input aria-label="孤立输入" />
      </Field>,
    )

    expect(container.querySelector('label')).toBeNull()
    expect(screen.getByLabelText('孤立输入')).toBeInTheDocument()
  })
})
