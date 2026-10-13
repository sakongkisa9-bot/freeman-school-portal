import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import cloud_portal_v2


class NewsletterAttachmentFlowTests(unittest.TestCase):
    def test_uploaded_attachment_opens_inline_and_downloads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "portal.sqlite")
            connection = sqlite3.connect(database_path)
            connection.executescript(
                """
                CREATE TABLE schools (
                    id INTEGER PRIMARY KEY,
                    school_name TEXT,
                    school_code TEXT UNIQUE
                );
                INSERT INTO schools (school_name, school_code)
                VALUES ('Test School', 'test-school');
                CREATE TABLE students (
                    id INTEGER PRIMARY KEY,
                    student_name TEXT,
                    grade TEXT,
                    stream TEXT
                );
                """
            )
            connection.commit()
            connection.close()

            with patch.object(cloud_portal_v2, "PROJECT_DIR", temp_dir), patch.object(
                cloud_portal_v2,
                "get_db",
                side_effect=lambda: sqlite3.connect(database_path, timeout=10),
            ):
                client = cloud_portal_v2.app.test_client()
                response = client.post(
                    "/api/save_newsletter",
                    data={
                        "school_code": "test-school",
                        "newsletter": json.dumps(
                            {
                                "subject": "Attachment test",
                                "body": "Test body",
                                "target_type": "All School",
                                "class_context": "All Classes",
                                "recipient_role": "All Parents",
                                "send_sms": 1,
                            }
                        ),
                        "attachment": (io.BytesIO(b"%PDF-1.4 test file"), "fees.pdf"),
                    },
                    content_type="multipart/form-data",
                )

                self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
                connection = sqlite3.connect(database_path)
                attachment_url = connection.execute(
                    "SELECT attachment_path FROM portal_announcements"
                ).fetchone()[0]
                connection.close()
                self.assertTrue(
                    attachment_url.startswith("/newsletter-attachments/test-school/"),
                    attachment_url,
                )

                inline_response = client.get(attachment_url)
                download_response = client.get(attachment_url + "?download=1")

                self.assertEqual(inline_response.status_code, 200)
                self.assertEqual(download_response.status_code, 200)
                self.assertNotIn(
                    "attachment",
                    inline_response.headers.get("Content-Disposition", "").lower(),
                )
                self.assertIn(
                    "attachment",
                    download_response.headers.get("Content-Disposition", "").lower(),
                )
                self.assertEqual(inline_response.data, b"%PDF-1.4 test file")
                self.assertEqual(download_response.data, inline_response.data)
                inline_response.close()
                download_response.close()


if __name__ == "__main__":
    unittest.main()