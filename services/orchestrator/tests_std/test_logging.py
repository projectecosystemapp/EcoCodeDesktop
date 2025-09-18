import logging
import unittest


class TestLogging(unittest.TestCase):
    def test_configure_logging_sets_level(self):
        # Defer import to avoid side effects and ensure package is importable from source
        from eco_api.logging import configure_logging

        # Reset root logger handlers to ensure basicConfig applies
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        configure_logging(level=logging.DEBUG)
        root = logging.getLogger()
        self.assertEqual(root.level, logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
