export function Footer() {
  return (
    <footer className="border-t border-white/10 py-6">
      <div className="container-app flex flex-col items-center gap-1 text-center text-xs text-white/40">
        <p className="font-display text-sm text-white/60">
          FEG<span className="text-fortuna">BET</span>
        </p>
        <p>Pariuri pe orgoliu, nu pe bani. Fara portofel, fara retrageri.</p>
        <p>Uz intern FEG · {new Date().getFullYear()}</p>
      </div>
    </footer>
  )
}
