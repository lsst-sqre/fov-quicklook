import { useNavigate } from "react-router-dom"

type LinkButtonProps = {
  to: string
  children: React.ReactNode
}

export function LinkButton({ to, children }: LinkButtonProps) {
  const navigate = useNavigate()
  const onClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    navigate(to)
  }

  return (
    <button onClick={onClick}>
      {children}
    </button>
  )
}