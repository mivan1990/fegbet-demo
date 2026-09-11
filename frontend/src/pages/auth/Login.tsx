import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button, Input, useToast } from '@/components/ui'
import { useAuth } from '@/auth/AuthContext'
import { apiErrorMessage } from '@/api/client'
import { AuthShell } from './AuthShell'

const schema = z.object({
  email: z.string().min(1, 'Scrie emailul.').email('Emailul nu pare valid.'),
  password: z.string().min(1, 'Scrie parola.'),
})

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const toast = useToast()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [submitting, setSubmitting] = useState(false)

  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const validate = () => {
    const result = schema.safeParse({ email, password })
    if (result.success) {
      setErrors({})
      return result.data
    }
    const next: typeof errors = {}
    for (const issue of result.error.issues) {
      next[issue.path[0] as 'email' | 'password'] = issue.message
    }
    setErrors(next)
    return null
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const values = validate()
    if (!values) return
    setSubmitting(true)
    try {
      await login(values.email, values.password)
      toast.success('Bine ai revenit!')
      navigate(from, { replace: true })
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Email sau parolă greșite.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Intră în cont"
      subtitle="Biletele tale te așteaptă."
      footer={
        <>
          N-ai cont?{' '}
          <Link to="/inregistrare" className="font-semibold text-fortuna hover:underline">
            Fă-ți unul
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <Input
          label="Email"
          type="email"
          inputMode="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onBlur={validate}
          error={errors.email}
        />
        <Input
          label="Parolă"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onBlur={validate}
          error={errors.password}
        />
        <Button type="submit" variant="primary" block loading={submitting}>
          Intru
        </Button>
      </form>
    </AuthShell>
  )
}
