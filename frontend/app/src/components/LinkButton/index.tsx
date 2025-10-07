import { useNavigate } from "react-router-dom"

type LinkButtonProps = {
  to: string
  children: React.ReactNode
  className?: string
}

export function LinkButton({ to, children, className }: LinkButtonProps) {
  const navigate = useNavigate()
  const onClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    navigate(to)
  }

  return (
    <button onClick={onClick} className={className}>
      {children}
    </button>
  )
}