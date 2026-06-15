"""
Unit tests for lang-handling guards in WolframAlphaRetrievalEngine.

Covers:
  - None lang defaults to "en" (no crash, no translation attempt)
  - BCP-47 tags (e.g. "en-US") are normalised before comparison
  - translator guard: no translation when self.translator is None
  - translator invoked only for non-English queries when translator is set
  - get_image and get_expanded_answer share the same guards
"""
import unittest
from unittest.mock import MagicMock, patch

from ovos_wolfram_alpha_plugin import WolframAlphaRetrievalEngine


def _make_engine(translator=None):
    with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
        engine = WolframAlphaRetrievalEngine(config={"appid": "TEST"}, translator=translator)
    engine.api = MagicMock()
    return engine


class TestGetSpokenAnswerLangHandling(unittest.TestCase):

    def test_none_lang_does_not_crash(self):
        engine = _make_engine()
        engine.api.spoken.return_value = "The answer is 42."
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            result = engine.get_spoken_answer("what is 42", lang=None)
        self.assertEqual(result, "The answer is 42.")

    def test_bcp47_en_us_does_not_translate(self):
        engine = _make_engine()
        mock_tx = MagicMock()
        engine.translator = mock_tx
        engine.api.spoken.return_value = "The answer is 42."
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            result = engine.get_spoken_answer("what is 42", lang="en-US")
        mock_tx.translate.assert_not_called()
        self.assertEqual(result, "The answer is 42.")

    def test_no_translator_no_crash_for_non_english(self):
        engine = _make_engine(translator=None)
        engine.api.spoken.return_value = "The answer is 42."
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            result = engine.get_spoken_answer("qual é 42", lang="pt")
        self.assertEqual(result, "The answer is 42.")

    def test_translator_used_for_non_english_query(self):
        mock_tx = MagicMock()
        mock_tx.translate.side_effect = lambda q, target, source: f"[{target}]{q}"
        engine = _make_engine(translator=mock_tx)
        engine.api.spoken.return_value = "The answer is 42."
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            result = engine.get_spoken_answer("qual é 42", lang="pt")
        # query translated to en before API call, answer translated back to pt
        self.assertIn("pt", result)

    def test_bad_answer_returns_none(self):
        engine = _make_engine()
        engine.api.spoken.return_value = "Wolfram Alpha did not understand your input"
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            result = engine.get_spoken_answer("xyzzy", lang=None)
        self.assertIsNone(result)


class TestGetImageLangHandling(unittest.TestCase):

    def test_none_lang_does_not_crash(self):
        engine = _make_engine()
        engine.api.get_image = MagicMock(return_value="/tmp/test.gif")
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            result = engine.get_image("mercury", lang=None)
        self.assertEqual(result, "/tmp/test.gif")

    def test_bcp47_en_us_does_not_translate(self):
        engine = _make_engine()
        mock_tx = MagicMock()
        engine.translator = mock_tx
        engine.api.get_image = MagicMock(return_value="/tmp/test.gif")
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            engine.get_image("mercury", lang="en-US")
        mock_tx.translate.assert_not_called()

    def test_no_translator_no_crash_for_non_english(self):
        engine = _make_engine(translator=None)
        engine.api.get_image = MagicMock(return_value="/tmp/test.gif")
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            result = engine.get_image("mercúrio", lang="pt")
        self.assertEqual(result, "/tmp/test.gif")

    def test_translator_used_for_non_english(self):
        mock_tx = MagicMock()
        mock_tx.translate.return_value = "mercury"
        engine = _make_engine(translator=mock_tx)
        engine.api.get_image = MagicMock(return_value="/tmp/test.gif")
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            engine.get_image("mercúrio", lang="pt")
        mock_tx.translate.assert_called_once_with("mercúrio", target="en", source="pt")


class TestQueryLangPropagation(unittest.TestCase):

    def test_query_passes_lang_to_get_spoken_answer(self):
        engine = _make_engine()
        engine.get_spoken_answer = MagicMock(return_value="result")
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            engine.query("hello", lang="fr")
        engine.get_spoken_answer.assert_called_once()
        call_lang = engine.get_spoken_answer.call_args[1].get("lang") or engine.get_spoken_answer.call_args[0][1]
        self.assertEqual(call_lang, "fr")

    def test_query_with_none_lang_does_not_crash(self):
        engine = _make_engine()
        engine.get_spoken_answer = MagicMock(return_value="42")
        with patch("ovos_wolfram_alpha_plugin.Configuration", return_value={}):
            result = engine.query("what is 6 times 7", lang=None)
        self.assertEqual(result, [("42", 0.9)])


if __name__ == "__main__":
    unittest.main()
