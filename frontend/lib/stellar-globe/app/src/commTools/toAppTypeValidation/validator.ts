import Ajv, { ValidateFunction } from 'ajv'
// @ts-ignore
import schema from './jsonschema.json'


const ajv = new Ajv({ allErrors: true })
ajv.addSchema({ ...schema, $id: 'schema' })


export const isValidMessage = (() => {
  const cache = new Map<string, ReturnType<typeof isValidMessage_native>>()
  return (validatorName: string) => {
    if (!cache.has(validatorName)) {
      cache.set(validatorName, isValidMessage_native(validatorName))
    }
    return cache.get(validatorName)!
  }
})()


function isValidMessage_native(validatorName: string) {
  const validate: ValidateFunction = ajv.getSchema(`schema#/properties/${validatorName}`)!

  if (validate === undefined) {
    return undefined
  }

  const is = (
    obj: any,
  ) => {
    const ok = validate(obj)
    if (ok) {
      Object.assign(is, { errors: [] as string[] })
    } else {
      Object.assign(is, { errors: (validate as any).errors as string[] })
    }
    return ok
  }

  return Object.assign(is, { errors: [] as string[] })
}
