import { ToApp, validateToAppMessage as validateToAppMessageType } from "../../../types/commTools"
import { isValidMessage } from './validator'


export function validateToAppMessage(type: keyof ToApp, message: any): { errors: string[] } {
  const validate = isValidMessage(type)
  if (validate === undefined) {
    return { errors: [`Validator not found: ${type}`] }
  }
  validate(message)
  const errors = validate.errors ?? [] as string[]
  return { errors }
}

type AssertTypeImplements<T, U extends T> = T
type _TypeCheck1 = AssertTypeImplements<typeof validateToAppMessageType, typeof validateToAppMessage>
