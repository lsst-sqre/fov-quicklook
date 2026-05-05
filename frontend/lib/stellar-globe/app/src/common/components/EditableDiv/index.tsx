import React, { CSSProperties, FocusEvent, FormEvent, useEffect, useRef, useState } from 'react'
import { Icon } from '../Icon'

type Props = {
  value: string
  onChange: (newValue: string) => void
  display?: (value: string) => React.ReactNode
  style?: CSSProperties
}

const EditableDiv: React.FC<Props> = ({ value, onChange, style, display }) => {
  const [isEditing, setEditing] = useState(false)
  const [inputValue, setInputValue] = useState(value)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isEditing])

  const handleSpanClick = () => {
    setEditing(true)
  }

  const handleFormSubmit = (e: FormEvent | FocusEvent) => {
    e.preventDefault()
    onChange(inputValue)
    setEditing(false)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
  }

  if (isEditing) {
    return (
      <form onSubmit={handleFormSubmit}>
        <input
          type="text"
          ref={inputRef}
          value={inputValue}
          onChange={handleInputChange}
          onBlur={handleFormSubmit}
        />
      </form>
    )
  }

  const displayText = display ? display(value) : value

  return (
    <div onClick={handleSpanClick} style={style}>
      {displayText || <Icon type='edit' />}
    </div>
  )
}

export default EditableDiv

export { EditableDiv }
