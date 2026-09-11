import { useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { Badge, Button, ConfirmDialog, Input, Modal, Toggle, useToast } from '@/components/ui'
import { DataList } from '@/components/admin/DataList'
import type { Column } from '@/components/admin/DataList'
import { apiErrorMessage } from '@/api/client'
import { useAdminTeams, useCreateTeam, useDeleteTeam, useUpdateTeam } from '@/api/teams'
import type { TeamAdmin } from '@/api/types'

interface FormState {
  name: string
  short_name: string
  logo_url: string
  is_feg: boolean
  is_active: boolean
}

const EMPTY: FormState = { name: '', short_name: '', logo_url: '', is_feg: false, is_active: true }

export function AdminTeams() {
  const toast = useToast()
  const { data, isLoading } = useAdminTeams()
  const createTeam = useCreateTeam()
  const updateTeam = useUpdateTeam()
  const deleteTeam = useDeleteTeam()

  const [editing, setEditing] = useState<TeamAdmin | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<FormState>(EMPTY)
  const [nameError, setNameError] = useState<string | null>(null)
  const [toDelete, setToDelete] = useState<TeamAdmin | null>(null)

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY)
    setNameError(null)
    setFormOpen(true)
  }

  const openEdit = (team: TeamAdmin) => {
    setEditing(team)
    setForm({
      name: team.name,
      short_name: team.short_name ?? '',
      logo_url: team.logo_url ?? '',
      is_feg: team.is_feg,
      is_active: team.is_active,
    })
    setNameError(null)
    setFormOpen(true)
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) {
      setNameError('Numele echipei e obligatoriu.')
      return
    }
    const body = {
      name: form.name.trim(),
      short_name: form.short_name.trim() || null,
      logo_url: form.logo_url.trim() || null,
      is_feg: form.is_feg,
      is_active: form.is_active,
    }
    try {
      if (editing) {
        await updateTeam.mutateAsync({ id: editing.id, body })
        toast.success('Echipă actualizată.')
      } else {
        await createTeam.mutateAsync(body)
        toast.success('Echipă adăugată.')
      }
      setFormOpen(false)
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  const confirmDelete = async () => {
    if (!toDelete) return
    try {
      await deleteTeam.mutateAsync(toDelete.id)
      toast.success('Echipă ștearsă.')
      setToDelete(null)
    } catch (err) {
      toast.error(apiErrorMessage(err))
      setToDelete(null)
    }
  }

  const columns: Column<TeamAdmin>[] = [
    { key: 'name', label: 'Nume', hideOnCard: true, render: (t) => t.name },
    {
      key: 'short',
      label: 'Prescurtare',
      render: (t) => <span className="font-mono">{t.short_name ?? '—'}</span>,
    },
    {
      key: 'flags',
      label: 'Etichete',
      render: (t) => (
        <div className="flex flex-wrap justify-end gap-1 md:justify-start">
          {t.is_feg && <Badge tone="info">FEG</Badge>}
          {!t.is_active && <Badge tone="neutral">Dezactivată</Badge>}
        </div>
      ),
    },
    {
      key: 'usage',
      label: 'Folosire',
      align: 'right',
      render: (t) => (
        <span className="font-mono text-xs tabular-nums text-white/60">
          {t.player_count} jucători · {t.match_count} meciuri
        </span>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        title="Echipe"
        subtitle="Adaugă adversarii turneului. O singură echipă poate fi FEG."
        action={
          <Button variant="primary" iconLeft={<Plus className="h-4 w-4" />} onClick={openCreate}>
            Echipă nouă
          </Button>
        }
      />

      <DataList
        rows={data ?? []}
        loading={isLoading}
        columns={columns}
        rowKey={(t) => t.id}
        cardTitle={(t) => t.name}
        empty={
          <p className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-white/50">
            Nicio echipă încă. Adaugă prima.
          </p>
        }
        actions={(t) => (
          <>
            <Button
              variant="secondary"
              size="sm"
              iconLeft={<Pencil className="h-4 w-4" />}
              onClick={() => openEdit(t)}
              className="max-md:w-full"
            >
              Editează
            </Button>
            <Button
              variant="danger"
              size="sm"
              iconLeft={<Trash2 className="h-4 w-4" />}
              onClick={() => setToDelete(t)}
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
        title={editing ? 'Editează echipa' : 'Echipă nouă'}
        fullScreenOnMobile={false}
        footer={
          <>
            <Button variant="ghost" onClick={() => setFormOpen(false)}>
              Renunță
            </Button>
            <Button
              variant="primary"
              onClick={submit}
              loading={createTeam.isPending || updateTeam.isPending}
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
            label="Prescurtare (3-4 litere)"
            hint={'Pentru bracket. Ex. „MKT".'}
            value={form.short_name}
            maxLength={4}
            onChange={(e) => setForm((f) => ({ ...f, short_name: e.target.value }))}
          />
          <Input
            label="Logo URL"
            hint="Opțional."
            value={form.logo_url}
            onChange={(e) => setForm((f) => ({ ...f, logo_url: e.target.value }))}
          />
          <Toggle
            label="Este echipa FEG"
            hint={'Doar o echipă poate fi FEG. Piața „Marcator" apare doar la meciurile ei.'}
            checked={form.is_feg}
            onChange={(v) => setForm((f) => ({ ...f, is_feg: v }))}
          />
          {editing && (
            <Toggle
              label="Activă"
              checked={form.is_active}
              onChange={(v) => setForm((f) => ({ ...f, is_active: v }))}
            />
          )}
        </form>
      </Modal>

      <ConfirmDialog
        open={toDelete !== null}
        title={`Ștergi „${toDelete?.name}"?`}
        message="Dacă echipa e folosită într-un meci sau are jucători, serverul refuză — dezactiveaz-o în loc."
        confirmLabel="Șterge"
        danger
        loading={deleteTeam.isPending}
        onConfirm={confirmDelete}
        onClose={() => setToDelete(null)}
      />
    </>
  )
}
