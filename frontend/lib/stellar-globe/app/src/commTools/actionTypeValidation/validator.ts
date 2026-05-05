import Ajv, { ValidateFunction } from 'ajv'
import { BaseAction } from '../../app/context'
// @ts-ignore
import schema from './jsonschema.json'


fixJsonSchemaDefinitionName()


const ajv = new Ajv({ allErrors: true })
ajv.addSchema(schema)


export const isBaseAction = (() => {
  const s = ajv.getSchema(`#/properties/BaseAction`)!
  if (s === undefined) {
    throw new Error(`Schema for BaseAction not found`)
  }
  return createIs<BaseAction>(s)
})()


export const isAction = (() => {
  const cache = new Map<string, ValidateFunction>()
  return function isAction(type: string) {
    type = type.replace(/\//g, `$`)
    if (!cache.has(type)) {
      const s = ajv.getSchema(`#/properties/Actions/properties/${type}`)!
      if (s === undefined) {
        throw new Error(`Schema for action ${type} not found`)
      }
      cache.set(type, s)
    }
    return createIs(cache.get(type)!)
  }
})()


export function hasActionValidator(type: string) {
  type = type.replace(/\//g, `$`)
  return ajv.getSchema(`#/properties/Actions/properties/${type}`) !== undefined
}


function createIs<Type = unknown>(validate: ValidateFunction) {
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


function fixJsonSchemaDefinitionName() {
  // @ts-ignore
  const actions = schema.properties.Actions.properties as any
  for (const key of Object.keys(actions)) {
    const value = actions[key]
    delete actions[key]
    actions[key.replace(/\//g, '$')] = value
  }
}
