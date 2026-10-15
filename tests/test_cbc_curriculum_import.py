import unittest

from cbc_curriculum_import import extract_curriculum_tables


class CBCCurriculumImportTests(unittest.TestCase):
    def test_extracts_strands_and_continued_sub_strands(self):
        tables = [
            [
                ["Strands", "Sub Strands", "Suggested Number of Lessons"],
                ["1.0 Conservation of Resources", "1.1 Soil Conservation", "7"],
                [None, "1.2 Water Conservation", "7"],
                ["2.0 Food Production Processes", "2.1 Direct Sowing of Tiny Seeds", "8"],
            ],
            [
                ["Strand", "Sub strand", "Specific learning outcomes"],
                ["Detailed content", "Not a summary sub-strand", "Ignored"],
            ],
        ]
        self.assertEqual(
            extract_curriculum_tables(tables),
            [
                {
                    "name": "1.0 Conservation of Resources",
                    "sub_strands": ["1.1 Soil Conservation", "1.2 Water Conservation"],
                },
                {
                    "name": "2.0 Food Production Processes",
                    "sub_strands": ["2.1 Direct Sowing of Tiny Seeds"],
                },
            ],
        )

    def test_rejects_pdf_tables_without_summary_headers(self):
        with self.assertRaisesRegex(ValueError, "No table"):
            extract_curriculum_tables([["Strand", "Sub strand"], ["Topic", "Item"]])


if __name__ == "__main__":
    unittest.main()