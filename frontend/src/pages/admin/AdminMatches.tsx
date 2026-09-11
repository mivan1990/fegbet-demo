import { useMemo, useState } from 'react'
import { CalendarClock, CheckCircle2, GitBranch, Pencil, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, useToast } from '@/components/ui'
import { DataList } from '@/components/admin/DataList'
import type { Column } from '@/components/admin/DataList'
import { apiErrorMessage } from '@/api/client'
import { formatMatchDateTime } from '@/lib/datetime'
import { useAdminMatches, useDeleteMatch } from '@/api/matches'
import type { Match } from '@/api/types'
import { BracketModal } from './BracketModal'
import { MatchEditModal } from './MatchEditModal'
import { SettleModal } from './SettleModal'

function teamName(m: Match, side: 'home' | 'away') {
  const t = side === 'home' ? m.home_team : m.away_team
  return t ? t.name : 'TBD'
}

function StatusBadge({ m }: { m: Match }) {
  if (m.is_settled) return <Badge tone="success">Validat</Badge>
  if (m.status === 'CANCELLED') return <Badge tone="neutral">Anulat</Badge>
  if (m.is_locked) return <Badge tone="urgent">În desfășurare</Badge>
  if (m.is_bettable) return <Badge tone="info">Deschis</Badge>
  return <Badge tone="neutral">Neprogramat</Badge>
}

export function AdminMatches() {
  const toast = useToast()
  const { data, isLoading } = useAdminMatches()
  const deleteMatch = useDeleteMatch()

  const [bracketOpen, setBracketOpen] = useState(false)
  const [editing, setEditing] = useState<Match | null>(null)
  const [settling, setSettling] = useState<Match | null>(null)
  const [toDelete, setToDelete] = useState<Match | null>(null)

  const rounds = useMemo(() => {
    const map = new Map<number, Match[]>()
    for (const m of data ?? []) {
      const arr = map.get(m.round_no) ?? []
      arr.push(m)
      map.set(m.round_no, arr)
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0])
  }, [data])

  const confirmDelete = async () => {
    if (!toDelete) return
    try {
      await deleteMatch.mutateAsync(toDelete.id)
      toast.success('Meci șters.')
      setToDelete(null)
    } catch (err) {
      toast.error(apiErrorMessage(err))
      setToDelete(null)
    }
  }

  const columns: Column<Match>[] = [
    {
      key: 'match',
      label: 'Meci',
      hideOnCard: true,
      render: (m) => (
        <span>
          {teamName(m, 'home')} <span className="text-white/30">vs</span> {teamName(m, 'away')}
        </span>
      ),
    },
    {
      key: 'when',
      label: 'Data',
      render: (m) =>
        m.scheduled_at ? (
          formatMatchDateTime(m.scheduled_at)
        ) : (
          <span className="text-white/40">nestabilită</span>
        ),
    },
    { key: 'status', label: 'Stare', align: 'right', render: (m) => <StatusBadge m={m} /> },
  ]

  return (
    <>
      <PageHeader
        title="Meciuri"
        subtitle="Generează bracket-ul, apoi pune ora fiecărui meci."
        action={
          <Button
            variant="primary"
            iconLeft={<GitBranch className="h-4 w-4" />}
            onClick={() => setBracketOpen(true)}
          >
            Generează bracket
          </Button>
        }
      />

      {isLoading ? (
        <DataList rows={[]} columns={columns} rowKey={() => 0} cardTitle={() => ''} empty={null} loading />
      ) : rounds.length === 0 ? (
        <EmptyState
          icon={CalendarClock}
          title="Niciun meci"
          line="Generează bracket-ul ca să apară meciurile turneului."
          action={
            <Button variant="primary" onClick={() => setBracketOpen(true)}>
              Generează bracket
            </Button>
          }
        />
      ) : (
        <div className="space-y-8">
          {rounds.map(([roundNo, matches]) => (
            <section key={roundNo}>
              <h2 className="mb-3 font-display text-lg text-white">
                {matches[0].stage_label ?? `Runda ${roundNo}`}
              </h2>
              <DataList
                rows={matches}
                columns={columns}
                rowKey={(m) => m.id}
                cardTitle={(m) => (
                  <>
                    {teamName(m, 'home')} <span className="text-white/30">vs</span> {teamName(m, 'away')}
                  </>
                )}
                empty={null}
                actions={(m) => (
                  <>
                    {m.home_team && m.away_team && (
                      <Button
                        variant={m.is_settled ? 'secondary' : 'primary'}
                        size="sm"
                        iconLeft={<CheckCircle2 className="h-4 w-4" />}
                        onClick={() => setSettling(m)}
                        className="max-md:w-full"
                      >
                        {m.is_settled ? 'Re-validează' : 'Validează meci'}
                      </Button>
                    )}
                    <Button
                      variant="secondary"
                      size="sm"
                      iconLeft={<Pencil className="h-4 w-4" />}
                      onClick={() => setEditing(m)}
                      disabled={m.is_settled}
                      className="max-md:w-full"
                    >
                      Editează
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      iconLeft={<Trash2 className="h-4 w-4" />}
                      onClick={() => setToDelete(m)}
                      disabled={m.is_settled}
                      className="max-md:w-full"
                    >
                      Șterge
                    </Button>
                  </>
                )}
              />
            </section>
          ))}
        </div>
      )}

      <BracketModal open={bracketOpen} onClose={() => setBracketOpen(false)} />
      <MatchEditModal match={editing} onClose={() => setEditing(null)} />
      <SettleModal match={settling} onClose={() => setSettling(null)} />

      <ConfirmDialog
        open={toDelete !== null}
        title="Ștergi meciul?"
        message="Meciurile care avansau în acesta rămân fără destinație. Nu merge dacă are bilete."
        confirmLabel="Șterge"
        danger
        loading={deleteMatch.isPending}
        onConfirm={confirmDelete}
        onClose={() => setToDelete(null)}
      />
    </>
  )
}
