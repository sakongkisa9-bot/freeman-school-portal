import importlib.machinery
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from file_loader import CustomImportHook, sync_updated_files


PROJECT_DIR = Path(__file__).parents[1]


class UserModuleOverrideTests(unittest.TestCase):
    def test_rejects_teacher_view_without_stream_support(self):
        with tempfile.TemporaryDirectory() as directory:
            override = Path(directory) / "teachers_linked.py"
            override.write_text(
                "class TeachersLinkedView:\n"
                "    def __init__(self, parent, db, class_name, return_callback):\n"
                "        pass\n",
                encoding="utf-8",
            )
            hook = CustomImportHook(directory, str(PROJECT_DIR))

            self.assertIsNone(hook.find_spec("teachers_linked", None))
            bundled_spec = importlib.machinery.PathFinder.find_spec(
                "teachers_linked", [str(PROJECT_DIR)]
            )
            self.assertIsNotNone(bundled_spec)

    def test_rejects_cloud_service_missing_current_endpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            override = Path(directory) / "cloud_service.py"
            override.write_text(
                "class CloudService:\n"
                "    def upload_marks(self, *args):\n"
                "        pass\n",
                encoding="utf-8",
            )

            error = CustomImportHook._validate_override("cloud_service", str(override))

            self.assertIn("CloudService.create_exam", error)
            self.assertIn("CloudService.upload_cba_tasks", error)

    def test_accepts_current_teacher_view_override(self):
        error = CustomImportHook._validate_override(
            "teachers_linked", str(PROJECT_DIR / "teachers_linked.py")
        )

        self.assertIsNone(error)

    def test_rejects_legacy_wizard_override(self):
        with tempfile.TemporaryDirectory() as directory:
            override = Path(directory) / "wizard.py"
            override.write_text(
                "class SchoolSetupWizard:\n"
                "    pass\n",
                encoding="utf-8",
            )

            error = CustomImportHook._validate_override("wizard", str(override))

            self.assertIn("compatible setup wizard API version", error)

    def test_accepts_current_wizard_override(self):
        error = CustomImportHook._validate_override("wizard", str(PROJECT_DIR / "wizard.py"))

        self.assertIsNone(error)

    def test_sync_removes_user_directory_from_import_search_path(self):
        with tempfile.TemporaryDirectory() as user_directory:
            bundled_directory = str(PROJECT_DIR)
            original_path = list(sys.path)
            try:
                sys.path.insert(0, user_directory)
                with (
                    patch.object(sys, "frozen", True, create=True),
                    patch(
                        "file_loader.get_app_directories",
                        return_value=(bundled_directory, user_directory),
                    ),
                    patch("file_loader.install_custom_import_hook"),
                ):
                    sync_updated_files()

                self.assertNotIn(user_directory, sys.path)
            finally:
                sys.path[:] = original_path


if __name__ == "__main__":
    unittest.main()