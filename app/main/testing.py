import unittest


def merge_lists(my_list, alices_list):

    # Combine the sorted lists into one large sorted list
    my_list_index = 0
    alice_list_index = 0
    new_list = []

    while my_list_index < len(my_list) and alice_list_index < len(alices_list):
        if my_list[my_list_index] < alices_list[alice_list_index]:
            new_list.append(my_list[my_list_index])
            my_list_index += 1
        else:
            new_list.append(my_list[my_list_index])
            alice_list_index += 1

    if my_list_index < len(my_list):
        new_list += my_list[my_list_index:]
    else:
        new_list += alices_list[alice_list_index:]

    return new_list


# Tests

class Test(unittest.TestCase):

    def test_both_lists_are_empty(self):
        actual = merge_lists([], [])
        expected = []
        self.assertEqual(actual, expected)

    def test_first_list_is_empty(self):
        actual = merge_lists([], [1, 2, 3])
        expected = [1, 2, 3]
        self.assertEqual(actual, expected)

    def test_second_list_is_empty(self):
        actual = merge_lists([5, 6, 7], [])
        expected = [5, 6, 7]
        self.assertEqual(actual, expected)

    def test_both_lists_have_some_numbers(self):
        actual = merge_lists([2, 4, 6], [1, 3, 7])
        expected = [1, 2, 3, 4, 6, 7]
        self.assertEqual(actual, expected)

    def test_lists_are_different_lengths(self):
        actual = merge_lists([2, 4, 6, 8], [1, 7])
        expected = [1, 2, 4, 6, 7, 8]
        self.assertEqual(actual, expected)


unittest.main(verbosity=2)
