import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import PasswordInput from '../PasswordInput'

describe('PasswordInput', () => {
  it('starts masked with the reveal switch off', () => {
    render(<PasswordInput aria-label="密码" />)

    expect(screen.getByLabelText('密码')).toHaveAttribute('type', 'password')
    const toggle = screen.getByRole('button', { name: '显示密码' })
    expect(toggle).toHaveAttribute('aria-pressed', 'false')
  })

  it('reveals and re-masks the value on click', async () => {
    const user = userEvent.setup()
    render(<PasswordInput aria-label="密码" defaultValue="Passw0rd1" />)

    const input = screen.getByLabelText('密码')
    await user.click(screen.getByRole('button', { name: '显示密码' }))
    expect(input).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: '隐藏密码' })).toHaveAttribute('aria-pressed', 'true')

    await user.click(screen.getByRole('button', { name: '隐藏密码' }))
    expect(input).toHaveAttribute('type', 'password')
    expect(screen.getByRole('button', { name: '显示密码' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })

  it('does not submit the surrounding form when toggling', async () => {
    const user = userEvent.setup()
    render(
      <form>
        <PasswordInput aria-label="密码" />
      </form>,
    )

    expect(screen.getByRole('button', { name: '显示密码' })).toHaveAttribute('type', 'button')
    await user.click(screen.getByRole('button', { name: '显示密码' }))
    expect(screen.getByLabelText('密码')).toHaveAttribute('type', 'text')
  })

  it('forwards name, value and change handlers to the native input', async () => {
    const user = userEvent.setup()
    let seen = ''
    render(
      <PasswordInput
        aria-label="密码"
        name="password"
        onChange={(event) => {
          seen = event.target.value
        }}
      />,
    )

    const input = screen.getByLabelText('密码')
    expect(input).toHaveAttribute('name', 'password')

    await user.type(input, 'abc')
    expect(seen).toBe('abc')
    expect(input).toHaveValue('abc')
  })
})
