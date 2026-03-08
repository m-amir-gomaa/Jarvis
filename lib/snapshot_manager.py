import os
import tarfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

class SnapshotManager:
    def __init__(self, vault_root: Path):
        self.vault_root = vault_root
        self.snapshots_dir = self.vault_root / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, label: str = "manual") -> Path:
        """Create a compressed tarball of the vault root."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"snapshot_{label}_{ts}.tar.gz"
        snapshot_path = self.snapshots_dir / snapshot_name
        
        # We exclude the 'snapshots' directory itself to avoid recursive snapshots
        def exclude_function(tarinfo):
            if "snapshots" in tarinfo.name:
                return None
            return tarinfo

        with tarfile.open(snapshot_path, "w:gz") as tar:
            tar.add(self.vault_root, arcname=".", filter=exclude_function)
            
        return snapshot_path

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        List all available snapshots in the snapshots directory.
        
        Returns:
            A list of dictionaries containing snapshot metadata:
            - name: The filename of the snapshot.
            - path: The absolute path to the snapshot.
            - size_mb: The size of the snapshot in megabytes.
            - created_at: ISO formatted creation timestamp.
        """
        snapshots = []
        for f in self.snapshots_dir.glob("snapshot_*.tar.gz"):
            stat = f.stat()
            snapshots.append({
                "name": f.name,
                "path": str(f),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
            })
        # Sort by creation time descending
        snapshots.sort(key=lambda x: x["created_at"], reverse=True)
        return snapshots

    def restore_snapshot(self, snapshot_name: str) -> bool:
        """
        Restore the vault root from a snapshot.
        Warning: This will overwrite existing files in the vault.
        
        Args:
            snapshot_name: The name of the snapshot file to restore.
            
        Returns:
            True if restoration was successful, False otherwise.
        """
        snapshot_path = self.snapshots_dir / snapshot_name
        if not snapshot_path.exists():
            return False
            
        # Optional: Backup current state before restoring? 
        # For simplicity, we just extract.
        # Warning: This will overwrite files in the vault.
        with tarfile.open(snapshot_path, "r:gz") as tar:
            tar.extractall(path=self.vault_root)
        return True
