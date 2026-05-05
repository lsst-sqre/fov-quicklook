from hscmap.comm.base import remove_none


def test_remove_none():
    # Test case 1: Dictionary with None values
    input_dict = {'a': 1, 'b': None, 'c': 3, 'd': None}
    expected_output_dict = {'a': 1, 'c': 3}
    assert remove_none(input_dict) == expected_output_dict

    input_list = [1, None, 3, None]
    expected_output_list = [1, None, 3, None]
    assert remove_none(input_list) == expected_output_list

    # Test case 3: Nested dictionary and list with None values
    input_nested = {'a': 1, 'b': None, 'c': [1, None, 3, None], 'd': {'x': 1, 'y': None, 'z': 3, 'w': None}}
    expected_output_nested = {'a': 1, 'c': [1, None, 3, None], 'd': {'x': 1, 'z': 3}}
    assert remove_none(input_nested) == expected_output_nested
