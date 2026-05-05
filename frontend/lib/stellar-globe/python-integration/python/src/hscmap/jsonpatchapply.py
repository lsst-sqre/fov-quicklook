from typing import Any, Dict, List, Union

JsonType = Union[Dict[str, Any], List[Any]]
PatchOperation = Dict[str, Any]


def apply_patch(original: JsonType, patch: List[PatchOperation]) -> JsonType:
    if not isinstance(original, (dict, list)):  # pragma: no cover
        raise ValueError(f"Invalid original object: {original}")

    result = original

    for op in patch:
        try:
            operation = op['op']
            if operation == 'add':
                result = apply_add(result, path2parts(op['path']), op['value'])
            elif operation == 'remove':
                result = apply_remove(result, path2parts(op['path']))
            elif operation == 'replace':
                result = apply_replace(result, path2parts(op['path']), op['value'])
            elif operation == 'move':
                result = apply_move(result, path2parts(op['from']), path2parts(op['path']))
            else:  # pragma: no cover
                raise ValueError(f"Invalid operation: {operation}")
        except Exception as e:  # pragma: no cover
            raise ValueError(f"Failed to apply {op} on {original}") from e

    return result


def copy_for_mutation(obj: JsonType, parts: List[str]) -> JsonType:
    # Create a copy along the path and return the copy.
    # The copy returned at the end has the same structure as obj,
    obj = shallow_copy(obj)
    parent = obj
    for part in parts[:-1]:
        if isinstance(parent, list):
            i = int(part)
            parent[i] = shallow_copy(parent[i])
            parent = parent[i]
        elif isinstance(parent, dict):
            parent[part] = shallow_copy(parent[part])
            parent = parent[part]
        else:  # pragma: no cover
            raise ValueError(f"Invalid object to copy: {repr(parent)}")
    return obj


def shallow_copy(obj: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    if isinstance(obj, list):
        return obj[:]
    elif isinstance(obj, dict):
        return {**obj}
    else:  # pragma: no cover
        raise ValueError(f"Invalid object to copy: {repr(obj)}")


def assign(obj, key: str, value):
    if isinstance(obj, list):
        obj[int(key)] = value
    elif isinstance(obj, dict):
        obj[key] = value
    else:  # pragma: no cover
        raise ValueError()


def navigate(obj: JsonType, parts: List[str]) -> JsonType:
    current = obj
    for part in parts:
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:  # pragma: no cover
            raise ValueError()
    return current


def path2parts(path: str) -> List[str]:
    return path.strip('/').split('/')


def apply_add(obj: JsonType, parts: List[str], value: Any) -> JsonType:
    obj = copy_for_mutation(obj, parts)
    parent = navigate(obj, parts[:-1])
    key = parts[-1]
    if isinstance(parent, list):
        if key == '-':
            parent.append(value)
        else:
            index = int(key)
            if index > len(parent):  # pragma: no cover
                raise ValueError(f'{repr(obj)}[{repr(parts[:-1])}] == {repr(parent)}, but index {index} is out of range')
            else:
                parent.insert(index, value)
    elif isinstance(parent, dict):
        if key in parent:  # pragma: no cover
            raise ValueError(f'{repr(obj)}[{repr(parts[:-1])}] == {repr(parent)}, but key {key} already exists')
        parent[key] = value
    else:  # pragma: no cover
        raise ValueError(f'{repr(obj)}[{repr(parts)}] = {repr(value)}')
    return obj


def apply_remove(obj: JsonType, parts: List[str]) -> JsonType:
    obj = copy_for_mutation(obj, parts)
    parent = navigate(obj, parts[:-1])
    key = parts[-1]
    if isinstance(parent, list):
        del parent[int(key)]
    elif isinstance(parent, dict):
        del parent[key]
    else:  # pragma: no cover
        raise ValueError()
    return obj


def apply_replace(obj, parts: List[str], value):
    obj = copy_for_mutation(obj, parts)
    parent = navigate(obj, parts[:-1])
    assign(parent, parts[-1], value)
    return obj


def apply_move(obj: JsonType, from_parts: List[str], to_parts: List[str]) -> JsonType:
    value = extract_value(obj, from_parts)
    obj = apply_remove(obj, from_parts)
    obj = apply_add(obj, to_parts, value)
    return obj


def extract_value(obj, parts: List[str]):
    parent = navigate(obj, parts[:-1])
    key = parts[-1]
    if isinstance(parent, list):
        return parent[int(key)]
    elif isinstance(parent, dict):
        return parent[key]
    else:  # pragma: no cover
        raise ValueError()
