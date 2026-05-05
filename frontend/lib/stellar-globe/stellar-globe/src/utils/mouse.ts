export enum Button {
  LEFT = 0,
  MIDDLE = 1,
  RIGHT = 2,
}

function button(e: MouseEvent) {
  switch (e.button) {
    case 2:
      return Button.RIGHT
    case 1:
      return Button.MIDDLE
    default: {
      if (!e.altKey && e.ctrlKey && !e.shiftKey) {
        return Button.RIGHT
      }
      if (e.altKey && !e.ctrlKey && !e.shiftKey) {
        return Button.MIDDLE
      }
    }
  }
  return Button.LEFT
}

export const mouse = {
  button,
  Button,
}
