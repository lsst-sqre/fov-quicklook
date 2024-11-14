import { Link } from "react-router-dom"

type LinkButtonProps = {
  to: string
  children: React.ReactNode
}

export function LinkButton({ to, children }: LinkButtonProps) {
  return (
    <button>
      <Link to={to}>
        {children}
      </Link>
    </button>
  )
}