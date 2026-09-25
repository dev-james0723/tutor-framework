import unittest


class PackageSmokeTests(unittest.TestCase):
    def test_package_import_exposes_version(self):
        import tutor_framework

        self.assertEqual(tutor_framework.__version__, "0.1.0")
