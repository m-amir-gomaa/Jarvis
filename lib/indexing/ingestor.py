import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Generator

@dataclass
class Chunk:
    chunk_id: str
    source_path: str
    chunk_type: str  # "Python", "Markdown", "Rust", "Lua"
    content: str
    start_line: int
    end_line: int
    extra_meta: dict = field(default_factory=dict)

class IngestionWorker:
    """
    Parses and chunks files intelligently based on their extensions.
    - Python: AST-based class/function extraction
    - Markdown: Sliding window paragraph chunker
    - Rust/Lua: RegEx-based boundary chunker
    """
    
    def process_file(self, file_path: Path) -> List[Chunk]:
        """Reads file and routes to language specific chunker."""
        if not file_path.exists():
            return []
            
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            # Skip non-utf8 unreadable files
            return []

        rel_path = str(file_path)
        ext = file_path.suffix.lower()

        if ext == '.py':
            return self._chunk_python(content, rel_path)
        elif ext == '.md':
            return self._chunk_markdown(content, rel_path)
        elif ext in ['.rs', '.lua']:
            lang = "Rust" if ext == '.rs' else "Lua"
            return self._chunk_regex(content, rel_path, lang)
        else:
            return self._chunk_markdown(content, rel_path) # Default to text sliding window

    def _chunk_python(self, content: str, source_path: str) -> List[Chunk]:
        chunks = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fallback for invalid python
            return self._chunk_markdown(content, source_path)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno
                end = node.end_lineno or start
                code_lines = content.splitlines()[start-1:end]
                code_text = "\n".join(code_lines)
                
                # Use robust chunk_id
                cid = f"{source_path}::{node.name}::{start}"
                
                chunks.append(Chunk(
                    chunk_id=cid,
                    source_path=source_path,
                    chunk_type="Python",
                    content=code_text,
                    start_line=start,
                    end_line=end,
                    extra_meta={"node_name": node.name}
                ))
        return chunks

    def _chunk_markdown(self, content: str, source_path: str, window_size: int = 5) -> List[Chunk]:
        """Chunks by grouping paragraphs in a sliding window to capture context."""
        chunks = []
        lines = content.splitlines()
        
        # Split into paragraphs (blocks of text separated by blank lines)
        paragraphs = []
        current_para = []
        start_lineno = 1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "":
                if current_para:
                    end_lineno = i # i is 0-indexed, so line before blank is i
                    paragraphs.append((start_lineno, end_lineno, "\n".join(current_para)))
                    current_para = []
                start_lineno = i + 2
            else:
                if not current_para:
                    start_lineno = i + 1
                current_para.append(line)
                
        if current_para:
            paragraphs.append((start_lineno, len(lines), "\n".join(current_para)))

        # Sliding window over paragraphs
        for i in range(0, max(1, len(paragraphs) - window_size + 1), max(1, window_size // 2)):
            window = paragraphs[i:i + window_size]
            if not window:
                break
                
            start = window[0][0]
            end = window[-1][1]
            text = "\n\n".join(p[2] for p in window)
            
            cid = f"{source_path}::MD::{start}"
            chunks.append(Chunk(
                chunk_id=cid,
                source_path=source_path,
                chunk_type="Markdown",
                content=text,
                start_line=start,
                end_line=end
            ))
            if i + window_size >= len(paragraphs):
                break
        return chunks

    def _chunk_regex(self, content: str, source_path: str, lang: str) -> List[Chunk]:
        """
        Uses RegEx to find function definitions in Rust or Lua.
        Rust: "fn name("
        Lua: "function name("
        Extracts up to next match or EOF.
        """
        chunks = []
        
        if lang == "Rust":
            pattern = re.compile(r'^(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)\s*\(', re.MULTILINE)
        else:
            # Lua
            pattern = re.compile(r'^(?:local\s+)?function\s+([a-zA-Z0-9_:\.]+)\s*\(', re.MULTILINE)

        matches = list(pattern.finditer(content))
        lines = content.splitlines(keepends=True) # preserve \n for accurate reconstruction
        
        def count_lines(s: str) -> int:
            return s.count('\n') + (1 if not s.endswith('\n') and len(s) > 0 else 0)

        for i, match in enumerate(matches):
            node_name = match.group(1)
            start_pos = match.start()
            end_pos = matches[i+1].start() if i + 1 < len(matches) else len(content)
            
            chunk_content = content[start_pos:end_pos].strip()
            
            # Calculate line numbers
            # A bit slow for very large files, but acceptable for typical source code
            prefix = content[:start_pos]
            start_line = count_lines(prefix) + 1
            end_line = start_line + count_lines(chunk_content) - 1
            
            cid = f"{source_path}::{lang}::{start_line}"
            chunks.append(Chunk(
                chunk_id=cid,
                source_path=source_path,
                chunk_type=lang,
                content=chunk_content,
                start_line=start_line,
                end_line=end_line,
                extra_meta={"node_name": node_name}
            ))

        return chunks
