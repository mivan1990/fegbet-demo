import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button, Input, useToast } from '@/components/ui'
import { useAuth } from '@/auth/AuthContext'
import { apiErrorMessage } from '@/api/client'
import { AuthShell } from './AuthShell'

// Fara nicio mentiune despre domeniul de email — nici in schema, nici in mesaje.
const schema = z.object({
  email: z.string().min(1, 'Scrie emailul.').email('Emailul nu pare valid.'),
  displayName: z.string().trim().max(80, 'Prea lung.').optional(),
  password: z.string().min(8, 'Minim 8 caractere.'),
})

export function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()

  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; displayName?: string; password?: string }>({})
  const [submitting, setSubmitting] = useState(false)

  const validate = () => {
    const result = schema.safeParse({ email, displayName: displayName || undefined, password })
    if (result.success) {
      setErrors({})
      return result.data
    }
    const next: typeof errors = {}
    for (const issue of result.error.issues) {
      next[issue.path[0] as keyof typeof errors] = issue.message
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
      await register(values.email, values.password, values.displayName)
      toast.success('Cont creat. Bagă primul bilet!')
      navigate('/', { replace: true })
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Nu am putut crea contul cu acest email.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Cont nou"
      subtitle="Îți ia un minut. Biletele, o viață."
      footer={
        <>
          Ai deja cont?{' '}
          <Link to="/login" className="font-semibold text-fortuna hover:underline">
            Intră aici
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
          label="Nume afișat"
          hint="Opțional. Așa te vor vedea ceilalți în clasament."
          autoComplete="nickname"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          onBlur={validate}
          error={errors.displayName}
        />
        <Input
          label="Parolă"
          type="password"
          autoComplete="new-password"
          hint="Minim 8 caractere."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onBlur={validate}
          error={errors.password}
        />
        <Button type="submit" variant="primary" block loading={submitting}>
          Îmi fac cont
        </Button>
      </form>
    </AuthShell>
  )
}
