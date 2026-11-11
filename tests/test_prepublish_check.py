"""Detection patterns of the release hygiene check, including the false positives it must avoid."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import prepublish_check as check  # noqa: E402

BS = "\\"
# Samples are assembled from pieces so that the check does not flag this file itself.
DRIVE, HOME, MAC = "d:/", "/home/", "/Users/"


class PrepublishPatternTests(unittest.TestCase):
    def test_profile_paths_are_found_raw_and_json_escaped(self):
        for text in ("C:" + BS + "Users" + BS + "someone", "C:" + BS * 2 + "Users" + BS * 2 + "someone",
                     DRIVE + "users/someone", HOME + "alice/project", MAC + "bob/project"):
            self.assertTrue(check.PROFILE_PATH.search(text), text)

    def test_json_escapes_urls_and_synthetic_paths_are_not_profile_paths(self):
        for text in ("Note:" + BS + "nUsers", '"a:' + BS + 'u00e9"', "C:/run $(nope)/x",
                     "https://example.org/home/a/", "relative/home/a/"):
            self.assertFalse(check.PROFILE_PATH.search(text), text)

    def test_french_prose_needs_several_function_words(self):
        french = "Voici les notes pour la revue, avec des exemples."
        english = "The pas de deux est is a dance term."
        self.assertGreaterEqual(len({w.lower() for w in check.FRENCH.findall(french)}), 3)
        self.assertLess(len({w.lower() for w in check.FRENCH.findall(english)}), 3)

    def test_only_placeholder_and_noreply_addresses_are_allowed(self):
        self.assertTrue("1+name@users.noreply.github.com".endswith(check.ALLOWED_EMAIL_DOMAINS))
        self.assertFalse(("name" + "@gmail.com").endswith(check.ALLOWED_EMAIL_DOMAINS))


if __name__ == "__main__":
    unittest.main()
