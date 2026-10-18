import json
import os
import tempfile
import unittest
from unittest.mock import patch

import cloud_service


class CloudServiceCredentialTests(unittest.TestCase):
    def test_saved_credentials_are_used_without_prompts(self):
        config = {
            "cloud_school_code": "school-1",
            "cloud_teacher_username": "teacher-1",
            "cloud_teacher_password": "secret",
        }
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, "school_config.json")
            with open(config_path, "w", encoding="utf-8") as config_file:
                json.dump(config, config_file)

            with patch.object(cloud_service, "CONFIG_PATH", config_path), patch.object(
                cloud_service, "askstring"
            ) as askstring:
                credentials = cloud_service.ask_cloud_credentials()

        self.assertEqual(
            credentials,
            {
                "school_code": "school-1",
                "username": "teacher-1",
                "password": "secret",
            },
        )
        askstring.assert_not_called()


if __name__ == "__main__":
    unittest.main()