import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import ods


class ConfigStatusTests(unittest.TestCase):
    def check_status(self, status):
        config = json.loads((Path(__file__).resolve().parent.parent / 'onlytools.config.json').read_text(encoding='utf-8'))
        config['product']['status'] = status
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'onlytools.config.json'
            path.write_text(json.dumps(config), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                return ods.config(path)

    def test_schema_statuses_pass(self):
        for status in ['active', 'beta', 'development', 'archived']:
            with self.subTest(status=status):
                self.assertEqual(0, self.check_status(status))

    def test_nonempty_status_outside_schema_is_rejected(self):
        self.assertEqual(1, self.check_status('early-development'))


if __name__ == '__main__':
    unittest.main()
