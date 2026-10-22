import unittest

from q35_semantic_regrade import semantic_score


EXPECTED = {
    "case-6103-01": "MX-6130",
    "case-6103-02": "7.625 units",
}


class SemanticRegradeTests(unittest.TestCase):
    def test_json_object_uses_exact_keys_and_values(self):
        result = semantic_score('{"case-6103-01":"MX-6130","case-6103-02":"wrong"}', EXPECTED)
        self.assertEqual(result["method"], "json_object")
        self.assertEqual(result["correct"], 1)

    def test_numbered_requests_map_by_prompt_order(self):
        result = semantic_score("1. MX-6130\n2. 7.625 units", EXPECTED)
        self.assertEqual(result["method"], "numbered_requests_in_prompt_order")
        self.assertEqual(result["correct"], 2)

    def test_final_answers_section_ignores_earlier_revoked_mentions(self):
        raw = "Source says revoked 18.75 units.\n\nFinal Answers:\n1. MX-6130\n2. 7.625 units"
        result = semantic_score(raw, EXPECTED)
        self.assertEqual(result["correct"], 2)

    def test_bold_final_answers_heading_with_colon_is_recognized(self):
        raw = "Earlier text mentions revoked values.\n\n**Final Answers:**\n1. MX-6130\n2. 7.625 units"
        result = semantic_score(raw, EXPECTED)
        self.assertEqual(result["method"], "numbered_requests_in_prompt_order")
        self.assertEqual(result["correct"], 2)

    def test_case_scoped_answer_ignores_revoked_value_in_same_block(self):
        raw = (
            "1. **Case-6103-01**\n   Answer: **MX-6130**\n   Note: REVOKED value NW-7314\n"
            "2. **Case-6103-02**\n   Answer: **7.625 units**\n   Note: REVOKED value 18.75 units"
        )
        result = semantic_score(raw, EXPECTED)
        self.assertEqual(result["method"], "case_scoped_explicit_answer_or_approved_record")
        self.assertEqual(result["correct"], 2)

    def test_case_scoped_approved_record_is_used_not_revoked_record(self):
        raw = (
            "1. **Case-6103-01**\n"
            "Source: case_id=case-6103-01; status=FINAL_APPROVED; value=MX-6130; audit=verified.\n"
            "Note: case_id=case-6103-01; status=REVOKED; value=NW-7314.\n"
            "2. **Case-6103-02**\n"
            "Source: case_id=case-6103-02; status=FINAL_APPROVED; value=7.625 units; audit=verified.\n"
            "Note: case_id=case-6103-02; status=REVOKED; value=18.75 units."
        )
        result = semantic_score(raw, EXPECTED)
        self.assertEqual(result["correct"], 2)

    def test_conflicting_case_answers_are_unresolved(self):
        raw = (
            "1. **Case-6103-01**\nAnswer: MX-6130\nAnswer: NW-7314\n"
            "2. **Case-6103-02**\nAnswer: 7.625 units"
        )
        result = semantic_score(raw, EXPECTED)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["unresolved_case_ids"], ["case-6103-01"])

    def test_unlabelled_value_occurrence_does_not_count(self):
        result = semantic_score("The archive mentions MX-6130 and 7.625 units.", EXPECTED)
        self.assertEqual(result["correct"], 0)
        self.assertEqual(set(result["unanswered_case_ids"]), set(EXPECTED))


if __name__ == "__main__":
    unittest.main()
