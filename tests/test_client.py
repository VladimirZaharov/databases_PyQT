import unittest
import client


class ClientTestCase(unittest.TestCase):

    def setUp(self):
        self.name = 'some_name'
        self.action = 'some_action'

    def test_gen_msg(self):
        msg = client.gen_msg(self.name, self.action)
        self.assertEqual(msg['USER']['ACCOUNT_NAME'], self.name)


if __name__ == '__main__':
    unittest.main()