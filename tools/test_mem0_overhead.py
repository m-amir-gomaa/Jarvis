import sys
import os
import psutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_memory_mb():
    process = psutil.Process()
    # RSS (Resident Set Size) memory in MB
    return process.memory_info().rss / 1024 / 1024

baseline = get_memory_mb()
print(f"Baseline Python script memory: {baseline:.2f} MB")

os.environ["MEM0_DIR"] = "/tmp/mem0_test"

# Import mem0
import mem0
import openai

after_import = get_memory_mb()
print(f"Memory after 'import mem0': {after_import:.2f} MB")
print(f"Import Overhead: {after_import - baseline:.2f} MB")

if after_import - baseline > 50:
    print("\nFAIL: Overhead exceeds 50MB budget.")
    sys.exit(1)
else:
    print("\nPASS: Overhead acceptable.")
    sys.exit(0)
