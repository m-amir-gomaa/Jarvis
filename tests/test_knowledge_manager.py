import unittest
import sqlite3
import json
import os
from pathlib import Path
import sys

# Add the project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.knowledge_manager import KnowledgeManager

class TestKnowledgeManager(unittest.TestCase):
    def setUp(self):
        self.test_db = Path("/tmp/test_knowledge.db")
        if self.test_db.exists():
            self.test_db.unlink()
        self.km = KnowledgeManager(db_path=self.test_db)

    def tearDown(self):
        if self.test_db.exists():
            self.test_db.unlink()

    def test_init_db(self):
        # Verify tables exist
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn('chunks', tables)
            self.assertIn('inbox', tables)

        # Verify columns in chunks
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.execute("PRAGMA table_info(chunks)")
            columns = [row[1] for row in cursor.fetchall()]
            self.assertIn('layer', columns)
            self.assertIn('category', columns)
            self.assertIn('source_url', columns)
            self.assertIn('content', columns)
            self.assertIn('type', [row[1] for row in conn.execute("PRAGMA table_info(inbox)").fetchall()])

    def test_add_entry(self):
        self.km.add_entry(layer=1, content="Test content", category="test_cat", source_title="Test Title")
        results = self.km.search("Test content")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['category'], "test_cat")
        self.assertEqual(results[0]['layer'], 1)

    def test_add_to_inbox(self):
        self.km.add_to_inbox(title="Test Inbox", url="http://example.com", reason="Testing", item_type="test_type")
        items = self.km.get_inbox()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], "Test Inbox")
        self.assertEqual(items[0]['type'], "test_type")

    def test_migration(self):
        # Create a legacy DB
        legacy_db = Path("/tmp/legacy_knowledge.db")
        if legacy_db.exists():
            legacy_db.unlink()
        
        with sqlite3.connect(legacy_db) as conn:
            conn.execute("""
                CREATE TABLE knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    layer INTEGER NOT NULL,
                    source_url TEXT,
                    source_title TEXT,
                    content TEXT NOT NULL,
                    embedding BLOB,
                    metadata TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("INSERT INTO knowledge (layer, content) VALUES (1, 'legacy content')")
            conn.execute("""
                CREATE TABLE inbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT,
                    recommendation_reason TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("INSERT INTO inbox (title) VALUES ('legacy inbox')")

        # Initialize KnowledgeManager with legacy DB
        km_migrated = KnowledgeManager(db_path=legacy_db)
        
        # Verify migration
        with sqlite3.connect(legacy_db) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn('chunks', tables)
            self.assertNotIn('knowledge', tables)
            
            # Check data preserved
            content = conn.execute("SELECT content FROM chunks").fetchone()[0]
            self.assertEqual(content, 'legacy content')
            
            # Check type column added to inbox
            cursor = conn.execute("PRAGMA table_info(inbox)")
            columns = [row[1] for row in cursor.fetchall()]
            self.assertIn('type', columns)

        if legacy_db.exists():
            legacy_db.unlink()

if __name__ == '__main__':
    unittest.main()
