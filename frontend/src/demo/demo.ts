/**
 * Modul care exista DOAR in varianta publica de demo.
 *
 * Aplicatia originala nu are asa ceva: acolo fiecare isi face cont cu emailul
 * de serviciu si intra normal. Aici vizitatorul pica direct inauntru, fiindca
 * un ecran de login intr-un demo public e un zid, nu o functionalitate.
 *
 * Autentificarea reala ramane neatinsa dedesubt — JWT, bcrypt, rate limiting,
 * roluri. Doar ca prima cerere de login o face pagina in locul omului.
 *
 * Se aprinde cu VITE_DEMO_MODE=1 la build. Fara variabila, tot codul de aici
 * e inert si aplicatia se comporta exact ca originalul.
 */

export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === '1'

export type DemoRole = 'user' | 'admin'

export interface DemoAccount {
  email: string
  password: string
  label: string
  hint: string
}

/**
 * Parolele stau la vedere intentionat: datele din spate sunt inventate, iar
 * rostul demo-ului e fix sa poti intra si ca admin. Baza se reseteaza oricum
 * din ora in ora, deci nu are ce strica cineva permanent.
 */
export const DEMO_ACCOUNTS: Record<DemoRole, DemoAccount> = {
  user: {
    email: 'test@mariusivan.ro',
    password: 'demo1234',
    label: 'Utilizator',
    hint: 'Pariezi, îți vezi biletele și locul în clasament.',
  },
  admin: {
    email: 'admin@mariusivan.ro',
    password: 'demo1234',
    label: 'Admin',
    hint: 'Validezi meciuri, schimbi punctajele, vezi jurnalul de acțiuni.',
  },
}

// Cand vizitatorul iese explicit din cont, nu-l mai logam automat la loc —
// altfel butonul de logout n-ar avea niciun efect vizibil. Marcajul tine cat
// tine fila deschisa; un refresh de pagina noua il pastreaza, unul de tab nou nu.
const OPT_OUT_KEY = 'fegbet.demo.optedOut'

export function hasOptedOut(): boolean {
  if (!DEMO_MODE) return false
  try {
    return sessionStorage.getItem(OPT_OUT_KEY) === '1'
  } catch {
    return false
  }
}

export function setOptedOut(value: boolean): void {
  if (!DEMO_MODE) return
  try {
    if (value) sessionStorage.setItem(OPT_OUT_KEY, '1')
    else sessionStorage.removeItem(OPT_OUT_KEY)
  } catch {
    /* sessionStorage indisponibil (mod privat) — demo-ul merge si fara */
  }
}
