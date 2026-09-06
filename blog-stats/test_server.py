import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


class StatisticsRenameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        os.environ["BLOG_STATS_DATABASE"] = str(root / "stats.sqlite3")
        os.environ["BLOG_STATS_SECRET_FILE"] = str(root / "cookie-secret")
        os.environ["BLOG_POSTS_DIRECTORY"] = str(root / "posts")
        spec = importlib.util.spec_from_file_location("stats_server_for_test", Path(__file__).with_name("server.py"))
        cls.server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.server)
        cls.server.initialize_database()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        with self.server.connect_database() as connection:
            connection.execute("DELETE FROM post_views")
            connection.execute("DELETE FROM post_likes")
            connection.execute("DELETE FROM post_redirects")

    def test_rename_preserves_counts_and_creates_redirect(self):
        with self.server.connect_database() as connection:
            connection.execute("INSERT INTO post_views(post_slug, visitor_id) VALUES ('old-slug', 'visitor')")
            connection.execute("INSERT INTO post_likes(post_slug, visitor_id) VALUES ('old-slug', 'visitor')")
        self.server.rename_post("old-slug", "new-slug")
        stats = self.server.get_all_stats()
        self.assertEqual(stats["new-slug"], {"views": 1, "likes": 1})
        self.assertEqual(self.server.redirect_for("old-slug"), "new-slug")

    def test_rollback_removes_forward_redirect(self):
        self.server.rename_post("old-slug", "new-slug")
        self.server.rename_post("new-slug", "old-slug", rollback=True)
        self.assertIsNone(self.server.redirect_for("old-slug"))


if __name__ == "__main__":
    unittest.main()
