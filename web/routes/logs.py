"""
Live Logs Routes - Tab 3

WebSocket streaming of log files with file watching.
"""

import asyncio
from pathlib import Path
from typing import Dict, Set, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

router = APIRouter()

# Paths
WEB_DIR = Path(__file__).parent.parent
PROJECT_ROOT = WEB_DIR.parent
LOGS_DIR = PROJECT_ROOT / "logs"

# Log files configuration (keys must match HTML element IDs)
LOG_FILES = {
    "log-panel-1": "full_cycle_btn.log",
    "log-panel-2": "player_service.log",
    "log-panel-3": "world_theme_music_player.log",
    "log-panel-4": "backup.log",
}


class LogFileHandler(FileSystemEventHandler):
    """Watchdog handler for log file changes."""
    
    def __init__(self, callback):
        self.callback = callback
        self._last_positions: Dict[str, int] = {}
    
    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and not event.is_directory:
            filepath = Path(event.src_path)
            if filepath.suffix == ".log":
                # Read new content from file
                new_content = self._get_new_content(filepath)
                if new_content:
                    self.callback(filepath.name, new_content)
    
    def _get_new_content(self, filepath: Path) -> str:
        """Read only new content since last read."""
        try:
            file_key = str(filepath)
            last_pos = self._last_positions.get(file_key, 0)
            
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)  # End of file
                file_size = f.tell()
                
                # If file was truncated/rotated, start from beginning
                if file_size < last_pos:
                    last_pos = 0
                
                f.seek(last_pos)
                new_content = f.read()
                self._last_positions[file_key] = f.tell()
                
            return new_content
        except Exception:
            return ""
    
    def init_file_position(self, filepath: Path, tail_lines: int = 50):
        """Initialize file position, optionally reading last N lines."""
        try:
            file_key = str(filepath)
            
            if not filepath.exists():
                self._last_positions[file_key] = 0
                return ""
            
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                # Get file size
                f.seek(0, 2)
                file_size = f.tell()
                
                # Read last N lines
                lines = []
                if file_size > 0:
                    # Start from end and work backwards
                    chunk_size = 8192
                    position = file_size
                    
                    while position > 0 and len(lines) < tail_lines:
                        read_size = min(chunk_size, position)
                        position -= read_size
                        f.seek(position)
                        chunk = f.read(read_size)
                        lines = chunk.splitlines() + lines
                    
                    lines = lines[-tail_lines:]
                
                # Set position to end of file
                self._last_positions[file_key] = file_size
                
                return "\n".join(lines)
        except Exception:
            return ""


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.observer: Optional[Observer] = None
        self.handler: Optional[LogFileHandler] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        
        # Start file watcher if first connection
        if len(self.active_connections) == 1:
            self._start_watcher()
        
        # Send initial log content (tail of each file)
        await self._send_initial_logs(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        
        # Stop watcher if no connections
        if len(self.active_connections) == 0:
            self._stop_watcher()
    
    async def _send_initial_logs(self, websocket: WebSocket):
        """Send last N lines of each log file on connect."""
        for panel_id, filename in LOG_FILES.items():
            filepath = LOGS_DIR / filename
            
            if self.handler:
                content = self.handler.init_file_position(filepath, tail_lines=100)
                if content:
                    await websocket.send_json({
                        "panel": panel_id,
                        "filename": filename,
                        "content": content,
                        "type": "initial",
                    })
                else:
                    # File doesn't exist or is empty
                    await websocket.send_json({
                        "panel": panel_id,
                        "filename": filename,
                        "content": f"// Waiting for {filename}...\n",
                        "type": "initial",
                    })
    
    def _start_watcher(self):
        """Start the file system watcher."""
        self._loop = asyncio.get_event_loop()
        
        def on_log_change(filename: str, content: str):
            # Find panel for this filename
            panel_id = None
            for pid, fname in LOG_FILES.items():
                if fname == filename:
                    panel_id = pid
                    break
            
            if panel_id and content:
                # Schedule async broadcast
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "panel": panel_id,
                        "filename": filename,
                        "content": content,
                        "type": "update",
                    }),
                    self._loop
                )
        
        self.handler = LogFileHandler(on_log_change)
        self.observer = Observer()
        
        # Watch logs directory
        if LOGS_DIR.exists():
            self.observer.schedule(self.handler, str(LOGS_DIR), recursive=False)
            self.observer.start()
    
    def _stop_watcher(self):
        """Stop the file system watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=1)
            self.observer = None
            self.handler = None
    
    async def _broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.active_connections.discard(conn)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for live log streaming."""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive, handle any client messages
            data = await websocket.receive_text()
            # Could handle commands like "clear" or "pause" here
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
