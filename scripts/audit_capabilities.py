# scripts/audit_capabilities.py
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.absolute()
REQUIRE_PATTERN = re.compile(r'\.require\(["\']([^"\']+)["\']')
REQUEST_PATTERN = re.compile(r'CapabilityRequest\(.*?capability=["\']([^"\']+)["\']', re.DOTALL)

def audit():
    print(f"--- Jarvis v2 Capability Audit ---")
    print(f"Root: {REPO_ROOT}\n")
    
    findings = {}
    
    for root, _, files in os.walk(REPO_ROOT):
        for file in files:
            if file.endswith(".py") and "test" not in root:
                path = Path(root) / file
                content = path.read_text()
                
                requires = REQUIRE_PATTERN.findall(content)
                requests = REQUEST_PATTERN.findall(content)
                
                caps = set(requires + requests)
                if caps:
                    findings[str(path.relative_to(REPO_ROOT))] = sorted(list(caps))

    if not findings:
        print("No capability requirements found.")
        return

    print(f"{'File':<50} | {'Capabilities'}")
    print("-" * 80)
    for file, caps in sorted(findings.items()):
        print(f"{file:<50} | {', '.join(caps)}")
    
    print(f"\nAudit complete. Found {len(findings)} files with capability requirements.")

if __name__ == "__main__":
    audit()
