import unittest
import json
from check_salaries import check_for_non_droppable_player
from app import create_app


class TestTransaction(unittest.TestCase):

    def test_transaction_data(self):
        oracle = "Nick Chubb was dropped\nCalvin Ridley was dropped\nLamar Jackson was dropped\nDavid Johnson was dropped\nDeAndre Hopkins was dropped\n"
        f = open('tests/transactions.json')
        data = json.load(f)
        f.close()

        with(create_app('development').app_context()):
            message = check_for_non_droppable_player(data)
            self.assertEqual(
                message, oracle)


if __name__ == "__main__":
    unittest.main()
