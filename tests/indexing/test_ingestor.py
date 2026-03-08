import pytest
from pathlib import Path
from lib.indexing.ingestor import IngestionWorker, Chunk

@pytest.fixture
def worker():
    return IngestionWorker()

def test_chunk_python(worker, tmp_path):
    code = """
class MyClass:
    def method_a(self):
        return 1

def func_b():
        return 2
"""
    f_path = tmp_path / "test.py"
    f_path.write_text(code)

    chunks = worker.process_file(f_path)
    # ast.walk order is not necessarily top-down lines, but it yields ClassDef and 2 FunctionDefs
    assert len(chunks) == 3
    
    names = {c.extra_meta['node_name'] for c in chunks}
    assert "MyClass" in names
    assert "method_a" in names
    assert "func_b" in names
    
    func_b_chunk = next(c for c in chunks if c.extra_meta['node_name'] == "func_b")
    assert func_b_chunk.start_line == 6
    assert func_b_chunk.end_line == 7
    assert "return 2" in func_b_chunk.content

def test_chunk_markdown_sliding_window(worker, tmp_path):
    md = """Para 1

Para 2

Para 3

Para 4

Para 5"""
    f_path = tmp_path / "test.md"
    f_path.write_text(md)

    # With window_size = 3, stride = max(1, 3//2) = 1
    # Windows: [1,2,3], [2,3,4], [3,4,5], [4,5], [5]
    # For a 5-paragraph document, standard chunking should produce multiple overlapping chunks
    chunks = worker._chunk_markdown(md, "test.md", window_size=3)
    
    assert len(chunks) > 1
    assert "Para 1\n\nPara 2\n\nPara 3" in chunks[0].content
    assert chunks[0].start_line == 1
    # Para 3 is at line 5
    assert chunks[0].end_line == 5

def test_chunk_rust_regex(worker, tmp_path):
    rust_code = """
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

async fn hello() {
    println!("hi");
}
"""
    f_path = tmp_path / "main.rs"
    f_path.write_text(rust_code)
    
    chunks = worker.process_file(f_path)
    assert len(chunks) == 2
    assert chunks[0].chunk_type == "Rust"
    assert chunks[0].extra_meta["node_name"] == "add"
    assert "a + b" in chunks[0].content
    assert chunks[0].start_line == 2
    assert chunks[0].end_line == 4
    
    assert chunks[1].extra_meta["node_name"] == "hello"
    assert "println!" in chunks[1].content
    assert chunks[1].start_line == 6

def test_chunk_lua_regex(worker, tmp_path):
    lua_code = """
local function my_local_func()
    print("local")
end

function global_func()
    print("global")
end
"""
    f_path = tmp_path / "script.lua"
    f_path.write_text(lua_code)
    
    chunks = worker.process_file(f_path)
    assert len(chunks) == 2
    assert chunks[0].chunk_type == "Lua"
    assert chunks[0].extra_meta["node_name"] == "my_local_func"
    assert chunks[1].extra_meta["node_name"] == "global_func"
