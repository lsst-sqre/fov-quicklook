export function assert(ok: any, msg: string | undefined = undefined): asserts ok {
  if (!ok) {
    throw new Error(`Assertion Error${msg ? `: ${msg}` : ''}`)
  }
}
