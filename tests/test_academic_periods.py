import unittest

from academic_periods import TERMS, available_terms


class AvailableTermsTests(unittest.TestCase):
    def test_current_year_stops_at_configured_term(self):
        self.assertEqual(available_terms("2026", 2026, "Term 1"), TERMS[:1])
        self.assertEqual(available_terms("2026", 2026, "Term 2"), TERMS[:2])
        self.assertEqual(available_terms("2026", 2026, "Term 3"), TERMS)

    def test_past_year_exposes_all_terms(self):
        self.assertEqual(available_terms("2025", 2026, "Term 1"), TERMS)

    def test_unset_year_uses_current_term_limit(self):
        self.assertEqual(available_terms("-", None, "Term 1"), TERMS[:1])

    def test_invalid_current_term_falls_back_to_first_term(self):
        self.assertEqual(available_terms("2026", 2026, "invalid"), TERMS[:1])


if __name__ == "__main__":
    unittest.main()