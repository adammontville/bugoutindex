"""
BugOutIndex
Copyright (C) 2025 Your Name or Organization

This program is dual-licensed under the AGPL-3.0 and a commercial license.

You may use, modify, and distribute this software under the terms of the
GNU Affero General Public License v3.0 as published by the Free Software Foundation.

For proprietary or commercial use, please contact: your-email@example.com
"""
import unittest
from processing.normalize import normalize_metric

class TestScoringMethods(unittest.TestCase):
    def test_normalization(self):
        self.assertAlmostEqual(normalize_metric(4, 0, 10), 60.0)
        self.assertAlmostEqual(normalize_metric(0, 0, 10), 100.0)
        self.assertAlmostEqual(normalize_metric(10, 0, 10), 0.0)

