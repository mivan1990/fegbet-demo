import { useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { Badge, Button, ConfirmDialog, Input, Modal, Select, Toggle, useToast } from '@/components/ui'
import { DataList } from '@/components/admin/DataList'
import type { Column } from '@/components/admin/DataList'
import { apiErrorMessage } from '@/api/client'
import {
  useAdminPlayers,
  useCreatePlayer,
  useDeletePlayer,
  useUpdatePlayer,
} from '@/api/players'
import type { Player, PlayerPosition } from '@/api/types'

const POSITIONS: { value: string; label: string }[] = [
  { value: '', label: '— fără —' },
  { value: 'GK', label: 'Portar (GK)' },
  { value: 'DEF', label: 'Fundaș (DEF)' },
  { value: 'MID', label: 'Mijlocaș (MID)' },
  { value: 'ATT', label: 'Atacant (ATT)' },
]

interface FormState {
  name: string
  shirt_number: string
  position: string
  is_active: boolean
}

const EMPTY: FormState = { name: '', shirt_number: '', position: '', is_active: true }

export function AdminPlayers() {
  const toast = useToast()
  const { data, isLoading } = useAdminPlayers()
  const createPlayer = useCreatePlayer()
  const updatePlayer = useUpdatePlayer()
  const deletePlayer = useDeletePlayer()

  const [editing, setEditing] = useState<Player | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<FormState>(EMPTY)
  const [nameError, setNameError] = useState<string | null>(null)
  const [toDelete, setToDelete] = useState<Player | null>(null)

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY)
    setNameError(null)
    setFormOpen(true)
  }

  const openEdit = (p: Player) => {
    setEditing(p)
    setForm({
      name: p.name,
      shirt_number: p.shirt_number?.toString() ?? '',
      position: p.position ?? '',
      is_active: p.is_active,
    })
    setNameError(null)
    setFormOpen(true)
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) {
      setNameError('Numele jucătorului e obligatoriu.')
      return
    }
    const body = {
      name: form.name.trim(),
      shirt_number: form.shirt_number ? Number(form.shirt_number) : null,
      position: (form.position || null) as PlayerPosition | null,
      is_active: form.is_active,
    }
    try {
      if (editing) {
        await updatePlayer.mutateAsync({ id: editing.id, body })
        toast.success('Jucător actualizat.')
      } else {
        await createPlayer.mutateAsync(body)
        toast.success('Jucător adăugat.')
      }
      setFormOpen(false)
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  const confirmDelete = async () => {
    if (!toDelete) return
    try {
      const res = await deletePlayer.mutateAsync(toDelete.id)
      toast.success(res.mode === 'soft' ? (res.detail ?? 'Jucător dezactivat.') : 'Jucător șters.')
      setToDelete(null)
    } catch (err) {
      toast.error(apiErrorMessage(err))
      setToDelete(null)
    }
  }

  const columns: Column<Player>[] = [
    { key: 'name', label: 'Nume', hideOnCard: true, render: (p) => p.name },
    {
      key: 'shirt',
      label: 'Tricou',
      render: (p) => <span className="font-mono">{p.shirt_number ?? '—'}</span>,
    },
    { key: 'pos', label: 'Poziție', render: (p) => p.position ?? '—' },
    {
      key: 'active',
      label: 'Stare',
      align: 'right',
      render: (p) =>
        p.is_active ? (
          <Badge tone="success">Activ</Badge>
        ) : (
          <Badge tone="neutral">Inactiv</Badge>
        ),
    },
  ]

  return (
    <>
      <PageHeader
        title="Jucători FEG"
        subtitle={'Lotul pentru piața „Marcator". Ștergerea e soft dacă jucătorul apare pe bilete.'}
        action={
          <Button variant="primary" iconLeft={<Plus className="h-4 w-4" />} onClick={openCreate}>
            Jucător nou
          </Button>
        }
      />

      <DataList
        rows={data ?? []}
        loading={isLoading}
        columns={columns}
        rowKey={(p) => p.id}
        cardTitle={(p) => p.name}
        empty={
          <p className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-white/50">
            Niciun jucător.
          </p>
        }
        actions={(p) => (
          <>
            <Button
              variant="secondary"
              size="sm"
              iconLeft={<Pencil className="h-4 w-4" />}
              onClick={() => openEdit(p)}
              className="max-md:w-full"
            >
              Editează
            </Button>
            <Button
              variant="danger"
              size="sm"
              iconLeft={<Trash2 className="h-4 w-4" />}
              onClick={() => setToDelete(p)}
              className="max-md:w-full"
            >
              Șterge
            </Button>
          </>
        )}
      />

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? 'Editează jucătorul' : 'Jucător nou'}
        fullScreenOnMobile={false}
        footer={
          <>
            <Button variant="ghost" onClick={() => setFormOpen(false)}>
              Renunță
            </Button>
            <Button
              variant="primary"
              onClick={submit}
              loading={createPlayer.isPending || updatePlayer.isPending}
            >
              Salvează
            </Button>
          </>
        }
      >
        <form onSubmit={submit} className="flex flex-col gap-4">
          <Input
            label="Nume"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            error={nameError}
          />
          <Input
            label="Număr de tricou"
            type="number"
            inputMode="numeric"
            value={form.shirt_number}
            onChange={(e) => setForm((f) => ({ ...f, shirt_number: e.target.value }))}
          />
          <Select
            label="Poziție"
            options={POSITIONS}
            value={form.position}
            onChange={(e) => setForm((f) => ({ ...f, position: e.target.value }))}
          />
          {editing && (
            <Toggle
              label="Activ"
              checked={form.is_active}
              onChange={(v) => setForm((f) => ({ ...f, is_active: v }))}
            />
          )}
        </form>
      </Modal>

      <ConfirmDialog
        open={toDelete !== null}
        title={`Ștergi pe „${toDelete?.name}"?`}
        message="Dacă apare deja pe bilete sau ca marcator, va fi doar dezactivat."
        confirmLabel="Șterge"
        danger
        loading={deletePlayer.isPending}
        onConfirm={confirmDelete}
        onClose={() => setToDelete(null)}
      />
    </>
  )
}
