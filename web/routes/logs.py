"""
Live Logs Routes - Tab 3

WebSocket streaming of log files with real-time file watching.

Architecture:
- ConnectionManager handles multiple WebSocket clients
- LogFileHandler uses watchdog to detect file changes
- Changes are broadcast to all connected clients as JSON messages

Message format:
{
    "panel": "log-panel-1",       # Panel ID (matches frontend)
    "filename": "cron.log",       # Log filename
    "content": "...",             # New log content
    "type": "initial" | "update"  # Initial load or incremental update
}
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

WEB_DIR = Path(__file__).parent.parent
PROJECT_ROOT = WEB_DIR.parent
LOGS_DIR = PROJECT_ROOT / "logs"

# Log panel configuration
# Keys are HTML element IDs, values are log filenames
LOG_FILES: Dict[str, str] = {
    "log-panel-1": "full_cycle_btn.log",
    "log-panel-2": "player_service.log",
    "log-panel-3": "world_theme_music_player.log",
    "log-panel-4": "backup.log",
}

# Number of lines to show on initial connection
INITIAL_TAIL_LINES = 100

# Chunk size for reading file backwards
READ_CHUNK_SIZE = 8192

logger = logging.getLogger(__name__)
router = APIRouter()


# -----------------------------------------------------------------------------
# File Watching
# -----------------------------------------------------------------------------

class LogFileHandler(FileSystemEventHandler):
    """
    Watchdog handler for log file changes.
    
    Tracks file positions to only send new content since last read.
    Handles file truncation/rotation gracefully.
    """
    
    def __init__(self, callback):
        """
        Initialize handler with callback for new content.
        
        Args:
            callback: Function(filename: str, content: str) called on changes
        """
        self.callback = callback
        self._last_positions: Dict[str, int] = {}
    
    def on_modified(self, event) -> None:
        """Handle file modification events."""
        if not isinstance(event, FileModifiedEvent) or event.is_directory:
            return
            
        filepath = Path(event.src_path)
        if filepath.suffix != ".log":
            return
            
        new_content = self._get_new_content(filepath)
        if new_content:
            self.callback(filepath.name, new_content)
    
    def _get_new_content(self, filepath: Path) -> str:
        """
        Read only new content since last read position.
        
        Handles file truncation (log rotation) by resetting position.
        
        Args:
            filepath: Path to the log file.
            
        Returns:
            New content string, or empty string if no new content.
        """
        try:
            file_key = str(filepath)
            last_pos = self._last_positions.get(file_key, 0)
            
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                # Get current file size
                f.seek(0, 2)
                file_size = f.tell()
                
                # Handle file truncation/rotation
                if file_size < last_pos:
                    logger.debug(f"File {filepath.name} was truncated, resetting position")
                    last_pos = 0
                
                # Read new content
                f.seek(last_pos)
                new_content = f.read()
                self._last_positions[file_key] = f.tell()
                
            return new_content
            
        except FileNotFoundError:
            logger.debug(f"File not found: {filepath}")
            return ""
        except Exception as e:
            logger.warning(f"Error reading {filepath}: {e}")
            return ""
    
    def init_file_position(self, filepath: Path, tail_lines: int = INITIAL_TAIL_LINES) -> str:
        """
        Initialize file position and return last N lines.
        
        Called on initial WebSocket connection to show recent history.
        
        Args:
            filepath: Path to the log file.
            tail_lines: Number of lines to return from end of file.
            
        Returns:
            Last N lines of the file as a string.
        """
        file_key = str(filepath)
        
        if not filepath.exists():
            self._last_positions[file_key] = 0
            return ""
        
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                # Get file size
                f.seek(0, 2)
                file_size = f.tell()
                
                if file_size == 0:
                    self._last_positions[file_key] = 0
                    return ""
                
                # Read backwards to get last N lines
                lines = self._read_last_lines(f, file_size, tail_lines)
                
                # Set position to end of file for future updates
                self._last_positions[file_key] = file_size
                
                return "\n".join(lines)
                
        except Exception as e:
            logger.warning(f"Error initializing {filepath}: {e}")
            self._last_positions[file_key] = 0
            return ""
    
    def _read_last_lines(self, f, file_size: int, num_lines: int) -> list:
        """
        Efficiently read the last N lines of a file.
        
        Reads backwards in chunks to avoid loading entire file.
        """
        lines = []
        position = file_size
        
        while position > 0 and len(lines) < num_lines:
            read_size = min(READ_CHUNK_SIZE, position)
            position -= read_size
            f.seek(position)
            chunk = f.read(read_size)
            lines = chunk.splitlines() + lines
        
        return lines[-num_lines:]


# -----------------------------------------------------------------------------
# Connection Manager
# -----------------------------------------------------------------------------

class ConnectionManager:
    """
    Manages WebSocket connections and file watching.
    
    Starts/stops the file observer based on active connections.
    Broadcasts log updates to all connected clients.
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._observer: Optional[Observer] = None
        self._handler: Optional[LogFileHandler] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept a new WebSocket connection.
        
        Starts file watcher if this is the first connection.
        Sends initial log content to the new client.
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Start file watcher if first connection
        if len(self.active_connections) == 1:
            self._start_watcher()
        
        # Send initial log content
        await self._send_initial_logs(websocket)
    
    def disconnect(self, websocket: WebSocket) -> None:
        """
        Handle WebSocket disconnection.
        
        Stops file watcher if no more connections.
        """
        self.active_connections.discard(websocket)
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
        
        # Stop watcher if no connections
        if len(self.active_connections) == 0:
            self._stop_watcher()
    
    async def _send_initial_logs(self, websocket: WebSocket) -> None:
        """Send last N lines of each log file on initial connection."""
        if self._handler is None:
            return
            
        for panel_id, filename in LOG_FILES.items():
            filepath = LOGS_DIR / filename
            content = self._handler.init_file_position(filepath)
            
            message: Dict[str, Any] = {
                "panel": panel_id,
                "filename": filename,
                "type": "initial",
            }
            
            if content:
                message["content"] = content
            else:
                message["content"] = f"// Waiting for {filename}...\n"
            
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending initial logs: {e}")
    
    def _start_watcher(self) -> None:
        """Start the filesystem watcher for log directory."""
        self._loop = asyncio.get_event_loop()
        
        def on_log_change(filename: str, content: str) -> None:
            """Callback when a log file changes."""
            # Find panel ID for this filename
            panel_id = None
            for pid, fname in LOG_FILES.items():
                if fname == filename:
                    panel_id = pid
                    break
            
            if panel_id is None or not content:
                return
            
            # Schedule async broadcast on the event loop
            message = {
                "panel": panel_id,
                "filename": filename,
                "content": content,
                "type": "update",
            }
            
            if self._loop is not None:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast(message),
                    self._loop
                )
        
        self._handler = LogFileHandler(on_log_change)
        self._observer = Observer()
        
        if LOGS_DIR.exists():
            self._observer.schedule(self._handler, str(LOGS_DIR), recursive=False)
            self._observer.start()
            logger.info(f"Started watching {LOGS_DIR}")
        else:
            logger.warning(f"Logs directory does not exist: {LOGS_DIR}")
    
    def _stop_watcher(self) -> None:
        """Stop the filesystem watcher."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
            self._handler = None
            logger.info("Stopped file watcher")
    
    async def _broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.
        
        Removes clients that fail to receive (disconnected).
        """
        if not self.active_connections:
            return
            
        disconnected: Set[WebSocket] = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)
            logger.debug("Removed disconnected client during broadcast")


# -----------------------------------------------------------------------------
# Global State
# -----------------------------------------------------------------------------

manager = ConnectionManager()


# -----------------------------------------------------------------------------
# WebSocket Route
# -----------------------------------------------------------------------------

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for live log streaming.
    
    Accepts connection, sends initial log content, then streams
    updates as log files change. Connection stays open until
    client disconnects.
    """
    await manager.connect(websocket)
    
    try:
        # Keep connection alive and handle any client messages
        while True:
            # Receive messages (could implement commands like "clear" or "pause")
            _ = await websocket.receive_text()
            # Currently we just ignore client messages
            
    except WebSocketDisconnect:
        logger.debug("Client initiated disconnect")
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)
