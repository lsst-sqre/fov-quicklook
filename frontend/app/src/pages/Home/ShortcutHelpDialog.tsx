import styles from "./styles.module.scss"
import { homeShortcutDefinitions } from "./keyboardShortcuts"

const homeShortcutEntries = Object.entries(homeShortcutDefinitions)

export function ShortcutHelpDialog({ open, onClose }: { open: boolean, onClose: () => void }) {
  if (!open) {
    return null
  }

  return (
    <div className={styles.shortcutHelpBackdrop} onClick={onClose}>
      <div
        aria-labelledby="keyboard-shortcuts-title"
        className={styles.shortcutHelpDialog}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className={styles.shortcutHelpHeader}>
          <h2 className={styles.shortcutHelpTitle} id="keyboard-shortcuts-title">Keyboard shortcuts</h2>
          <button className={styles.shortcutHelpCloseButton} onClick={onClose} type="button">Close</button>
        </div>
        <ul className={styles.shortcutHelpList}>
          {homeShortcutEntries.map(([shortcutId, definition]) => (
            <li className={styles.shortcutHelpItem} key={shortcutId}>
              <kbd className={styles.shortcutHelpKey}>{definition.keyBinding}</kbd>
              <span>{definition.description}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
