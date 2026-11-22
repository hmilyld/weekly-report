import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import SettingsPage from '../Settings'
import { AuthContext } from '../../contexts/auth'
import { ConfirmContext } from '../../components/ui/confirm'
import { changePassword, getConfig, getTokens, updateConfig } from '../../api'

vi.mock('../../api', () => ({
  getConfig: vi.fn(),
  updateConfig: vi.fn(),
  testConnection: vi.fn(),
  getTokens: vi.fn(),
  createToken: vi.fn(),
  deleteToken: vi.fn(),
  revokeAllTokens: vi.fn(),
  changePassword: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const CONFIG = {
  llm_api_url: 'http://localhost:11434/v1/chat/completions',
  llm_model_name: 'llama2',
  api_key: 'sk-****',
}

function renderSettings({
  isAdmin = true,
  tokens = [],
  confirm = () => Promise.resolve(true),
} = {}) {
  getConfig.mockResolvedValue({ data: CONFIG })
  getTokens.mockResolvedValue({ data: tokens })
  return render(
    <AuthContext.Provider value={{ isAdmin }}>
      <ConfirmContext.Provider value={confirm}>
        <SettingsPage />
      </ConfirmContext.Provider>
    </AuthContext.Provider>,
  )
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('gives an admin all three panels with the saved config', async () => {
    renderSettings()

    expect(screen.getByText('大模型配置')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '修改密码' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'API Token' })).toBeInTheDocument()
    expect(await screen.findByDisplayValue('llama2')).toBeInTheDocument()
    expect(screen.getByDisplayValue(CONFIG.llm_api_url)).toBeInTheDocument()
    expect(getConfig).toHaveBeenCalledTimes(1)
  })

  it('hides the model panel from a regular user but keeps account panels', async () => {
    renderSettings({ isAdmin: false })

    expect(screen.queryByText('大模型配置')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '修改密码' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'API Token' })).toBeInTheDocument()
    expect(getConfig).not.toHaveBeenCalled()
    expect(await screen.findByText(/还没有 Token/)).toBeInTheDocument()
  })

  it('lists existing tokens with their usage state', async () => {
    renderSettings({
      tokens: [
        {
          id: 1,
          name: 'ci-bot',
          created_at: '2026-11-01T09:15:02',
          last_used_at: null,
        },
      ],
    })

    expect(await screen.findByText('ci-bot')).toBeInTheDocument()
    expect(screen.getByText('尚未使用')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '删除 ci-bot' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '吊销全部 Token' })).toBeEnabled()
  })

  it('disables revoking when the account has no tokens', async () => {
    renderSettings({ tokens: [] })

    expect(await screen.findByText(/还没有 Token/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '吊销全部 Token' })).toBeDisabled()
  })

  it('saves the model config and never echoes a masked key', async () => {
    const user = userEvent.setup()
    renderSettings()

    const url = await screen.findByDisplayValue(CONFIG.llm_api_url)
    await user.clear(url)
    await user.type(url, 'http://10.0.0.5:11434/v1/chat/completions')
    await user.click(screen.getByRole('button', { name: '保存配置' }))

    expect(updateConfig).toHaveBeenCalledWith({
      llm_api_url: 'http://10.0.0.5:11434/v1/chat/completions',
      llm_model_name: 'llama2',
    })
  })

  it('blocks a password change when the two entries differ', async () => {
    const user = userEvent.setup()
    renderSettings()

    await user.type(screen.getByLabelText('当前密码'), 'Passw0rd1')
    await user.type(screen.getByLabelText('新密码'), 'Passw0rd2')
    await user.type(screen.getByLabelText('确认新密码'), 'Passw0rd3')
    await user.click(screen.getByRole('button', { name: '修改密码' }))

    expect(screen.getByRole('alert')).toHaveTextContent('两次输入的新密码不一致')
    expect(changePassword).not.toHaveBeenCalled()
  })

  it('submits a valid password change', async () => {
    const user = userEvent.setup()
    changePassword.mockResolvedValue({ data: { access_token: 'fresh-token' } })
    renderSettings()

    await user.type(screen.getByLabelText('当前密码'), 'Passw0rd1')
    await user.type(screen.getByLabelText('新密码'), 'Passw0rd2')
    await user.type(screen.getByLabelText('确认新密码'), 'Passw0rd2')
    await user.click(screen.getByRole('button', { name: '修改密码' }))

    expect(changePassword).toHaveBeenCalledWith('Passw0rd1', 'Passw0rd2')
    expect(localStorage.getItem('token')).toBe('fresh-token')
  })
})
