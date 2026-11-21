import { useAuth } from '../contexts/auth'
import PageHeader from '../components/ui/PageHeader'
import LlmPanel from '../components/settings/LlmPanel'
import PasswordPanel from '../components/settings/PasswordPanel'
import TokenPanel from '../components/settings/TokenPanel'

/**
 * System settings: one panel per concern. Each panel owns its own state and
 * requests, so mounting order has no effect on the others.
 */
export default function SettingsPage() {
  const { isAdmin } = useAuth()

  return (
    <div className="page page-narrow">
      <PageHeader title="系统配置" subtitle="模型接入、账号安全，以及给脚本用的 API Token。" />

      {isAdmin && <LlmPanel />}
      <PasswordPanel />
      <TokenPanel />
    </div>
  )
}
