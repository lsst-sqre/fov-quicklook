type Options = {
  alert?: boolean
}

export function assert(condition: boolean, message: string = 'Assertion failed', options: Options = {}) {
  if (import.meta.env.DEV) {
    if (!condition) {
      if (options.alert) {
        alert(message)
      }
      console.error(message)
      throw new Error(message)
    }
  }
}
