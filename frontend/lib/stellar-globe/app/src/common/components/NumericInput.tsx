import React, { useEffect, useState } from 'react'


type NumericInputProps = Omit<React.HTMLProps<HTMLInputElement>, 'value' | 'onChange'> & {
  value: number
  onChange: (newValue: number) => void
  transform?: (value: number) => number
}

function NumericInput(props: NumericInputProps) {
  const { value, onChange, transform, ...inputProps } = props
  const [inputValue, setInputValue] = useState(value.toString())


  useEffect(() => {
    setInputValue(value.toString())
  }, [value])

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value)
  }

  const handleBlur = () => {
    validateAndSubmitInput()
  }

  const handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      validateAndSubmitInput()
    }
  }

  const validateAndSubmitInput = () => {
    const numericValue = Number(inputValue)
    if (Number.isFinite(numericValue)) {
      const finalValue = transform ? transform(numericValue) : numericValue
      onChange(finalValue)
    } else {
      setInputValue(value.toString())
    }
  }

  return (
    <input
      {...inputProps}
      type="text"
      value={inputValue}
      onChange={handleChange}
      onBlur={handleBlur}
      onKeyDown={handleKeyPress}
    />
  )
}

export default NumericInput
