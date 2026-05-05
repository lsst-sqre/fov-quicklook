import type { validateAction as validateActionType } from '../../../types/commTools/index.js'
import { isBaseAction, isAction, hasActionValidator } from './validator.js'


export function validateAction(action: any) {
  const errors: string[] = []
  do {
    if (isBaseAction(action)) {
      if (hasActionValidator(action.type)) {
        const isValidAction = isAction(action.type)
        if (isValidAction(action)) {
          break
        }
        else {
          errors.push(...isValidAction.errors)
        }
      }
      else {
        errors.push(`No validator for action type ${action.type}`)
      }
    }
    else {
      errors.push(...isBaseAction.errors)
    }
  } while
    // eslint-disable-next-line no-constant-condition
    (false)
  return { errors }
}


type AssertTypeImplements<T, U extends T> = T
type _TypeCheck1 = AssertTypeImplements<typeof validateActionType, typeof validateAction>
