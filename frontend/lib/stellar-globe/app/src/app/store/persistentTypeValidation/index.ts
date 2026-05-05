import Ajv, { ValidateFunction } from 'ajv'
// @ts-ignore
import schema from './jsonschema.json'


const ajv = new Ajv({ allErrors: true })
ajv.addSchema({ ...schema, $id: 'schema' })


// @ts-ignore
export function createIs<Type>(_validatorName: keyof typeof schema.properties) {
  const validatorName = _validatorName as string
  const validate: ValidateFunction = ajv.getSchema(`schema#/properties/${validatorName}`)!

  if (validate === undefined) {
    throw new Error(`Schema for component ${validatorName} not found`)
  }

  function is(
    obj: any,
  ): obj is Type {
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
