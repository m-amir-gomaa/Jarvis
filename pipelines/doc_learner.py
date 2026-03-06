import sys
import argparse
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Any, Optional
from lib.knowledge_manager import KnowledgeManager
from lib.event_bus import emit

# /THE_VAULT/jarvis/pipelines/doc_learner.py

class DocLearner:
    def __init__(self):
        self.km = KnowledgeManager()

    def scrape_official_docs(self, url: str, layer: int, category: Optional[str] = None, metadata: Optional[Dict] = None):
        """Basic scraper for official documentation sites."""
        print(f"[Learner] Crawling {url} for Layer {layer}...")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Simple heuristic: grab all paragraph text for Layer 1/2
            text_blocks = [p.get_text().strip() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])]
            content = "\n\n".join(text_blocks)
            
            title = soup.title.string if soup.title else url
            
            # Check if we already have this URL
            existing = self.is_already_indexed(url)
            if existing:
                print(f"[Learner] Updating existing entry: {title}")
                self.km.update_entry(url, content, metadata=metadata)
            else:
                print(f"[Learner] Adding new entry: {title}")
                self.km.add_entry(layer=layer, content=content, source_url=url, source_title=title, category=category, metadata=metadata)

            # Identification of "Recommended Reading" for Inbox (Layer 2 suggestion logic)
            self.identify_recommendations(soup, url)
            
            emit("doc_learner", "completed", {"url": url, "layer": layer})
            return True
        except Exception as e:
            print(f"[Learner] Error scraping {url}: {e}")
            return False

    def is_already_indexed(self, url: str) -> bool:
        results = self.km.search(url) # Temporary search match
        for r in results:
            if r.get('source_url') == url:
                return True
        return False

    def identify_recommendations(self, soup: BeautifulSoup, base_url: str):
        """Scan for 'book', 'guide', 'deep dive' to suggest to the user inbox."""
        anchors = soup.find_all('a', href=True)
        keywords = ['book', 'guide', 'pdf', 'deep dive', 'specification']
        for a in anchors:
            text = a.get_text().lower()
            if any(k in text for k in keywords):
                href = a['href']
                if not href.startswith('http'):
                    # Basic relative URL join
                    href = base_url.rstrip('/') + '/' + href.lstrip('/')
                
                print(f"[Learner] Found potential recommendation: {a.get_text().strip()} ({href})")
                self.km.add_to_inbox(title=a.get_text().strip(), url=href, reason=f"Suggested from {base_url}", item_type='recommended_reading')

    def ingest_path(self, path_str: str, layer: int, category: Optional[str] = None):
        """Ingest a local file or URL."""
        path = Path(path_str)
        metadata = {"category": category} if category else {}
        
        if path_str.startswith("http"):
            return self.scrape_official_docs(path_str, layer, category=category, metadata=metadata)
        
        if not path.exists():
            print(f"[Learner] Error: Path {path_str} not found.")
            return False
            
        print(f"[Learner] Ingesting local file: {path.name} into Layer {layer}...")
        
        content = ""
        # 1. Convert/Read
        if path.suffix.lower() in [".pdf", ".docx", ".pptx"]:
            from tools.doc_converter import convert_to_pdf, process_with_mineru
            pdf_p = convert_to_pdf(path)
            md_p = process_with_mineru(pdf_p)
            if md_p and md_p.exists():
                with open(md_p, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                print(f"[Learner] Error converting {path.name}")
                return False
        else:
            # Assume text/markdown
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
        # 2. Add to Knowledge Base
        title = path.name
        self.km.add_entry(layer=layer, content=content, source_url=str(path.absolute()), source_title=title, category=category, metadata=metadata)
        
        emit("doc_learner", "completed", {"file": path.name, "layer": layer, "category": category})
        print(f"  Successfully learned '{title}'")
        return True

def main():
    parser = argparse.ArgumentParser(description="Jarvis Knowledge Learner")
    parser.add_argument("input", help="URL or File Path to ingest")
    parser.add_argument("--layer", "-l", type=int, default=3, choices=[1, 2, 3], help="Target Layer (default 3: Theory)")
    parser.add_argument("--category", "-c", help="Knowledge category (e.g., 'rust', 'assistant_nl')")
    args = parser.parse_args()

    learner = DocLearner()
    success = learner.ingest_path(args.input, args.layer, category=args.category)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
