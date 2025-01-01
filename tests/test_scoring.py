import unittest
from processing.normalize import normalize_metric

class TestScoringMethods(unittest.TestCase):
    def test_normalization(self):
        self.assertAlmostEqual(normalize_metric(4, 0, 10), 60.0)
        self.assertAlmostEqual(normalize_metric(0, 0, 10), 100.0)
        self.assertAlmostEqual(normalize_metric(10, 0, 10), 0.0)

