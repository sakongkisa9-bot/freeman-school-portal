import unittest

from teacher_comments import (
    COMMENT_SETS,
    build_subject_comment_indices,
    rating_to_comment,
)


class TeacherCommentTests(unittest.TestCase):
    def test_assigns_unused_comment_sets_before_reuse(self):
        subjects = {"grade": [f"Subject {index}" for index in range(15)]}

        indices = build_subject_comment_indices(subjects)

        self.assertEqual(len(set(indices.values())), 14)
        self.assertEqual(indices["SUBJECT0"], 0)
        self.assertEqual(indices["SUBJECT13"], 13)
        self.assertEqual(indices["SUBJECT14"], 0)

    def test_normalizes_common_cross_grade_subject_names(self):
        subjects = {
            "playgroup": ["LANG", "MATH", "CREAT"],
            "lower": ["ENG", "MAT", "CRE"],
        }

        indices = build_subject_comment_indices(subjects)

        self.assertEqual(indices["ENGLISH"], 0)
        self.assertEqual(indices["MATH"], 1)
        self.assertEqual(indices["CREATIVE"], 2)
        self.assertEqual(len(indices), 3)

    def test_subjects_receive_different_comments(self):
        indices = build_subject_comment_indices({"grade": ["MATH", "ENG"]})

        self.assertNotEqual(
            rating_to_comment("BE1", "MATH", indices),
            rating_to_comment("BE1", "ENG", indices),
        )
        self.assertEqual(rating_to_comment("BE1", "MATH", indices), COMMENT_SETS[0]["BE1"])

    def test_unknown_subject_and_rating_fall_back_safely(self):
        self.assertEqual(rating_to_comment("UNKNOWN", "NEW SUBJECT", {}), "No comment available.")


if __name__ == "__main__":
    unittest.main()
