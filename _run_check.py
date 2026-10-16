import subprocess
import sys

r = subprocess.run(
    [sys.executable, "-m", "unittest", "tests.test_ui_marksheet_kicd", "tests.test_kicd_grading", "tests.test_cbc_cloud_flow"],
    capture_output=True, text=True,
)
out = r.stderr[-2500:]
try:
    import ui_marksheet_primary, ui_marksheet_lower, ui_marksheet_pp1, ui_marksheet_pp2  # noqa
    import ui_marksheet_playgroup, ui_marksheet_junior, marksheet_chooser, grading_four_level  # noqa
    import create_exam_dialog  # noqa
    out += "\nimports ok"
except Exception as error:
    out += f"\nimport failed: {error!r}"
with open("_check_result.txt", "w", encoding="utf8") as handle:
    handle.write(out)
