import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { CheckCircle2, Save, XCircle, Zap } from 'lucide-react'

import { getConfig, testConnection, updateConfig } from '../../api'
import Button from '../ui/Button'
import Field from '../ui/Field'
import PasswordInput from '../ui/PasswordInput'
import { Panel, PanelBody, PanelFooter, PanelHeader } from '../ui/Panel'

/** Admin-only: the OpenAI-compatible endpoint the reports are generated with. */
export default function LlmPanel() {
  const [config, setConfig] = useState({ llm_api_url: '', llm_model_name: '', api_key: '' })
  const [loadingConfig, setLoadingConfig] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const loadConfig = useCallback(async () => {
    setLoadingConfig(true)
    try {
      const { data } = await getConfig()
      setConfig({
        llm_api_url: data.llm_api_url || '',
        llm_model_name: data.llm_model_name || '',
        api_key: data.api_key || '',
      })
    } catch {
      toast.error('加载配置失败')
    } finally {
      setLoadingConfig(false)
    }
  }, [])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  // A masked key must not be sent back; only a freshly typed key is written.
  const configPayload = () => {
    const payload = { ...config }
    if (config.api_key && config.api_key.includes('*')) delete payload.api_key
    return payload
  }

  const handleSaveConfig = async () => {
    setSaving(true)
    try {
      await updateConfig(configPayload())
      toast.success('配置已保存')
      loadConfig()
    } catch (err) {
      toast.error(err.response?.data?.detail || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      await updateConfig(configPayload())
      const { data } = await testConnection()
      setTestResult(data)
      toast[data.success ? 'success' : 'error'](data.message)
    } catch (err) {
      setTestResult({ success: false, message: err.message || '测试失败' })
    } finally {
      setTesting(false)
    }
  }

  return (
    <Panel className="page-section">
      <PanelHeader title="大模型配置" icon={Zap} />
      <form
        onSubmit={(event) => {
          event.preventDefault()
          handleSaveConfig()
        }}
        noValidate
      >
        <PanelBody>
          {loadingConfig ? (
            <div className="loading-block">
              <span className="spinner" aria-hidden="true" />
              正在读取配置…
            </div>
          ) : (
            <div className="form-stack">
              <Field label="API 地址" hint="以 /chat/completions 结尾的完整 OpenAI 兼容地址">
                <input
                  className="input"
                  type="url"
                  name="llm_api_url"
                  placeholder="http://localhost:11434/v1/chat/completions"
                  value={config.llm_api_url}
                  onChange={(event) => setConfig({ ...config, llm_api_url: event.target.value })}
                  autoComplete="off"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                />
              </Field>
              <Field label="模型名称" hint="与接口返回的模型标识一致，例如 llama2、gpt-4o-mini">
                <input
                  className="input"
                  type="text"
                  name="llm_model_name"
                  placeholder="llama2"
                  value={config.llm_model_name}
                  onChange={(event) => setConfig({ ...config, llm_model_name: event.target.value })}
                  autoComplete="off"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                />
              </Field>
              <Field
                label="API Key"
                optional
                hint="留空则不发送 Authorization 头；已保存的密钥显示为掩码。"
              >
                <PasswordInput
                  name="api_key"
                  placeholder="留空则不发送 Authorization 头"
                  value={config.api_key}
                  onChange={(event) => setConfig({ ...config, api_key: event.target.value })}
                  autoComplete="off"
                />
              </Field>
              {testResult && (
                <div
                  className={`notice ${testResult.success ? 'notice-success' : 'notice-danger'}`}
                  role="status"
                >
                  {testResult.success ? (
                    <CheckCircle2 size={16} aria-hidden="true" />
                  ) : (
                    <XCircle size={16} aria-hidden="true" />
                  )}
                  <span>{testResult.message}</span>
                </div>
              )}
            </div>
          )}
        </PanelBody>
        <PanelFooter>
          <Button type="button" variant="outline" icon={Zap} onClick={handleTest} loading={testing}>
            测试连接
          </Button>
          <Button type="submit" variant="primary" icon={Save} loading={saving}>
            保存配置
          </Button>
        </PanelFooter>
      </form>
    </Panel>
  )
}
