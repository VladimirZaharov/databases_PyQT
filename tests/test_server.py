import unittest
import server
from client import gen_msg


class ServerTestCase(unittest.TestCase):

    def test_gen_answer(self):
        msg = gen_msg('some_name', 'presence')
        self.assertEqual(server.gen_answer(msg)['RESPONSE'], 200)


if __name__ == '__main__':
    unittest.main()