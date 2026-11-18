"""Startup smoke test: exercise the Streamlit entrypoint, not just helper imports.

The custom handle component's browser JS cannot run in AppTest; only that
browser-facing input is stubbed. All other app modules import normally.
"""

import sys
import types
import unittest
from unittest.mock import patch


class StartupTests(unittest.TestCase):
    def test_streamlit_app_initial_render(self):
        import persistent_handle  # The actual component module must still import.
        from streamlit.testing.v1 import AppTest

        fake = types.ModuleType("persistent_handle")
        fake.persistent_handle_input = lambda label: ""
        with patch.dict(sys.modules, {"persistent_handle": fake}):
            app = AppTest.from_file("app.py", default_timeout=25).run()
        self.assertFalse(
            app.exception,
            "\n".join(str(item.message) for item in app.exception),
        )


if __name__ == "__main__":
    unittest.main()
