from typing import List


def extractSchema(schema, routes: List[str]):
    # machine translation of devel/generate-js-type-validators.js

    def dig(schema, routes, definitions=None):
        if definitions is None:
            definitions = {}
        definitions = {**schema.get('definitions', {}), **definitions}
        schema = dereference(schema, definitions)

        if len(routes) == 0:
            return schema
        else:
            route, *rest = routes
            nextSchema = schema['properties'][route]
            return dig(nextSchema, rest, definitions)

    def isRef(obj):
        return isinstance(obj, dict) and '$ref' in obj

    def dereference(obj, definitions):
        if isRef(obj):
            ref = obj['$ref']
            assert ref.startswith('#/definitions/')
            return definitions[definitionKey(ref)]
        return obj

    def definitionKey(ref):
        return ref[len('#/definitions/') :]

    def cleanupDefinitions(schema, definitions):
        used_definitions = set()

        def walk(o):
            nonlocal used_definitions
            if isRef(o):
                key = definitionKey(o['$ref'])
                if key not in used_definitions:
                    used_definitions.add(key)
                    walk(definitions[key])
            elif isinstance(o, list):
                for c in o:
                    walk(c)
            elif isinstance(o, dict):
                for k, v in o.items():
                    if k != 'definitions':
                        walk(v)

        walk(schema)
        return {k: definitions[k] for k in used_definitions}

    target = dig(schema, routes)
    newSchema = {**target, 'definitions': cleanupDefinitions(target, schema.get('definitions', {}))}
    return newSchema
