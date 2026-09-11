import { useEffect, useState } from 'react'
import { Button, Input, Modal, Select, useToast } from '@/components/ui'
import { apiErrorMessage } from '@/api/client'
import { isoToLocalInput, localInputToIso } from '@/lib/datetimeLocal'
import { useTeams } from '@/api/teams'
import { useUpdateMatch } from '@/api/matches'
import type { Match } from '@/api/types'

interface Props {
  match: Match | null
  onClose: () => void
}

export function MatchEditModal({ match, onClose }: Props) {
  const toast = useToast()
  const { data: teams } = useTeams()
  const updateMatch = useUpdateMatch()

  const [homeId, setHomeId] = useState('')
  const [awayId, setAwayId] = useState('')
  const [stage, setStage] = useState('')
  const [when, setWhen] = useState('')

  useEffect(() => {
    if (!match) return
    setHomeId(match.home_team?.id?.toString() ?? '')
    setAwayId(match.away_team?.id?.toString() ?? '')
    setStage(match.stage_label ?? '')
    setWhen(isoToLocalInput(match.scheduled_at))
  }, [match])

  const teamOptions = [
    { value: '', label: 'TBD (nedeterminat)' },
    ...(teams ?? []).map((t) => ({ value: t.id.toString(), label: t.name })),
  ]

  const save = async () => {
    if (!match) return
    try {
      await updateMatch.mutateAsync({
        id: match.id,
        body: {
          home_team_id: homeId ? Number(homeId) : null,
          away_team_id: awayId ? Number(awayId) : null,
          stage_label: stage.trim() || null,
          scheduled_at: localInputToIso(when),
        },
      })
      toast.success('Meci actualizat.')
      onClose()
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  return (
    <Modal
      open={match !== null}
      onClose={onClose}
      title={match ? `${match.stage_label ?? 'Meci'} · poziția ${match.bracket_position + 1}` : 'Meci'}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Renunță
          </Button>
          <Button variant="primary" onClick={save} loading={updateMatch.isPending}>
            Salvează
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Select label="Gazde" options={teamOptions} value={homeId} onChange={(e) => setHomeId(e.target.value)} />
        <Select label="Oaspeți" options={teamOptions} value={awayId} onChange={(e) => setAwayId(e.target.value)} />
        <Input
          label="Etichetă etapă"
          hint={'Ex. „Sferturi". Bracket-ul generat le pune singur.'}
          value={stage}
          onChange={(e) => setStage(e.target.value)}
        />
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-white/80" htmlFor="match-when">
            Data și ora (ora ta locală)
          </label>
          <input
            id="match-when"
            type="datetime-local"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            className="h-11 rounded-xl border border-white/10 bg-navy-800 px-4 text-base text-white focus:border-white/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-fortuna focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950"
          />
          {when && (
            <button
              type="button"
              onClick={() => setWhen('')}
              className="self-start text-xs text-bet-400 hover:underline"
            >
              Șterge programarea
            </button>
          )}
          <p className="text-xs text-white/45">
            Cât timp nu are dată, nu se poate paria pe meci.
          </p>
        </div>
      </div>
    </Modal>
  )
}
