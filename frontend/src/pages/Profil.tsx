import { useState } from 'react'
import { z } from 'zod'
import { Button, Card, Input, useToast } from '@/components/ui'
import { PageHeader } from '@/components/layout'
import { useAuth } from '@/auth/AuthContext'
import { api, apiErrorMessage } from '@/api/client'
import { formatFull } from '@/lib/datetime'

const schema = z
  .object({
    old_password: z.string().min(1, 'Scrie parola actuală.'),
    new_password: z.string().min(8, 'Minim 8 caractere.'),
    confirm: z.string().min(1, 'Confirmă parola nouă.'),
  })
  .refine((d) => d.new_password === d.confirm, {
    path: ['confirm'],
    message: 'Parolele nu se potrivesc.',
  })

export function Profil() {
  const { user, refresh } = useAuth()
  const toast = useToast()
  const [form, setForm] = useState({ old_password: '', new_password: '', confirm: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  if (!user) return null

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  const validate = () => {
    const result = schema.safeParse(form)
    if (result.success) {
      setErrors({})
      return result.data
    }
    const next: Record<string, string> = {}
    for (const issue of result.error.issues) next[String(issue.path[0])] = issue.message
    setErrors(next)
    return null
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const values = validate()
    if (!values) return
    setSubmitting(true)
    try {
      await api.put('/auth/password', {
        old_password: values.old_password,
        new_password: values.new_password,
      })
      toast.success('Parola schimbată.')
      setForm({ old_password: '', new_password: '', confirm: '' })
      await refresh()
    } catch (err) {
      toast.error(apiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <PageHeader title="Profil" subtitle="Datele tale și parola." />

      <div className="grid gap-3 lg:grid-cols-2">
        <Card eyebrow="Cont" title={user.display_name}>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-white/45">Email</dt>
              <dd className="text-white/80">{user.email}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-white/45">Puncte</dt>
              <dd className="font-mono tabular-nums text-fortuna">{user.points}p</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-white/45">Membru din</dt>
              <dd className="text-white/80">{formatFull(user.created_at)}</dd>
            </div>
            {user.is_admin && (
              <div className="flex justify-between gap-4">
                <dt className="text-white/45">Rol</dt>
                <dd className="text-feg-400">Administrator</dd>
              </div>
            )}
          </dl>
        </Card>

        <Card eyebrow="Securitate" title="Schimbă parola">
          <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
            <Input
              label="Parola actuală"
              type="password"
              autoComplete="current-password"
              value={form.old_password}
              onChange={set('old_password')}
              onBlur={validate}
              error={errors.old_password}
            />
            <Input
              label="Parola nouă"
              type="password"
              autoComplete="new-password"
              value={form.new_password}
              onChange={set('new_password')}
              onBlur={validate}
              error={errors.new_password}
            />
            <Input
              label="Confirmă parola nouă"
              type="password"
              autoComplete="new-password"
              value={form.confirm}
              onChange={set('confirm')}
              onBlur={validate}
              error={errors.confirm}
            />
            <Button type="submit" variant="primary" loading={submitting}>
              Salvează parola
            </Button>
          </form>
        </Card>
      </div>
    </>
  )
}
