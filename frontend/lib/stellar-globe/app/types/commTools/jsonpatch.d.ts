type GetKey = (elem: any) => string | number

type Options = {
  getKey?: GetKey
}

type JsonPatchOp =
  | { op: "add", path: string, value: any }
  | { op: "remove", path: string }
  | { op: "replace", path: string, value: any }
  | { op: "move", path: string, from: string }

export function generateJsonPatch(
  oldObj: unknown,
  newObj: unknown,
  options?: Options
): JsonPatchOp[]
