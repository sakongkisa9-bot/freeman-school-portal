import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from excel_student_import import read_student_rows


class ExcelStudentImportTests(unittest.TestCase):
    def test_reads_knec_headers_and_keeps_assessment_number_as_text(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["KNEC Nominal Roll"])
        worksheet.append(["Assessment Number", "Name of Learner", "Gender", "Stream"])
        worksheet.append(["12345678901", "Amina Wanjiku", "Female", "East"])
        worksheet.append(["12345678902", "Brian Otieno", "Male", "West"])
        worksheet.append([12345, "Carol Njeri", "Female", "North"])
        worksheet[5][0].number_format = "00000000000"

        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "nominal-roll.xlsx"
            workbook.save(file_path)
            records = read_student_rows(file_path)

        self.assertEqual(records[0]["assessment_number"], "12345678901")
        self.assertEqual(records[0]["name"], "Amina Wanjiku")
        self.assertEqual(records[1]["stream"], "West")
        self.assertEqual(records[2]["assessment_number"], "00000012345")

    def test_stream_field_is_absent_when_workbook_has_no_stream_header(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["Assessment Number", "Name", "Gender"])
        worksheet.append(["12345678901", "Amina Wanjiku", "Female"])

        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "nominal-roll.xlsx"
            workbook.save(file_path)
            records = read_student_rows(file_path)

        self.assertNotIn("stream", records[0])


if __name__ == "__main__":
    unittest.main()