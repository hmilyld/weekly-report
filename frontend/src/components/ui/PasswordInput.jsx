import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

/**
 * A password field with the reveal switch forms are expected to offer.
 * The control keeps its native semantics; only the `type` flips, and the
 * button reports its state with aria-pressed.
 */
export default function PasswordInput({ className = 'input', ...rest }) {
  const [shown, setShown] = useState(false)
  return (
    <div className="field-reveal">
      <input type={shown ? 'text' : 'password'} className={className} {...rest} />
      <button
        type="button"
        className="field-reveal-toggle"
        aria-pressed={shown}
        aria-label={shown ? '隐藏密码' : '显示密码'}
        title={shown ? '隐藏密码' : '显示密码'}
        onClick={() => setShown((value) => !value)}
      >
        {shown ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
      </button>
    </div>
  )
}
