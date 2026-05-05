import pytest

from hscmap.jsonpatchapply import apply_patch, copy_for_mutation, path2parts


def test_copy_for_mutation():
    # path に沿ってコピーを作成し、そのコピーを返す
    # 最後に返却されるコピーは、obj と同じ構造を持つが、path に沿ってコピーが作成されている

    original = {
        "name": "John",
        "age": 30,
        "city": "New York",
        "children": [
            {"name": "Alice", "age": 5, "children": [{"name": "Grandchild", "age": 1}]},
            {"name": "Bob", "age": 10},
        ],
    }

    parts = path2parts("/children/0/children/0")
    expected = {
        "name": "John",
        "age": 30,
        "city": "New York",
        "children": [
            {"name": "Alice", "age": 5, "children": [{"name": "Grandchild", "age": 1}]},
            {"name": "Bob", "age": 10},
        ],
    }
    assert copy_for_mutation(original, parts) == expected
    assert copy_for_mutation(original, parts) is not original
    assert copy_for_mutation(original, parts)["children"] is not original["children"]  # type: ignore
    assert copy_for_mutation(original, parts)["children"][0] is not original["children"][0]  # type: ignore
    assert copy_for_mutation(original, parts)["children"][0]["children"][0] is original["children"][0]["children"][0]  # type: ignore
    assert copy_for_mutation(original, parts)["children"][1] is original["children"][1]  # type: ignore


def test_apply_add():
    original = {"name": "John", "age": 30}
    patch = [{"op": "add", "path": "/city", "value": "New York"}]
    expected = {"name": "John", "age": 30, "city": "New York"}
    assert apply_patch(original, patch) == expected


def test_apply_test_on_list_at_end():
    original = {"dict": {"list": [1, 2, 3]}}
    patch = [{"op": "add", "path": "/dict/list/-", "value": 4}]
    expected = {"dict": {"list": [1, 2, 3, 4]}}
    assert apply_patch(original, patch) == expected


def test_apply_test_on_list_at_middle():
    original = {"dict": {"list": [1, 2, 3]}}
    patch = [{"op": "add", "path": "/dict/list/1", "value": 4}]
    expected = {"dict": {"list": [1, 4, 2, 3]}}
    assert apply_patch(original, patch) == expected


def test_apply_remove_on_dict():
    original = {"name": "John", "age": 30, "city": "New York"}
    patch = [{"op": "remove", "path": "/city"}]
    expected = {"name": "John", "age": 30}
    assert apply_patch(original, patch) == expected


def test_apply_remove_on_list():
    original = {"name": "John", "age": 30, "city": "New York", "children": ["Alice", "Bob"]}
    patch = [{"op": "remove", "path": "/children/1"}]
    expected = {"name": "John", "age": 30, "city": "New York", "children": ["Alice"]}
    assert apply_patch(original, patch) == expected


def test_apply_replace_on_dict():
    original = {"name": "John", "age": 30, "city": "New York"}
    patch = [{"op": "replace", "path": "/age", "value": 35}]
    expected = {"name": "John", "age": 35, "city": "New York"}
    assert apply_patch(original, patch) == expected


def test_apply_replace_on_list():
    original = {"name": "John", "age": 30, "city": "New York", "children": ["Alice", "Bob"]}
    patch = [{"op": "replace", "path": "/children/1", "value": "Robert"}]
    expected = {"name": "John", "age": 30, "city": "New York", "children": ["Alice", "Robert"]}
    assert apply_patch(original, patch) == expected


def test_apply_move():
    original = {"name": "John", "age": 30, "city": "New York"}
    patch = [{"op": "move", "from": "/city", "path": "/address"}]
    expected = {"name": "John", "age": 30, "address": "New York"}
    assert apply_patch(original, patch) == expected


def test_apply_move_on_deeply_nested_complex_object():
    original = {
        "name": "John",
        "age": 30,
        "city": "New York",
        "children": [
            {"name": "Alice", "age": 5, "children": [{"name": "Grandchild", "age": 1}]},
            {"name": "Bob", "age": 10, "children": []},
        ],
    }
    patch = [{"op": "move", "from": "/children/0/children/0", "path": "/children/1/children/-"}]
    expected = {
        "name": "John",
        "age": 30,
        "city": "New York",
        "children": [
            {"name": "Alice", "age": 5, "children": []},
            {"name": "Bob", "age": 10, "children": [{"name": "Grandchild", "age": 1}]},
        ],
    }
    assert apply_patch(original, patch) == expected
