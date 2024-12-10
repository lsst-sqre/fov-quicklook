from typing import Any


def return_any(*args, **kwargs):
    return Any


for name in '''
binary
struct
int64
Array
Arrow
DataType
Field
StructScalar
array
dictionary
field
register_extension_type
'''.split():
    globals()[name] = return_any


class ExtensionType:
    def __init__(*args, **kwargs):
        pass


class ExtensionArray:
    def __init__(*args, **kwargs):
        pass


class ExtensionScalar:
    def __init__(*args, **kwargs):
        pass
