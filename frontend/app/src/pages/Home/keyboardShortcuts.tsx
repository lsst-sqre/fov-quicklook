import { useEffect } from "react"

type HomeShortcutDefinition = {
  keyBinding: string
  description: string
}

export const homeShortcutDefinitions = {
  recenter: {
    keyBinding: "c",
    description: "Re-center",
  },
  rotateClockwise: {
    keyBinding: "r",
    description: "Rotate 90 degrees",
  },
  rotateCounterClockwise: {
    keyBinding: "R",
    description: "Rotate -90 degrees",
  },
  toggleLineProfiler: {
    keyBinding: "p",
    description: "Toggle line profiler",
  },
  toggleShortcutHelp: {
    keyBinding: "?",
    description: "Show keyboard shortcuts",
  },
} satisfies Record<string, HomeShortcutDefinition>

export type HomeShortcutId = keyof typeof homeShortcutDefinitions
export type HomeShortcutHandlers = Record<HomeShortcutId, () => void>

const homeShortcutEntries = Object.entries(homeShortcutDefinitions) as Array<[HomeShortcutId, HomeShortcutDefinition]>
const nonTextInputTypes = new Set(["button", "checkbox", "color", "file", "hidden", "image", "radio", "range", "reset", "submit"])

export function useHomeKeyboardShortcuts(handlers: HomeShortcutHandlers) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey || event.repeat) {
        return
      }
      if (isTextEntryTarget(event.target)) {
        return
      }
      const shortcutId = findHomeShortcutId(event.key)
      if (!shortcutId) {
        return
      }
      event.preventDefault()
      handlers[shortcutId]()
    }

    window.addEventListener("keydown", onKeyDown)
    return () => {
      window.removeEventListener("keydown", onKeyDown)
    }
  }, [handlers])
}

function findHomeShortcutId(keyBinding: string): HomeShortcutId | undefined {
  const matchedShortcut = homeShortcutEntries.find(([, definition]) => definition.keyBinding === keyBinding)
  return matchedShortcut?.[0]
}

export function isTextEntryTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false
  }

  const editableElement = target.closest("input, textarea, [contenteditable]")
  if (!editableElement) {
    return false
  }
  if (editableElement instanceof HTMLTextAreaElement) {
    return true
  }
  if (editableElement instanceof HTMLInputElement) {
    return !nonTextInputTypes.has(editableElement.type)
  }
  return editableElement instanceof HTMLElement
    && (editableElement.isContentEditable || editableElement.getAttribute("contenteditable") !== "false")
}
