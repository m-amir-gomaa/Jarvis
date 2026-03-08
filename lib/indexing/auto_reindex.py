import asyncio
import logging
from pathlib import Path
from typing import Set, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

class AutoReindexTimer(FileSystemEventHandler):
    """
    Monitors a directory for changes and incrementally updates the FAISS index.
    Features a debounce mechanism to prevent rapid duplicate indexing.
    Also hosts an apscheduler cron for full rebuilds.
    """
    def __init__(self, watch_dir: str, faiss_manager, ingestor, embedding_engine, debounce_seconds: float = 2.0):
        self.watch_dir = Path(watch_dir).expanduser()
        self.faiss_manager = faiss_manager
        self.ingestor = ingestor
        self.embedding_engine = embedding_engine
        self.debounce_seconds = debounce_seconds
        
        self.pending_files: Set[str] = set()
        self.pending_deletes: Set[str] = set()
        self._debounce_task: Optional[asyncio.Task] = None
        
        self.observer = Observer()
        self.scheduler = AsyncIOScheduler()
        
    def start(self):
        """Starts the watchdog observer and APScheduler."""
        # Setup watchdog
        self.observer.schedule(self, str(self.watch_dir), recursive=True)
        self.observer.start()
        
        # Setup scheduled full syncs (e.g. daily at 3 AM)
        self.scheduler.add_job(self.full_reindex, 'cron', hour=3, minute=0)
        self.scheduler.start()
        logger.info(f"AutoReindexTimer started watching {self.watch_dir}")

    def stop(self):
        """Stops the observer and scheduler."""
        self.observer.stop()
        self.scheduler.shutdown()
        self.observer.join()

    async def full_reindex(self):
        """Rebuilds the entire index from scratch."""
        logger.info("Starting scheduled full re-index...")
        await self.faiss_manager.rebuild()
        # In a real app we would traverse self.watch_dir here and queue everything
        # For this scope, the method acts as the hook for the cron.
        
    def _is_valid_file(self, path: str) -> bool:
        """Filter out hidden files, venv, etc."""
        p = Path(path)
        if p.name.startswith('.') or '.venv' in p.parts:
            return False
        return p.suffix in ['.py', '.md', '.rs', '.lua']

    def on_modified(self, event):
        if not event.is_directory and self._is_valid_file(event.src_path):
            self._schedule_update(event.src_path, is_delete=False)

    def on_created(self, event):
        if not event.is_directory and self._is_valid_file(event.src_path):
            self._schedule_update(event.src_path, is_delete=False)

    def on_deleted(self, event):
        if not event.is_directory and self._is_valid_file(event.src_path):
            self._schedule_update(event.src_path, is_delete=True)

    def _schedule_update(self, file_path: str, is_delete: bool):
        """Queues a file for processing and resets the debounce timer."""
        # We need thread-safe loop access if watchdog calls from a different thread
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return # No event loop running for the debounce task

        if is_delete:
            self.pending_deletes.add(file_path)
            self.pending_files.discard(file_path)
        else:
            self.pending_files.add(file_path)
            self.pending_deletes.discard(file_path)

        if self._debounce_task is not None:
            self._debounce_task.cancel()
            
        self._debounce_task = loop.create_task(self._debounce_worker())

    async def _debounce_worker(self):
        """Waits for quiet period, then processes queue."""
        try:
            await asyncio.sleep(self.debounce_seconds)
            await self._process_queue()
        except asyncio.CancelledError:
            pass

    async def _process_queue(self):
        """Processes all pending file modifications and deletions."""
        files_to_update = list(self.pending_files)
        files_to_delete = list(self.pending_deletes)
        
        self.pending_files.clear()
        self.pending_deletes.clear()

        # Handle deletions
        for file_path in files_to_delete:
            logger.info(f"Removing deleted file from index: {file_path}")
            await self.faiss_manager.delete_by_source(file_path)
            
        # Handle additions / modifications
        for file_path in files_to_update:
            logger.info(f"Re-indexing updated file: {file_path}")
            
            # Step 1: Remove old chunks from the same file
            await self.faiss_manager.delete_by_source(file_path)
            
            # Step 2: Extract new chunks
            path_obj = Path(file_path)
            chunks = self.ingestor.process_file(path_obj)
            
            if not chunks:
                continue

            # Step 3: Embed and add chunks to DB
            texts = [c.content for c in chunks]
            try:
                embeddings = await self.embedding_engine.embed_batch(texts)
                for chunk, emb in zip(chunks, embeddings):
                    await self.faiss_manager.add(
                        chunk_id=chunk.chunk_id,
                        source_path=str(path_obj),
                        chunk_type=chunk.chunk_type,
                        content=chunk.content,
                        embedding=emb.tolist(),
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        extra_meta=chunk.extra_meta
                    )
            except Exception as e:
                logger.error(f"Failed to embed/index file {file_path}: {e}")
