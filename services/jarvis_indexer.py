#!/usr/bin/env python3
import asyncio
import logging
import os
import signal
from pathlib import Path
import sys

# Add JARVIS_ROOT to sys.path
JARVIS_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(JARVIS_ROOT))

from lib.indexing.embedding_engine import EmbeddingEngine
from lib.indexing.faiss_index import FAISSIndexManager
from lib.indexing.ingestor import Ingestor
from lib.indexing.auto_reindex import AutoReindexTimer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("jarvis.indexer_service")

async def main():
    logger.info("Starting Jarvis Indexer Service...")
    
    # Initialize components
    embeddings = EmbeddingEngine()
    faiss_manager = FAISSIndexManager(
        index_path=str(JARVIS_ROOT / "index" / "faiss.bin"),
        meta_db_path=str(JARVIS_ROOT / "data" / "knowledge.db")
    )
    ingestor = Ingestor()
    
    # Start the Timer (Watchdog + Scheduler)
    # We watch the JARVIS_ROOT/src or the whole JARVIS_ROOT depending on policy.
    # For now, we watch the main Jarvis directory.
    timer = AutoReindexTimer(
        watch_dir=str(JARVIS_ROOT),
        faiss_manager=faiss_manager,
        ingestor=ingestor,
        embedding_engine=embeddings
    )
    
    timer.start()
    
    # Handle Shutdown
    stop_event = asyncio.Event()
    
    def shutdown_signal():
        logger.info("Shutdown signal received.")
        stop_event.set()

    # Note: loop.add_signal_handler is only on Unix
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_signal)
        
    await stop_event.wait()
    
    logger.info("Stopping Indexer Service...")
    timer.stop()
    logger.info("Indexer Service stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
