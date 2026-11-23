import sys
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import database_url, describe_env, public_url  # noqa: E402


class DatabaseUrlTests(unittest.TestCase):
    def test_built_from_parts(self):
        url = database_url({"POSTGRES_USER": "game", "POSTGRES_PASSWORD": "pw",
                            "POSTGRES_DB": "invest"})
        self.assertEqual(url, "postgresql+psycopg2://game:pw@db:5432/invest")

    def test_special_characters_round_trip(self):
        password = "p@ss:w/rd#1%x"
        url = database_url({"POSTGRES_USER": "u", "POSTGRES_PASSWORD": password,
                            "POSTGRES_DB": "d"})
        parts = urlsplit(url)
        self.assertEqual(unquote(parts.password), password)
        self.assertEqual(parts.hostname, "db")
        self.assertEqual(parts.path, "/d")

    def test_windows_line_endings_and_quotes(self):
        url = database_url({"POSTGRES_USER": "u\r", "POSTGRES_PASSWORD": '"pw"\r',
                            "POSTGRES_DB": "d\r"})
        self.assertEqual(url, "postgresql+psycopg2://u:pw@db:5432/d")

    def test_fallback_to_database_url(self):
        url = database_url({"DATABASE_URL": ' "postgresql+psycopg2://a:b@h:1/c"\r'})
        self.assertEqual(url, "postgresql+psycopg2://a:b@h:1/c")

    def test_parts_win_over_database_url(self):
        url = database_url({"POSTGRES_USER": "u", "POSTGRES_PASSWORD": "p", "POSTGRES_DB": "d",
                            "DATABASE_URL": "postgresql://broken"})
        self.assertIn("//u:p@db", url)

    def test_missing_settings_give_clear_error(self):
        for env in ({}, {"DATABASE_URL": ""}, {"POSTGRES_USER": "u"}):
            with self.assertRaises(RuntimeError) as ctx:
                database_url(env)
            self.assertIn(".env", str(ctx.exception))


class DescribeEnvTests(unittest.TestCase):
    def test_never_contains_secret_values(self):
        text = describe_env({"POSTGRES_USER": "game", "POSTGRES_PASSWORD": "s3cret!",
                             "DATABASE_URL": ""})
        self.assertNotIn("s3cret", text)
        self.assertNotIn("game", text.replace("POSTGRES_", ""))
        self.assertIn("POSTGRES_PASSWORD: set (7 characters)", text)
        self.assertIn("POSTGRES_DB: MISSING", text)
        self.assertIn("DATABASE_URL: MISSING", text)


class PublicUrlTests(unittest.TestCase):
    def test_not_set(self):
        self.assertIsNone(public_url({}))
        self.assertIsNone(public_url({"PUBLIC_URL": "  "}))

    def test_normalised(self):
        self.assertEqual(public_url({"PUBLIC_URL": "http://192.168.0.10:8080/"}), "http://192.168.0.10:8080")
        self.assertEqual(public_url({"PUBLIC_URL": '"192.168.137.1:8080"\r'}), "http://192.168.137.1:8080")
        self.assertEqual(public_url({"PUBLIC_URL": "https://game.example.org"}), "https://game.example.org")

    def test_other_schemes_are_ignored(self):
        self.assertIsNone(public_url({"PUBLIC_URL": "javascript://x"}))
        self.assertIsNone(public_url({"PUBLIC_URL": "ftp://host"}))
        self.assertIsNone(public_url({"PUBLIC_URL": "http://"}))


if __name__ == "__main__":
    unittest.main()
