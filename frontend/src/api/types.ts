export interface AuthUser {
  id: number
  email: string
  display_name: string
  points: number
  is_admin: boolean
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  user: AuthUser
}

// -------------------------------------------------------------------------- teams
export interface Team {
  id: number
  name: string
  short_name: string | null
  logo_url: string | null
  is_feg: boolean
  is_active: boolean
}

export interface TeamAdmin extends Team {
  player_count: number
  match_count: number
}

export interface TeamInput {
  name: string
  short_name?: string | null
  logo_url?: string | null
  is_feg?: boolean
  is_active?: boolean
}

// ------------------------------------------------------------------------ players
export type PlayerPosition = 'GK' | 'DEF' | 'MID' | 'ATT'

export interface Player {
  id: number
  team_id: number
  name: string
  shirt_number: number | null
  position: PlayerPosition | null
  is_active: boolean
}

export interface PlayerInput {
  name: string
  shirt_number?: number | null
  position?: PlayerPosition | null
  is_active?: boolean
}

// ------------------------------------------------------------------------ matches
export type MatchStatus = 'SCHEDULED' | 'LIVE' | 'FINISHED' | 'CANCELLED'

export interface TeamRef {
  id: number
  name: string
  short_name: string | null
  is_feg: boolean
}

export interface Scorer {
  player_id: number
  name: string
  goals: number
}

export interface MyTicketSummary {
  ticket_id: number
  selection_count: number
  potential_points: number
  status: TicketStatus
  total_points: number | null
}

export type MatchPhase = 'GROUP' | 'KNOCKOUT'

export interface Match {
  id: number
  round_no: number
  bracket_position: number
  stage_label: string | null
  status: MatchStatus
  scheduled_at: string | null

  // Faza 9: faza meciului (grupe / eliminatoriu) si grupa lui, daca e cazul.
  phase: MatchPhase
  group_id: number | null
  group_name: string | null

  home_team: TeamRef | null
  away_team: TeamRef | null
  home_score: number | null
  away_score: number | null
  penalties_home: number | null
  penalties_away: number | null
  winner_team_id: number | null
  is_settled: boolean
  next_match_id: number | null
  next_slot: 'home' | 'away' | null
  is_locked: boolean
  is_bettable: boolean
  has_feg: boolean
  my_ticket: MyTicketSummary | null
}

export interface MatchDetail extends Match {
  scorers: Scorer[]
}

export interface BracketRound {
  round_no: number
  stage_label: string | null
  matches: Match[]
}

export interface AdminStats {
  users: number
  teams: number
  players: number
  matches: number
  matches_settled: number
  tickets: number
  top_market: string | null
}

// ------------------------------------------------------------------------ tickets
export type TicketStatus = 'OPEN' | 'SETTLED' | 'VOID'
export type MarketCode = 'WINNER' | 'QUALIFY' | 'TOTAL_GOALS' | 'BTTS' | 'SCORER'

export interface SelectionInput {
  market: MarketCode
  pick: string
  line?: number | null
  player_id?: number | null
}

export interface SelectionOut {
  market: MarketCode
  pick: string
  line: number | null
  player_id: number | null
  player_name: string | null
  points: number
  is_correct: boolean | null
  points_awarded: number | null
}

export interface TicketMatchRef {
  id: number
  stage_label: string | null
  scheduled_at: string | null
  status: MatchStatus
  is_settled: boolean
  is_locked: boolean
  home_name: string | null
  away_name: string | null
  home_score: number | null
  away_score: number | null
}

export interface Ticket {
  id: number
  match_id: number
  status: TicketStatus
  selections: SelectionOut[]
  potential_points: number
  total_points: number | null
  created_at: string
  updated_at: string
  match: TicketMatchRef | null
}

export type PointsMap = Record<string, number>

// -------------------------------------------------------------------------- grupe
export interface StandingRow {
  team_id: number
  team: TeamRef
  played: number
  won: number
  drawn: number
  lost: number
  goals_for: number
  goals_against: number
  goal_diff: number
  points: number
  rank: number
  tied_with: number[]
}

export type GroupPredictionStatus = 'OPEN' | 'SETTLED' | 'VOID'

export interface GroupPick {
  team_id: number
  team_name: string
  is_correct: boolean | null
  points_awarded: number | null
}

export interface GroupPrediction {
  id: number
  group_id: number
  status: GroupPredictionStatus
  total_points: number | null
  picks: GroupPick[]
  potential_points: number
  created_at: string
  updated_at: string
}

export interface Group {
  id: number
  name: string
  sort_order: number
  qualifiers_count: number
  teams: TeamRef[]
  standings: StandingRow[]
  matches: Match[]
  is_complete: boolean
  is_finalized: boolean
  is_locked: boolean
  // Exact ce intoarce `services.groups.group_lock_reason` (backend) — None cand
  // grupa e deschisa. Gandit pentru un raspuns de eroare la o actiune ("nu mai
  // poti SCHIMBA pronosticul").
  lock_reason: string | null
  // Formulare separata pentru empty state-ul unui user FARA pronostic deloc
  // ("nu mai poti PUNE pronostic") — vezi GroupCard.tsx.
  missed_prediction_reason: string | null
  locks_at: string | null
  qualified: TeamRef[]
  my_prediction: GroupPrediction | null
}

// -------------------------------------------------------------------- leaderboard
export interface LeaderboardRow {
  rank: number
  display_name: string
  points: number
  tickets: number
  settled_tickets: number
  won_tickets: number
  correct_selections: number
  total_selections: number
  // Faza 9: punctele din pronosticuri de grupa, separat de bilete.
  group_points: number
  correct_qualifiers: number
  total_qualifiers: number
}

// ------------------------------------------------------------------- admin: users
export interface AdminUser {
  id: number
  email: string
  display_name: string
  points: number
  is_admin: boolean
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

// -------------------------------------------------------------------- admin: logs
export interface LogItem {
  id: number
  action: string
  actor_user_id: number | null
  actor_name: string | null
  target_user_id: number | null
  entity_type: string | null
  entity_id: number | null
  detail: unknown
  ip_address: string | null
  created_at: string
}

export interface LogPage {
  items: LogItem[]
  total: number
  page: number
  pages: number
  actions: string[]
}

export interface LogFilters {
  user_id?: number | null
  action?: string | null
  from?: string | null
  to?: string | null
  q?: string | null
  page?: number
}
