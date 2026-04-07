import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ShortcutHelpDialog } from "./ShortcutHelpDialog"
import { HomeShortcutHandlers, homeShortcutDefinitions, useHomeKeyboardShortcuts } from "./keyboardShortcuts"

function ShortcutHarness({ handlers }: { handlers: HomeShortcutHandlers }) {
  useHomeKeyboardShortcuts(handlers)

  return (
    <>
      <input aria-label="Search input" type="text" />
      <textarea aria-label="Notes input" />
      <div contentEditable data-testid="editable-field" />
    </>
  )
}

function createHandlers(): HomeShortcutHandlers {
  return {
    recenter: vi.fn(),
    rotateClockwise: vi.fn(),
    rotateCounterClockwise: vi.fn(),
    toggleLineProfiler: vi.fn(),
    toggleShortcutHelp: vi.fn(),
  }
}

describe("useHomeKeyboardShortcuts", () => {
  it.each([
    ["c", "recenter"],
    ["r", "rotateClockwise"],
    ["R", "rotateCounterClockwise"],
    ["p", "toggleLineProfiler"],
    ["?", "toggleShortcutHelp"],
  ] satisfies Array<[string, keyof HomeShortcutHandlers]>)("handles %s", (keyBinding, shortcutId) => {
    const handlers = createHandlers()

    render(<ShortcutHarness handlers={handlers} />)
    fireEvent.keyDown(window, { key: keyBinding })

    expect(handlers[shortcutId]).toHaveBeenCalledTimes(1)
  })

  it("handles Shift+/ for shortcut help", () => {
    const handlers = createHandlers()

    render(<ShortcutHarness handlers={handlers} />)
    fireEvent.keyDown(window, { key: "/", shiftKey: true })

    expect(handlers.toggleShortcutHelp).toHaveBeenCalledTimes(1)
  })

  it("ignores shortcuts while typing in editable fields", () => {
    const handlers = createHandlers()

    render(<ShortcutHarness handlers={handlers} />)

    fireEvent.keyDown(screen.getByLabelText("Search input"), { key: "c" })
    fireEvent.keyDown(screen.getByLabelText("Notes input"), { key: "p" })
    fireEvent.keyDown(screen.getByTestId("editable-field"), { key: "?" })

    expect(handlers.recenter).not.toHaveBeenCalled()
    expect(handlers.toggleLineProfiler).not.toHaveBeenCalled()
    expect(handlers.toggleShortcutHelp).not.toHaveBeenCalled()
  })

  it("ignores modifier and repeat key presses", () => {
    const handlers = createHandlers()

    render(<ShortcutHarness handlers={handlers} />)

    fireEvent.keyDown(window, { key: "c", ctrlKey: true })
    fireEvent.keyDown(window, { key: "r", metaKey: true })
    fireEvent.keyDown(window, { key: "p", altKey: true })
    fireEvent.keyDown(window, { key: "?", repeat: true })

    expect(handlers.recenter).not.toHaveBeenCalled()
    expect(handlers.rotateClockwise).not.toHaveBeenCalled()
    expect(handlers.toggleLineProfiler).not.toHaveBeenCalled()
    expect(handlers.toggleShortcutHelp).not.toHaveBeenCalled()
  })
})

describe("ShortcutHelpDialog", () => {
  it("renders shortcut help from the shared definitions", () => {
    render(<ShortcutHelpDialog onClose={vi.fn()} open />)

    expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeTruthy()
    for (const definition of Object.values(homeShortcutDefinitions)) {
      expect(screen.getByText(definition.keyBinding)).toBeTruthy()
      expect(screen.getByText(definition.description)).toBeTruthy()
    }
  })
})
