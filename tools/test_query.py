import sys
import sqlite3
import sqlite_vec
import struct

sys.path.insert(0, ".")
from lib.ollama_client import embed

conn = sqlite3.connect("data/knowledge.db")
conn.enable_load_extension(True)
sqlite_vec.load(conn)

content = "test text"
vector = embed("embed", content)
vector_bytes = struct.pack(f"<{len(vector)}f", *vector)

# Create mock metadata to test Join
conn.execute("CREATE TABLE IF NOT EXISTS test_meta (rowid INTEGER PRIMARY KEY, cat TEXT)")
conn.execute("INSERT OR IGNORE INTO test_meta (rowid, cat) VALUES (1, 'foo')")

try:
    sql = """
        SELECT m.cat, v.distance 
        FROM vec_chunks v
        JOIN test_meta m ON v.rowid = m.rowid
        WHERE v.embedding MATCH ? AND v.k = ? AND m.cat = ?
    """
    cursor = conn.execute(sql, (vector_bytes, 5, 'foo'))
    print(cursor.fetchall())
except Exception as e:
    print(f"Error: {e}")
