"""Example usage of FileWatcher for automatic cache invalidation.

This example demonstrates how to integrate the FileWatcher into your
application for automatic cache invalidation when files change.
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path

from skillmeat.cache.repository import CacheRepository
from skillmeat.cache.watcher import FileWatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Basic usage example: start watcher with default paths."""
    logger.info("=== Basic Usage Example ===")

    # Create repository
    repo = CacheRepository()

    # Create watcher with default paths
    watcher = FileWatcher(cache_repository=repo)

    logger.info(f"Watching paths: {watcher.get_watch_paths()}")

    # Start watching
    watcher.start()
    logger.info("FileWatcher started")

    try:
        # Simulate application running
        logger.info("Application running... press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Stop watching
        watcher.stop()
        logger.info("FileWatcher stopped")


def example_custom_paths():
    """Example with custom watch paths."""
    logger.info("=== Custom Paths Example ===")

    repo = CacheRepository()

    # Specify custom paths to watch
    custom_paths = [
        str(Path.home() / ".skillmeat"),
        str(Path.cwd() / ".claude"),
        str(Path.cwd() / "my_project"),
    ]

    watcher = FileWatcher(
        cache_repository=repo,
        watch_paths=custom_paths,
        debounce_ms=200,  # Custom debounce window
    )

    logger.info(f"Watching {len(watcher.get_watch_paths())} paths")

    watcher.start()

    try:
        # Simulate work
        time.sleep(5)
    finally:
        watcher.stop()


def example_dynamic_paths():
    """Example: dynamically add/remove watch paths."""
    logger.info("=== Dynamic Paths Example ===")

    repo = CacheRepository()
    watcher = FileWatcher(cache_repository=repo)

    watcher.start()
    logger.info("FileWatcher started")

    # Add a new path while running
    new_path = Path.cwd() / "temp_watch"
    if new_path.exists():
        success = watcher.add_watch_path(str(new_path))
        if success:
            logger.info(f"Added watch path: {new_path}")

    logger.info(f"Currently watching: {watcher.get_watch_paths()}")

    # Simulate work
    time.sleep(2)

    # Remove the path
    if new_path.exists():
        success = watcher.remove_watch_path(str(new_path))
        if success:
            logger.info(f"Removed watch path: {new_path}")

    watcher.stop()
    logger.info("FileWatcher stopped")


def example_with_api_server():
    """Example: integrate with FastAPI server lifecycle."""
    logger.info("=== API Server Integration Example ===")

    # This demonstrates how to integrate with a FastAPI application
    # In a real application, this would be in your API startup/shutdown handlers

    repo = CacheRepository()
    watcher = FileWatcher(cache_repository=repo)

    # In FastAPI, you would use:
    # @app.on_event("startup")
    def startup():
        logger.info("Starting API server...")
        watcher.start()
        logger.info("FileWatcher started with API server")

    # @app.on_event("shutdown")
    def shutdown():
        logger.info("Shutting down API server...")
        watcher.stop()
        logger.info("FileWatcher stopped with API server")

    # Simulate server lifecycle
    startup()

    try:
        logger.info("API server running... press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        shutdown()


def example_manual_invalidation():
    """Example: manually trigger cache invalidation."""
    logger.info("=== Manual Invalidation Example ===")

    repo = CacheRepository()
    watcher = FileWatcher(cache_repository=repo)

    watcher.start()

    # You can manually trigger invalidation without file changes
    # This is useful for testing or forced refresh

    # Invalidate specific project
    watcher._queue_invalidation("project-123")
    logger.info("Queued invalidation for project-123")

    # Invalidate all projects
    watcher._queue_invalidation(None)
    logger.info("Queued global invalidation")

    # Wait for debounce to process
    time.sleep(0.2)

    watcher.stop()


def example_graceful_shutdown():
    """Example: graceful shutdown with signal handling."""
    logger.info("=== Graceful Shutdown Example ===")

    repo = CacheRepository()
    watcher = FileWatcher(cache_repository=repo)

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    watcher.start()
    logger.info("FileWatcher started. Send SIGINT or SIGTERM to stop.")

    try:
        # Keep running until signal received
        signal.pause()
    except AttributeError:
        # signal.pause() not available on Windows
        while watcher.is_running():
            time.sleep(1)


def example_with_logging_config():
    """Example: configure detailed logging for debugging."""
    logger.info("=== Detailed Logging Example ===")

    # Enable debug logging for watcher
    logging.getLogger("skillmeat.cache.watcher").setLevel(logging.DEBUG)
    logging.getLogger("watchdog").setLevel(logging.INFO)

    repo = CacheRepository()
    watcher = FileWatcher(cache_repository=repo, debounce_ms=50)

    watcher.start()
    logger.info("FileWatcher started with debug logging")

    # Make some file changes to see debug logs
    test_dir = Path.cwd() / ".claude"
    if test_dir.exists():
        manifest = test_dir / "manifest.toml"
        if manifest.exists():
            # Touch the file to trigger an event
            manifest.touch()
            logger.info(f"Modified {manifest}")

    # Wait for events to process
    time.sleep(0.5)

    watcher.stop()


if __name__ == "__main__":
    # Run examples
    examples = [
        example_basic_usage,
        example_custom_paths,
        example_dynamic_paths,
        example_manual_invalidation,
        example_with_logging_config,
        # example_with_api_server,  # Uncomment to run interactive example
        # example_graceful_shutdown,  # Uncomment to run interactive example
    ]

    for i, example in enumerate(examples, 1):
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running Example {i}/{len(examples)}: {example.__name__}")
            logger.info(f"{'='*60}\n")
            example()
        except Exception as e:
            logger.error(f"Example failed: {e}", exc_info=True)

        # Pause between examples
        if i < len(examples):
            logger.info("\nPausing between examples...\n")
            time.sleep(2)

    logger.info("\nAll examples completed!")
