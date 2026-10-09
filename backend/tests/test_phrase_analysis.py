import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.services.vocabulary_service import MAX_TEXT_LENGTH, analyze_vocabulary


class PhraseAnalysisTests(unittest.TestCase):
    def test_normalization_and_no_double_counting(self):
        result = analyze_vocabulary("The red cars passed a red car.")
        phrase = next(item for item in result["phrases"] if item["phrase"] == "red car")
        self.assertEqual(phrase["frequency"], 2)
        self.assertEqual(phrase["forms"], ["red car", "red cars"])
        self.assertEqual(phrase["types"], ["candidate", "noun_chunk"])
        self.assertEqual(phrase["example"], "The red cars passed a red car.")
        self.assertTrue(all(" " not in word["word"] for word in result["words"]))
        self.assertEqual(next(w for w in result["words"] if w["word"] == "car")["frequency"], 2)

    def test_candidates_include_subphrases(self):
        result = analyze_vocabulary("The large red car stopped.")
        phrases = {item["phrase"]: item for item in result["phrases"]}
        self.assertIn("large red car", phrases)
        self.assertIn("red car", phrases)
        self.assertIn("candidate", phrases["red car"]["types"])
        self.assertEqual(result["total_phrases"], sum(p["frequency"] for p in result["phrases"]))
        self.assertEqual(result["unique_phrases"], len(phrases))
        self.assertEqual(result["phrases"], sorted(result["phrases"], key=lambda p: (-p["frequency"], p["phrase"])))

    def test_empty_stop_words_single_words_and_boundaries(self):
        for text in ("", "   ", "the and or", "Cat.", "Cars. Roads.", "Cars, roads."):
            with self.subTest(text=text):
                result = analyze_vocabulary(text)
                self.assertEqual(result["phrases"], [])
                self.assertEqual(result["total_phrases"], 0)
                self.assertEqual(result["unique_phrases"], 0)

    def test_length_limit(self):
        with self.assertRaises(ValueError):
            analyze_vocabulary("x" * (MAX_TEXT_LENGTH + 1))

    def test_api_text_and_uploaded_document(self):
        from io import BytesIO
        from docx import Document

        document = Document()
        document.add_paragraph("The red cars passed a red car.")
        content = BytesIO()
        document.save(content)
        with TestClient(app) as client:
            responses = [
                client.post("/analyze", data={"text": "The red cars passed a red car."}),
                client.post("/analyze", files={"file": ("sample.docx", content.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}),
            ]
        for response in responses:
            self.assertEqual(response.status_code, 200)
            analysis = response.json()["analysis"]
            self.assertIn("words", analysis)
            self.assertEqual(next(p for p in analysis["phrases"] if p["phrase"] == "red car")["frequency"], 2)


if __name__ == "__main__":
    unittest.main()
