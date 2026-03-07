import os
import requests
import json
from typing import List, Dict, Optional
from lib.event_bus import emit

# /home/qwerty/NixOSenv/Jarvis/lib/anythingllm_client.py

BASE_URL = os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001")
API_KEY = os.environ.get("ANYTHINGLLM_API_KEY")

class AnythingLLMError(Exception):
    pass

def _get_headers() -> Dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers

def is_healthy() -> bool:
    """Checks if AnythingLLM is reachable."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/ping", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def list_workspaces() -> List[Dict]:
    """Returns list of workspaces."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/workspaces", headers=_get_headers())
        response.raise_for_status()
        return response.json().get("workspaces", [])
    except Exception as e:
        raise AnythingLLMError(f"Failed to list workspaces: {e}")

def create_workspace(name: str) -> Dict:
    """Creates a new workspace."""
    try:
        payload = {"name": name}
        response = requests.post(f"{BASE_URL}/api/v1/workspace/new", json=payload, headers=_get_headers())
        response.raise_for_status()
        emit('anythingllm', 'workspace_created', {'name': name})
        return response.json()
    except Exception as e:
        raise AnythingLLMError(f"Failed to create workspace: {e}")

def upload_document(workspace_slug: str, file_path: str) -> Dict:
    """Uploads a local file to a workspace."""
    try:
        url = f"{BASE_URL}/api/v1/workspace/{workspace_slug}/upload"
        with open(file_path, "rb") as f:
            files = {'file': f}
            response = requests.post(url, files=files, headers=_get_headers())
            response.raise_for_status()
            emit('anythingllm', 'document_uploaded', {'workspace': workspace_slug, 'file': os.path.basename(file_path)})
            return response.json()
    except Exception as e:
        raise AnythingLLMError(f"Failed to upload document: {e}")

def delete_document(workspace_slug: str, doc_id: str) -> Dict:
    """Deletes a document from a workspace."""
    try:
        url = f"{BASE_URL}/api/v1/workspace/{workspace_slug}/document/{doc_id}"
        response = requests.delete(url, headers=_get_headers())
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise AnythingLLMError(f"Failed to delete document: {e}")

if __name__ == "__main__":
    print(f"Health: {is_healthy()}")
    if is_healthy():
        try:
            ws = list_workspaces()
            print(f"Workspaces: {[w['name'] for w in ws]}")
        except Exception as e:
            print(f"Error: {e}")
