import os
import tempfile
import unittest

from debug_console import (
    clear_debug_buffer,
    debug_log,
    get_debug_buffer,
    set_debug_log_file,
)


class DebugConsoleTests(unittest.TestCase):
    def setUp(self):
        clear_debug_buffer()
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        set_debug_log_file(self.tmp.name)

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.remove(self.tmp.name)

    def test_debug_log_writes_to_buffer_and_file(self):
        message = "save marks debug"
        debug_log(message)

        buffer = get_debug_buffer()
        self.assertTrue(any(message in line for line in buffer))

        with open(self.tmp.name, "r", encoding="utf-8") as handle:
            contents = handle.read()
        self.assertIn(message, contents)


if __name__ == "__main__":
    unittest.main()
