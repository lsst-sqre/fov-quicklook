import { KeyboardEvent, useEffect, useId, useMemo, useState } from "react"

type ComboboxProps = {
  value: string
  options: string[]
  truncated: boolean
  placeholder?: string
  onChange: (value: string) => void
}

export function Combobox({ value, options, truncated, placeholder, onChange }: ComboboxProps) {
  const listboxId = useId()
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const hasSelectableOptions = options.length > 0

  const optionIds = useMemo(
    () => options.map((_, index) => `${listboxId}-option-${index}`),
    [listboxId, options],
  )

  useEffect(() => {
    if (!isOpen) {
      setActiveIndex(-1)
      return
    }
    setActiveIndex(hasSelectableOptions ? 0 : -1)
  }, [hasSelectableOptions, isOpen, value])

  const selectOption = (nextValue: string) => {
    onChange(nextValue)
    setIsOpen(false)
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault()
      setIsOpen(true)
      if (!hasSelectableOptions) {
        return
      }
      setActiveIndex((current) => (current + 1 + options.length) % options.length)
      return
    }
    if (event.key === "ArrowUp") {
      event.preventDefault()
      setIsOpen(true)
      if (!hasSelectableOptions) {
        return
      }
      setActiveIndex((current) => (current <= 0 ? options.length - 1 : current - 1))
      return
    }
    if (event.key === "Enter" && isOpen && activeIndex >= 0) {
      event.preventDefault()
      selectOption(options[activeIndex])
      return
    }
    if (event.key === "Escape") {
      setIsOpen(false)
    }
  }

  return (
    <div style={containerStyle}>
      <input
        aria-activedescendant={activeIndex >= 0 ? optionIds[activeIndex] : undefined}
        aria-autocomplete="list"
        aria-controls={listboxId}
        aria-expanded={isOpen}
        role="combobox"
        spellCheck={false}
        style={inputStyle}
        type="text"
        value={value}
        onBlur={() => setIsOpen(false)}
        onChange={(event) => {
          onChange(event.target.value)
          setIsOpen(true)
        }}
        onFocus={() => setIsOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
      />
      {isOpen && (hasSelectableOptions || truncated) && (
        <div id={listboxId} role="listbox" style={listboxStyle}>
          {options.map((option, index) => {
            const active = index === activeIndex
            return (
              <div
                aria-selected={active}
                id={optionIds[index]}
                key={option}
                role="option"
                style={{
                  ...optionStyle,
                  ...(active ? activeOptionStyle : {}),
                }}
                onMouseDown={(event) => {
                  event.preventDefault()
                  selectOption(option)
                }}
                onMouseEnter={() => setActiveIndex(index)}
              >
                {option}
              </div>
            )
          })}
          {truncated && <div aria-hidden="true" style={ellipsisStyle}>...</div>}
        </div>
      )}
    </div>
  )
}

const containerStyle = {
  position: "relative",
  width: "100%",
} as const

const listboxStyle = {
  position: "absolute",
  zIndex: 20,
  top: "calc(100% + 4px)",
  left: 0,
  minWidth: "max(100%, 24rem)",
  width: "max-content",
  maxWidth: "min(90vw, 64rem)",
  maxHeight: "18rem",
  overflowY: "auto",
  border: "1px solid rgba(255, 255, 255, 0.15)",
  borderRadius: "8px",
  backgroundColor: "rgba(31, 31, 31, 0.94)",
  color: "rgba(255, 255, 255, 0.92)",
  boxShadow: "0 20px 40px rgba(0, 0, 0, 0.4)",
  backdropFilter: "blur(6px)",
} as const

const inputStyle = {
  width: "100%",
  boxSizing: "border-box",
  minHeight: "38px",
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(255, 255, 255, 0.15)",
  backgroundColor: "rgba(255, 255, 255, 0.05)",
  color: "inherit",
} as const

const optionStyle = {
  padding: "8px 12px",
  cursor: "pointer",
  whiteSpace: "nowrap",
} as const

const activeOptionStyle = {
  backgroundColor: "rgba(255, 255, 255, 0.16)",
} as const

const ellipsisStyle = {
  padding: "8px 12px",
  color: "rgba(255, 255, 255, 0.6)",
  whiteSpace: "nowrap",
} as const
