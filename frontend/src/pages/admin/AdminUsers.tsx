import { useState } from 'react'
import { KeyRound, Shield, ShieldOff, UserCheck, UserX } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { Badge, Button, ConfirmDialog, Input, Modal, useToast } from '@/components/ui'
import { DataList } from '@/components/admin/DataList'
import type { Column } from '@/components/admin/DataList'
import { apiErrorMessage } from '@/api/client'
import { useAuth } from '@/auth/AuthContext'
import { useAdminUsers, useSetUserActive, useSetUserPassword, useSetUserRole } from '@/api/admin'
import { formatFull } from '@/lib/datetime'
import type { AdminUser } from '@/api/types'

const MIN_PASSWORD = 8

export function AdminUsers() {
  const toast = useToast()
  const { user: me } = useAuth()
  const { data, isLoading } = useAdminUsers()
  const setPassword = useSetUserPassword()
  const setRole = useSetUserRole()
  const setActive = useSetUserActive()

  const [pwTarget, setPwTarget] = useState<AdminUser | null>(null)
  const [pw, setPw] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [roleTarget, setRoleTarget] = useState<AdminUser | null>(null)
  const [activeTarget, setActiveTarget] = useState<AdminUser | null>(null)

  const isMe = (u: AdminUser) => u.id === me?.id

  const submitPassword = async () => {
    if (!pwTarget) return
    if (pw.length < MIN_PASSWORD) {
      setPwError(`Minim ${MIN_PASSWORD} caractere.`)
      return
    }
    try {
      await setPassword.mutateAsync({ id: pwTarget.id, new_password: pw })
      toast.success(`Parolă resetată pentru ${pwTarget.display_name}.`)
      setPwTarget(null)
      setPw('')
      setPwError(null)
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  const submitRole = async () => {
    if (!roleTarget) return
    try {
      const updated = await setRole.mutateAsync({
        id: roleTarget.id,
        is_admin: !roleTarget.is_admin,
      })
      toast.success(updated.is_admin ? 'Utilizator promovat admin.' : 'Drepturi de admin retrase.')
      setRoleTarget(null)
    } catch (err) {
      toast.error(apiErrorMessage(err))
      setRoleTarget(null)
    }
  }

  const submitActive = async () => {
    if (!activeTarget) return
    try {
      const updated = await setActive.mutateAsync({
        id: activeTarget.id,
        is_active: !activeTarget.is_active,
      })
      toast.success(updated.is_active ? 'Cont reactivat.' : 'Cont dezactivat.')
      setActiveTarget(null)
    } catch (err) {
      toast.error(apiErrorMessage(err))
      setActiveTarget(null)
    }
  }

  const columns: Column<AdminUser>[] = [
    {
      key: 'name',
      label: 'Nume',
      hideOnCard: true,
      render: (u) => <span className="font-medium text-white">{u.display_name}</span>,
    },
    {
      key: 'email',
      label: 'Email',
      render: (u) => <span className="font-mono text-xs text-white/70">{u.email}</span>,
    },
    {
      key: 'points',
      label: 'Puncte',
      align: 'right',
      render: (u) => <span className="font-mono tabular-nums text-fortuna">{u.points}p</span>,
    },
    {
      key: 'role',
      label: 'Rol & stare',
      render: (u) => (
        <div className="flex flex-wrap justify-end gap-1 md:justify-start">
          {u.is_admin && <Badge tone="info">Admin</Badge>}
          {!u.is_active && <Badge tone="neutral">Dezactivat</Badge>}
          {isMe(u) && <Badge tone="neutral">Tu</Badge>}
        </div>
      ),
    },
    {
      key: 'last_login',
      label: 'Ultima logare',
      align: 'right',
      render: (u) => (
        <span className="font-mono text-xs text-white/50">{formatFull(u.last_login_at)}</span>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        title="Utilizatori"
        subtitle="Colegii înscriși. Resetezi parole, dai sau iei drepturi de admin, dezactivezi conturi."
      />

      <DataList
        rows={data ?? []}
        loading={isLoading}
        columns={columns}
        rowKey={(u) => u.id}
        cardTitle={(u) => u.display_name}
        empty={
          <p className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-white/50">
            Niciun utilizator încă.
          </p>
        }
        actions={(u) => (
          <>
            <Button
              variant="secondary"
              size="sm"
              iconLeft={<KeyRound className="h-4 w-4" />}
              onClick={() => {
                setPwTarget(u)
                setPw('')
                setPwError(null)
              }}
              className="max-md:w-full"
            >
              Parolă
            </Button>
            <Button
              variant="secondary"
              size="sm"
              iconLeft={u.is_admin ? <ShieldOff className="h-4 w-4" /> : <Shield className="h-4 w-4" />}
              onClick={() => setRoleTarget(u)}
              disabled={isMe(u)}
              className="max-md:w-full"
            >
              {u.is_admin ? 'Scoate admin' : 'Fă admin'}
            </Button>
            <Button
              variant={u.is_active ? 'danger' : 'primary'}
              size="sm"
              iconLeft={u.is_active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
              onClick={() => setActiveTarget(u)}
              disabled={isMe(u)}
              className="max-md:w-full"
            >
              {u.is_active ? 'Dezactivează' : 'Activează'}
            </Button>
          </>
        )}
      />

      <Modal
        open={pwTarget !== null}
        onClose={() => setPwTarget(null)}
        title={`Parolă nouă pentru ${pwTarget?.display_name ?? ''}`}
        fullScreenOnMobile={false}
        footer={
          <>
            <Button variant="ghost" onClick={() => setPwTarget(null)}>
              Renunță
            </Button>
            <Button variant="primary" onClick={submitPassword} loading={setPassword.isPending}>
              Setează parola
            </Button>
          </>
        }
      >
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void submitPassword()
          }}
          className="flex flex-col gap-4"
        >
          <p className="text-sm text-white/60">
            Serverul e intern, fără email. Comunică parola nouă colegului direct.
          </p>
          <Input
            label="Parolă nouă"
            type="text"
            autoComplete="new-password"
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            error={pwError}
            hint={`Minim ${MIN_PASSWORD} caractere.`}
          />
        </form>
      </Modal>

      <ConfirmDialog
        open={roleTarget !== null}
        title={
          roleTarget?.is_admin
            ? `Scoți drepturile de admin lui ${roleTarget?.display_name}?`
            : `Îl faci admin pe ${roleTarget?.display_name}?`
        }
        message={
          roleTarget?.is_admin
            ? 'Nu va mai avea acces la panoul de administrare. Trebuie să rămână cel puțin un admin.'
            : 'Va putea administra echipe, meciuri, valida rezultate și vedea logurile.'
        }
        confirmLabel={roleTarget?.is_admin ? 'Scoate admin' : 'Fă admin'}
        danger={roleTarget?.is_admin}
        loading={setRole.isPending}
        onConfirm={submitRole}
        onClose={() => setRoleTarget(null)}
      />

      <ConfirmDialog
        open={activeTarget !== null}
        title={
          activeTarget?.is_active
            ? `Dezactivezi contul lui ${activeTarget?.display_name}?`
            : `Reactivezi contul lui ${activeTarget?.display_name}?`
        }
        message={
          activeTarget?.is_active
            ? 'Nu se va mai putea autentifica. Biletele și punctele rămân în clasament până îl reactivezi.'
            : 'Va putea din nou să se autentifice și să parieze.'
        }
        confirmLabel={activeTarget?.is_active ? 'Dezactivează' : 'Activează'}
        danger={activeTarget?.is_active}
        loading={setActive.isPending}
        onConfirm={submitActive}
        onClose={() => setActiveTarget(null)}
      />
    </>
  )
}
