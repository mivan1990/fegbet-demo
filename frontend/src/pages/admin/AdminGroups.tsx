import { useState } from 'react'
import { CheckCircle2, GitBranch, Layers, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, useToast } from '@/components/ui'
import { GroupStandings } from '@/components/group/GroupStandings'
import { apiErrorMessage } from '@/api/client'
import { useAdminGroups, useDeleteGroup, useGenerateBracketFromGroups } from '@/api/groups'
import type { Group } from '@/api/types'
import { GroupGenerateModal } from './GroupGenerateModal'
import { FinalizeGroupModal } from './FinalizeGroupModal'

function StatusBadge({ g }: { g: Group }) {
  if (g.is_finalized) return <Badge tone="success">Finalizată</Badge>
  if (g.is_complete) return <Badge tone="info">Meciuri încheiate</Badge>
  if (g.is_locked) return <Badge tone="urgent">În desfășurare</Badge>
  return <Badge tone="neutral">Deschisă</Badge>
}

export function AdminGroups() {
  const toast = useToast()
  const { data, isLoading } = useAdminGroups()
  const deleteGroup = useDeleteGroup()
  const generateBracket = useGenerateBracketFromGroups()

  const [generateOpen, setGenerateOpen] = useState(false)
  const [finalizing, setFinalizing] = useState<Group | null>(null)
  const [toDelete, setToDelete] = useState<Group | null>(null)

  const groups = data ?? []
  const allFinalized = groups.length > 0 && groups.every((g) => g.is_finalized)

  const confirmDelete = async () => {
    if (!toDelete) return
    try {
      await deleteGroup.mutateAsync(toDelete.id)
      toast.success('Grupă ștearsă.')
      setToDelete(null)
    } catch (err) {
      toast.error(apiErrorMessage(err))
      setToDelete(null)
    }
  }

  const buildBracket = async () => {
    try {
      await generateBracket.mutateAsync()
      toast.success('Bracket generat din grupe.')
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  return (
    <>
      <PageHeader
        title="Grupe"
        subtitle="Tragerea la sorți pe grupe și pronosticul de calificare al userilor."
        action={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              iconLeft={<GitBranch className="h-4 w-4" />}
              onClick={buildBracket}
              loading={generateBracket.isPending}
              disabled={!allFinalized}
            >
              Generează bracket din grupe
            </Button>
            <Button
              variant="primary"
              iconLeft={<Layers className="h-4 w-4" />}
              onClick={() => setGenerateOpen(true)}
            >
              Generează grupe
            </Button>
          </div>
        }
      />

      {isLoading ? null : groups.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="Nicio grupă"
          line="Generează grupele ca să apară meciurile de grupă și pronosticurile userilor."
          action={
            <Button variant="primary" onClick={() => setGenerateOpen(true)}>
              Generează grupe
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {groups.map((g) => (
            <section
              key={g.id}
              className="rounded-2xl border border-white/10 bg-navy-900 p-4 shadow-card md:p-6"
            >
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="font-display text-lg text-white">Grupa {g.name}</h2>
                <StatusBadge g={g} />
              </div>
              <GroupStandings standings={g.standings} qualifiersCount={g.qualifiers_count} className="mb-4" />
              {g.is_finalized && g.qualified.length > 0 && (
                <p className="mb-4 text-sm text-white/60">
                  Calificate: {g.qualified.map((t) => t.name).join(', ')}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={g.is_finalized ? 'secondary' : 'primary'}
                  size="sm"
                  iconLeft={<CheckCircle2 className="h-4 w-4" />}
                  onClick={() => setFinalizing(g)}
                  className="max-md:w-full"
                >
                  {g.is_finalized ? 'Re-finalizează' : 'Finalizează'}
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  iconLeft={<Trash2 className="h-4 w-4" />}
                  onClick={() => setToDelete(g)}
                  disabled={g.matches.some((m) => m.is_settled)}
                  className="max-md:w-full"
                >
                  Șterge
                </Button>
              </div>
            </section>
          ))}
        </div>
      )}

      <GroupGenerateModal open={generateOpen} onClose={() => setGenerateOpen(false)} />
      <FinalizeGroupModal group={finalizing} onClose={() => setFinalizing(null)} />

      <ConfirmDialog
        open={toDelete !== null}
        title={`Ștergi grupa ${toDelete?.name ?? ''}?`}
        message="Nu merge dacă grupa are meciuri validate sau pronosticuri plasate."
        confirmLabel="Șterge"
        danger
        loading={deleteGroup.isPending}
        onConfirm={confirmDelete}
        onClose={() => setToDelete(null)}
      />
    </>
  )
}
