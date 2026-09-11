import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { Ticket, Trophy } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  Chip,
  ConfirmDialog,
  Countdown,
  EmptyState,
  Input,
  MatchCardSkeleton,
  Modal,
  Select,
  Skeleton,
  Stepper,
  Toggle,
  useToast,
} from '@/components/ui'
import { PageHeader } from '@/components/layout'
import { GroupStandings } from '@/components/group/GroupStandings'
import { QualifyPicker } from '@/components/group/QualifyPicker'
import type { StandingRow, TeamRef } from '@/api/types'

const SAMPLE_TEAMS: TeamRef[] = [
  { id: 1, name: 'Marketing FC', short_name: 'MKT', is_feg: false },
  { id: 2, name: 'IT Support', short_name: 'IT', is_feg: false },
  { id: 3, name: 'Vânzări United', short_name: 'VNZ', is_feg: false },
  { id: 4, name: 'Resurse Umane', short_name: 'RU', is_feg: false },
]

const SAMPLE_STANDINGS: StandingRow[] = [
  { team_id: 1, team: SAMPLE_TEAMS[0], played: 3, won: 3, drawn: 0, lost: 0, goals_for: 7, goals_against: 2, goal_diff: 5, points: 9, rank: 1, tied_with: [] },
  { team_id: 2, team: SAMPLE_TEAMS[1], played: 3, won: 2, drawn: 0, lost: 1, goals_for: 5, goals_against: 3, goal_diff: 2, points: 6, rank: 2, tied_with: [] },
  { team_id: 3, team: SAMPLE_TEAMS[2], played: 3, won: 0, drawn: 1, lost: 2, goals_for: 2, goals_against: 6, goal_diff: -4, points: 1, rank: 3, tied_with: [4] },
  { team_id: 4, team: SAMPLE_TEAMS[3], played: 3, won: 0, drawn: 1, lost: 2, goals_for: 2, goals_against: 6, goal_diff: -4, points: 1, rank: 3, tied_with: [3] },
]

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="mb-4 font-display text-2xl text-white">{title}</h2>
      <div className="space-y-6">{children}</div>
    </section>
  )
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-navy-900 p-4">
      <span className="text-xs uppercase tracking-wider text-white/40">{label}</span>
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </div>
  )
}

const SWATCHES: { name: string; className: string; hex: string }[] = [
  { name: 'navy-950', className: 'bg-navy-950', hex: '#070B1A' },
  { name: 'navy-900', className: 'bg-navy-900', hex: '#0B1229' },
  { name: 'navy-800', className: 'bg-navy-800', hex: '#101B3D' },
  { name: 'navy-700', className: 'bg-navy-700', hex: '#16264F' },
  { name: 'navy-600', className: 'bg-navy-600', hex: '#1D3468' },
  { name: 'feg', className: 'bg-feg', hex: '#1E5BFF' },
  { name: 'feg-400', className: 'bg-feg-400', hex: '#4E82FF' },
  { name: 'fortuna', className: 'bg-fortuna', hex: '#FFC800' },
  { name: 'fortuna-400', className: 'bg-fortuna-400', hex: '#FFD84D' },
  { name: 'bet', className: 'bg-bet', hex: '#F03A2E' },
  { name: 'bet-400', className: 'bg-bet-400', hex: '#FF6A5E' },
  { name: 'paper', className: 'bg-paper', hex: '#FBF7EE' },
]

export function KitchenSink() {
  const toast = useToast()
  const [selectedChip, setSelectedChip] = useState<string | null>('over25')
  const [modalOpen, setModalOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmLoading, setConfirmLoading] = useState(false)
  const [name, setName] = useState('')
  const [showError, setShowError] = useState(false)
  const [toggleOn, setToggleOn] = useState(true)
  const [stepperValue, setStepperValue] = useState(2)
  const [qualifyPicked, setQualifyPicked] = useState<number[]>([1])

  const targets = useMemo(
    () => ({
      far: new Date(Date.now() + 3 * 24 * 3600 * 1000).toISOString(),
      urgent: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
      expired: new Date(Date.now() - 60 * 1000).toISOString(),
    }),
    [],
  )

  return (
    <>
      <PageHeader
        title="Kitchen Sink"
        subtitle="Oglinda design system-ului. Fiecare componenta, in fiecare stare. Doar in development."
      />

      <Section title="Paleta">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {SWATCHES.map((s) => (
            <div key={s.name} className="overflow-hidden rounded-xl border border-white/10">
              <div className={`${s.className} h-16`} />
              <div className="bg-navy-900 px-3 py-2">
                <p className="text-sm text-white">{s.name}</p>
                <p className="font-mono text-xs text-white/40">{s.hex}</p>
              </div>
            </div>
          ))}
        </div>
        <p className="text-sm text-white/50">
          Raport 60 / 30 / 10: albastru (structura) · galben (accent) · rosu (urgenta).
        </p>
      </Section>

      <Section title="Tipografie">
        <Row label="Display — Bricolage Grotesque">
          <p className="font-display text-4xl text-white">Regele biletelor · 17 puncte</p>
        </Row>
        <Row label="Text — Inter (cu diacritice)">
          <p className="text-base text-white/80">
            Înregistrează-te, alege-ți selecțiile și bagă biletul. Fotbalul e imprevizibil, tu mai puțin.
          </p>
        </Row>
        <Row label="Mono — JetBrains Mono (tabular-nums)">
          <p className="font-mono text-lg tabular-nums text-fortuna">
            #FEG-000123 · 2 - 1 · 18:30 · +9p
          </p>
        </Row>
      </Section>

      <Section title="Button">
        <Row label="Variante (md)">
          <Button variant="primary">BAG BILETUL</Button>
          <Button variant="secondary">Anuleaza</Button>
          <Button variant="danger">Sterge biletul</Button>
          <Button variant="ghost">Mai schimb o data</Button>
        </Row>
        <Row label="Dimensiuni">
          <Button variant="primary" size="sm">
            sm
          </Button>
          <Button variant="primary" size="md">
            md
          </Button>
          <Button variant="primary" size="lg">
            lg — CTA principal
          </Button>
        </Row>
        <Row label="Stari">
          <Button variant="primary" disabled>
            disabled
          </Button>
          <Button variant="primary" loading>
            loading
          </Button>
          <Button variant="secondary" iconLeft={<Trophy className="h-4 w-4" />}>
            cu icon
          </Button>
        </Row>
        <Row label="Block (bare mobile)">
          <div className="w-full max-w-sm">
            <Button variant="primary" block>
              BAG BILETUL
            </Button>
          </div>
        </Row>
        <p className="text-sm text-white/50">
          Hover (+6% luminozitate), active (scale .98) si focus-visible (inel galben) se vad la interactiune.
        </p>
      </Section>

      <Section title="Chip — optiunile de pariere">
        <Row label="Stari">
          <div className="w-28">
            <Chip
              label="FEG"
              points={3}
              selected={selectedChip === 'feg'}
              onClick={() => setSelectedChip((v) => (v === 'feg' ? null : 'feg'))}
            />
          </div>
          <div className="w-28">
            <Chip
              label="Peste"
              hint="2,5"
              points={3}
              selected={selectedChip === 'over25'}
              onClick={() => setSelectedChip((v) => (v === 'over25' ? null : 'over25'))}
            />
          </div>
          <div className="w-28">
            <Chip label="EGAL" points={4} disabled />
          </div>
        </Row>
        <p className="text-sm text-white/50">
          Un tap selecteaza, al doilea deselecteaza. Punctele apar mic, font-mono: <code>+3p</code>.
        </p>
      </Section>

      <Section title="Card">
        <div className="grid gap-3 md:grid-cols-2">
          <Card eyebrow="Sferturi · SÂM 14 sept" title="FEG vs Marketing">
            <p className="text-sm text-white/60">Card standard, fara accent.</p>
          </Card>
          <Card eyebrow="Urgent" title="Se inchide curand" accent="bet">
            <p className="text-sm text-white/60">Accent rosu pe margine.</p>
          </Card>
          <Card eyebrow="Accent galben" title="Selectat" accent="fortuna">
            <p className="text-sm text-white/60">Un card = albastru + o singura culoare de accent.</p>
          </Card>
          <Card
            eyebrow="Cu footer"
            title="Biletul tau"
            accent="feg"
            footer={
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm">
                  Renunta
                </Button>
                <Button variant="primary" size="sm">
                  Salveaza
                </Button>
              </div>
            }
          >
            <p className="text-sm text-white/60">4 selectii · poti castiga 12p</p>
          </Card>
        </div>
      </Section>

      <Section title="Badge">
        <Row label="Tonuri">
          <Badge tone="neutral">Deschis</Badge>
          <Badge tone="success">Castigat</Badge>
          <Badge tone="urgent">Se inchide</Badge>
          <Badge tone="info">Meciul nostru</Badge>
        </Row>
        <Row label="Pulse (doar countdown urgent)">
          <Badge tone="urgent" pulse>
            04:12
          </Badge>
        </Row>
      </Section>

      <Section title="Input & Select">
        <div className="grid max-w-md gap-4">
          <Input
            label="Nume afisat"
            placeholder="ex. Marius P."
            value={name}
            onChange={(e) => setName(e.target.value)}
            hint="Asa te vad ceilalti in clasament."
          />
          <Input
            label="Email"
            type="email"
            inputMode="email"
            placeholder="nume@exemplu"
            error={showError ? 'Nu am putut crea contul cu acest email.' : null}
          />
          <Input label="Camp dezactivat" value="blocat" disabled onChange={() => {}} />
          <Select
            label="Pozitie"
            placeholder="Alege o pozitie"
            options={[
              { value: 'GK', label: 'Portar' },
              { value: 'DEF', label: 'Fundas' },
              { value: 'MID', label: 'Mijlocas' },
              { value: 'ATT', label: 'Atacant' },
            ]}
          />
          <Select
            label="Select cu eroare"
            options={[{ value: 'x', label: 'Optiune' }]}
            error="Alege ceva, te rog."
          />
          <Button variant="secondary" size="sm" onClick={() => setShowError((v) => !v)}>
            Comuta eroarea
          </Button>
          <div className="space-y-4 rounded-xl border border-white/10 bg-navy-900 p-4">
            <Toggle
              label="Este echipa FEG"
              hint="Comutator on/off pentru formularele de admin."
              checked={toggleOn}
              onChange={setToggleOn}
            />
            <Stepper label="Scor gazde" value={stepperValue} onChange={setStepperValue} />
          </div>
        </div>
      </Section>

      <Section title="Countdown">
        <Row label="Peste 15 min / sub 15 min (pulseaza) / expirat">
          <Countdown target={targets.far} />
          <Countdown target={targets.urgent} />
          <Countdown target={targets.expired} />
          <Countdown target={null} />
        </Row>
      </Section>

      <Section title="GroupStandings — clasament de grupă">
        <GroupStandings standings={SAMPLE_STANDINGS} qualifiersCount={2} />
        <p className="text-sm text-white/50">
          Primele doua locuri au fundal verde si „→ sferturi"; echipele nedepartajabile primesc
          Badge „egale".
        </p>
      </Section>

      <Section title="QualifyPicker — pronosticul de grupă">
        <Row label="Interactiv (alege exact 2)">
          <div className="w-full">
            <QualifyPicker
              teams={SAMPLE_TEAMS}
              qualifiersCount={2}
              value={qualifyPicked}
              onChange={setQualifyPicked}
            />
          </div>
        </Row>
        <Row label="Dezactivat (pronostic blocat)">
          <div className="w-full">
            <QualifyPicker
              teams={SAMPLE_TEAMS}
              qualifiersCount={2}
              value={[1, 2]}
              onChange={() => {}}
              disabled
            />
          </div>
        </Row>
      </Section>

      <Section title="EmptyState">
        <EmptyState
          icon={Ticket}
          title="N-ai niciun bilet"
          line="N-ai pariat pe nimic inca. Curaj!"
          action={<Button variant="primary">Vezi meciurile</Button>}
        />
      </Section>

      <Section title="Skeleton">
        <div className="space-y-3">
          <div className="flex gap-3">
            <Skeleton className="h-11 w-11" rounded="full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </div>
          <MatchCardSkeleton />
        </div>
      </Section>

      <Section title="Toast">
        <Row label="Declanseaza">
          <Button variant="primary" onClick={() => toast.success('Biletul e bagat. Bafta!')}>
            Succes
          </Button>
          <Button variant="danger" onClick={() => toast.error('Am pierdut mingea. Mai incearca.')}>
            Eroare
          </Button>
          <Button variant="secondary" onClick={() => toast.info('Meciul incepe in 15 minute.')}>
            Info
          </Button>
        </Row>
      </Section>

      <Section title="Modal & Confirmare">
        <Row label="Deschide">
          <Button variant="secondary" onClick={() => setModalOpen(true)}>
            Modal
          </Button>
          <Button variant="danger" onClick={() => setConfirmOpen(true)}>
            Confirmare de stergere
          </Button>
        </Row>
      </Section>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Valideaza meciul"
        footer={
          <>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Renunta
            </Button>
            <Button variant="primary" onClick={() => setModalOpen(false)}>
              Salveaza
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-white/70">
            Pe mobil, modalul e ecran complet cu header fix si actiuni jos. Pe desktop e centrat.
          </p>
          <Input label="Scor gazde" type="number" inputMode="numeric" defaultValue={2} />
          <Input label="Scor oaspeti" type="number" inputMode="numeric" defaultValue={1} />
        </div>
      </Modal>

      <ConfirmDialog
        open={confirmOpen}
        title="Stergi biletul?"
        message="Selectiile se pierd. Poti face altul cat timp meciul n-a inceput."
        confirmLabel="Sterge"
        danger
        loading={confirmLoading}
        onConfirm={() => {
          setConfirmLoading(true)
          window.setTimeout(() => {
            setConfirmLoading(false)
            setConfirmOpen(false)
            toast.success('Gata, s-a dus biletul.')
          }, 900)
        }}
        onClose={() => setConfirmOpen(false)}
      />
    </>
  )
}
