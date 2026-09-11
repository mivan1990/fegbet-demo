import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { Button, EmptyState } from '@/components/ui'

export function NotFound() {
  return (
    <div className="py-12">
      <EmptyState
        icon={Compass}
        title="Pagina asta n-o găsim nicăieri"
        line="Poate a plecat și ea în vacanță. Hai înapoi la meciuri."
        action={
          <Link to="/">
            <Button variant="primary">Acasă</Button>
          </Link>
        }
      />
    </div>
  )
}
