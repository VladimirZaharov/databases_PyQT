import unittest
import utils


class UtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.config = utils.load_config()

    def test_load_config(self):
        self.assertEqual(self.config['DEFAULT_IP_ADDRESS'], '127.0.0.1')


if __name__ == '__main__':
    unittest.main()