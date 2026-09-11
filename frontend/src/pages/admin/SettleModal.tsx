import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Minus, Plus } from 'lucide-react'
import { Button, Modal, Stepper, useToast } from '@/components/ui'
import { cn } from '@/lib/cn'
import { apiErrorMessage } from '@/api/client'
import { usePlayers } from '@/api/players'
import { useSettleMatch } from '@/api/matches'
import type { Match } from '@/api/types'

interface Props {
  match: Match | null
  onClose: () => void
}

export function SettleModal({ match, onClose }: Props) {
  const toast = useToast()
  const { data: players = [] } = usePlayers()
  const settle = useSettleMatch()

  const [home, setHome] = useState(0)
  const [away, setAway] = useState(0)
  const [penHome, setPenHome] = useState(0)
  const [penAway, setPenAway] = useState(0)
  const [goals, setGoals] = useState<Record<number, number>>({})

  useEffect(() => {
    if (!match) return
    setHome(match.home_score ?? 0)
    setAway(match.away_score ?? 0)
    setPenHome(match.penalties_home ?? 0)
    setPenAway(match.penalties_away ?? 0)
    setGoals({})
  }, [match])

  // Pre-fill scorers on re-validation from the detail endpoint would need a fetch;
  // pentru simplitate re-validarea porneste cu marcatorii la 0 (adminul re-introduce).

  const isDraw = home === away
  // Meciurile de grupă pot rămâne egale, fără penalty-uri (PLAN_GRUPE.md 5.2).
  const needsPenalties = isDraw && match?.phase !== 'GROUP'
  const fegIsHome = !!match?.home_team?.is_feg
  const fegGoals = fegIsHome ? home : away
  const totalScorerGoals = useMemo(
    () => Object.values(goals).reduce((s, g) => s + g, 0),
    [goals],
  )
  const scorerOverflow = match?.has_feg ? totalScorerGoals > fegGoals : false

  const bump = (playerId: number, delta: number) =>
    setGoals((g) => {
      const next = Math.max(0, (g[playerId] ?? 0) + delta)
      return { ...g, [playerId]: next }
    })

  const submit = async () => {
    if (!match) return
    if (scorerOverflow) {
      toast.error('Marcatorii au mai multe goluri decât a marcat FEG.')
      return
    }
    const scorers = Object.entries(goals)
      .filter(([, g]) => g >= 1)
      .map(([pid, g]) => ({ player_id: Number(pid), goals: g }))

    try {
      const res = await settle.mutateAsync({
        id: match.id,
        body: {
          home_score: home,
          away_score: away,
          penalties_home: needsPenalties ? penHome : null,
          penalties_away: needsPenalties ? penAway : null,
          scorers,
        },
      })
      toast.success(
        `Meci ${match.is_settled ? 're-validat' : 'validat'}. ${res.tickets_settled} bilete decontate.`,
      )
      if (res.warning) toast.error(res.warning)
      onClose()
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  return (
    <Modal
      open={match !== null}
      onClose={onClose}
      title={
        match
          ? `${match.is_settled ? 'Re-validează' : 'Validează'}: ${match.home_team?.name ?? 'TBD'} vs ${match.away_team?.name ?? 'TBD'}`
          : 'Validează meci'
      }
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Renunță
          </Button>
          <Button
            variant="primary"
            onClick={submit}
            loading={settle.isPending}
            disabled={scorerOverflow}
          >
            {match?.is_settled ? 'Re-validează' : 'Validează'}
          </Button>
        </>
      }
    >
      {match && (
        <div className="space-y-5">
          {match.is_settled && (
            <p className="flex items-start gap-2 rounded-xl border border-fortuna/40 bg-fortuna/10 p-3 text-sm text-white/80">
              <AlertTriangle className="mt-1 h-4 w-4 shrink-0 text-fortuna" />
              Meciul e deja validat. Salvarea anulează complet punctele vechi și recalculează.
            </p>
          )}

          <div className="space-y-3">
            <Stepper label={`Scor ${match.home_team?.name ?? 'gazde'}`} value={home} onChange={setHome} />
            <Stepper label={`Scor ${match.away_team?.name ?? 'oaspeți'}`} value={away} onChange={setAway} />
          </div>

          {isDraw && match.phase === 'GROUP' && (
            <p className="rounded-xl border border-feg/30 bg-feg/5 p-3 text-sm text-white/70">
              Meci de grupă egal — se validează fără penalty-uri.
            </p>
          )}

          {needsPenalties && (
            <div className="space-y-3 rounded-xl border border-white/10 bg-navy-800 p-3">
              <p className="text-sm font-medium text-white/80">
                Meci egal — completează penalty-urile
              </p>
              <Stepper label="Penalty-uri gazde" value={penHome} onChange={setPenHome} />
              <Stepper label="Penalty-uri oaspeți" value={penAway} onChange={setPenAway} />
              {penHome === penAway && (
                <p className="text-xs text-bet-400">Penalty-urile nu pot fi egale.</p>
              )}
            </div>
          )}

          {match.has_feg && players.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-white/80">Marcatori FEG</p>
                <span
                  className={cn(
                    'font-mono text-xs',
                    scorerOverflow ? 'text-bet-400' : 'text-white/45',
                  )}
                >
                  {totalScorerGoals} / {fegGoals} goluri
                </span>
              </div>
              <ul className="space-y-1">
                {players.map((p) => {
                  const g = goals[p.id] ?? 0
                  return (
                    <li
                      key={p.id}
                      className={cn(
                        'flex items-center justify-between gap-3 rounded-xl px-3 py-2',
                        g > 0 ? 'bg-fortuna/10' : 'bg-navy-800',
                      )}
                    >
                      <span className="text-sm text-white/85">{p.name}</span>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          aria-label={`Scade gol ${p.name}`}
                          onClick={() => bump(p.id, -1)}
                          disabled={g === 0}
                          className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/15 text-white disabled:opacity-40"
                        >
                          <Minus className="h-4 w-4" />
                        </button>
                        <span className="w-6 text-center font-mono tabular-nums text-white">{g}</span>
                        <button
                          type="button"
                          aria-label={`Adaugă gol ${p.name}`}
                          onClick={() => bump(p.id, 1)}
                          className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/15 text-white"
                        >
                          <Plus className="h-4 w-4" />
                        </button>
                      </div>
                    </li>
                  )
                })}
              </ul>
              {scorerOverflow && (
                <p className="text-xs text-bet-400">
                  Suma golurilor marcatorilor depășește ce a marcat FEG.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
