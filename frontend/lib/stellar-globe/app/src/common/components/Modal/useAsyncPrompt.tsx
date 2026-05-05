import { KeyboardEvent, RefObject, useCallback, useEffect, useRef, useState } from "react"
import { useModal } from "."
import styles from './styles.module.scss'


export function useAsyncPrompt() {
  const { addLayer } = useModal()

  const asyncPromp = useCallback((message?: string, defaultText?: string) => {
    return new Promise<string | null>(resolve => {
      const onSubmit = (value: string | null) => {
        clear()
        resolve(value)
      }
      const clear = addLayer(
        <Prompt message={message} defaultText={defaultText} onSubmit={onSubmit} />
      )
    })
  }, [addLayer])

  return asyncPromp
}


type PromptProps = {
  message?: string
  defaultText?: string
  onSubmit: (value: string | null) => void
}


function Prompt({
  message, defaultText, onSubmit,
}: PromptProps) {
  const [text, setText] = useState(defaultText ?? '')
  const inputEl = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputEl.current?.select()
  }, [])

  const { blockRef } = useModal()
  useSetupModalFocusTrap(blockRef)

  const onKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      onSubmit(null)
    }
  }, [onSubmit])

  return (
    <div className={styles.prompt} tabIndex={-1} onKeyDown={onKeyDown} >
      {message && (
        <div className={styles.message}>{message}</div>
      )}
      <form onSubmit={e => {
        e.preventDefault()
        onSubmit(text)
      }}>
        <input ref={inputEl} type="text" value={text} onChange={e => setText(e.currentTarget.value)} />
      </form>
      <div className={styles.promptButtons}>
        <button onClick={() => { onSubmit(null) }}>Cancel</button>
        <button onClick={() => onSubmit(text)} >OK</button>
      </div>
    </div>
  )
}


function useSetupModalFocusTrap(containerRef: RefObject<HTMLElement>, rootElementRef?: RefObject<HTMLElement>) {
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    const firstFocusableElement = container.querySelectorAll(focusableElements)[0] as HTMLElement
    const focusableContent = container.querySelectorAll(focusableElements)
    const lastFocusableElement = focusableContent[focusableContent.length - 1] as HTMLElement

    const handleKeyDown = (e: KeyboardEvent) => {
      const isTabPressed = e.key === 'Tab'
      if (!isTabPressed) {
        return
      }
      if (e.shiftKey) { // shift + tab
        if (document.activeElement === firstFocusableElement) {
          lastFocusableElement.focus()
          e.preventDefault()
        }
      } else { // tab
        if (document.activeElement === lastFocusableElement) {
          firstFocusableElement.focus()
          e.preventDefault()
        }
      }
    }

    const handleFocusIn = (e: FocusEvent) => {
      if (!container.contains(e.target as Node)) {
        firstFocusableElement.focus()
      }
    }

    const target = (rootElementRef?.current ?? document) as HTMLElement

    target.addEventListener('keydown', handleKeyDown as () => void)
    target.addEventListener('focusin', handleFocusIn)

    return () => {
      target.removeEventListener('keydown', handleKeyDown as () => void)
      target.removeEventListener('focusin', handleFocusIn)
    }
  }, [containerRef, rootElementRef])
}
