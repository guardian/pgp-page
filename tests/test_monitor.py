import unittest

from src.monitor import *


class TestMonitor(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def test_get_stage(self):
        filename = os.path.join(os.path.dirname(__file__), 'stage')
        self.assertEqual('DEV', get_stage('none'))
        self.assertEqual('CODE', get_stage(filename))

    def test_get_expiry(self):
        self.assertEqual(1571306400, get_expiry(1570701600))

    def test_create_item(self):
        expected = {
            'CheckTime': 1570701600,
            'ExpirationTime': 1571306400,
            'Outcome': 'True'
        }
        self.assertEqual(expected, create_item(1570701600, True))


if __name__ == '__main__':
    unittest.main()
