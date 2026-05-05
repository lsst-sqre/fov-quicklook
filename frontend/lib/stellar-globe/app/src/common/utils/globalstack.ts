export function makeGlobalStack<Context>() {
  const stack: Context[] = []

  const pushContext = <R>(context: Context, cb: () => R) => {
    stack.push(context)
    try {
      return cb()
    }
    finally {
      stack.pop()
    }
  }

  const current = () => {
    if (stack.length === 0) {
      throw new Error(`Stack is empty`)
    }
    return stack[stack.length - 1]
  }

  return {
    pushContext,
    current,
  }
}
