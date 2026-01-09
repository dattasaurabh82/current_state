/**
 * Live Logs - xterm.js Integration with WebSocket
 * 
 * Streams log files in real-time via WebSocket.
 * Color coding: ERROR=red, WARNING=yellow, SUCCESS=green, DEBUG=dim
 */

document.addEventListener('DOMContentLoaded', function() {
    // Terminal instances
    const terminals = {};
    const fitAddons = {};
    
    // Log panel configuration (must match server)
    const panels = [
        { id: 'log-panel-1', name: 'full_cycle_btn.log' },
        { id: 'log-panel-2', name: 'player_service.log' },
        { id: 'log-panel-3', name: 'world_theme_music_player.log' },
        { id: 'log-panel-4', name: 'backup.log' },
    ];

    // ANSI color codes for log levels
    const COLORS = {
        ERROR: '\x1b[91m',    // Bright red
        WARNING: '\x1b[93m',  // Bright yellow
        SUCCESS: '\x1b[92m',  // Bright green
        INFO: '\x1b[97m',     // Bright white
        DEBUG: '\x1b[90m',    // Dim gray
        RESET: '\x1b[0m',     // Reset
    };

    /**
     * Colorize a log line based on log level
     */
    function colorizeLine(line) {
        // Loguru format: "2026-01-09 20:38:11.082 | INFO     | module:func:line - message"
        if (line.includes('| ERROR')) {
            return COLORS.ERROR + line + COLORS.RESET;
        } else if (line.includes('| WARNING')) {
            return COLORS.WARNING + line + COLORS.RESET;
        } else if (line.includes('| SUCCESS')) {
            return COLORS.SUCCESS + line + COLORS.RESET;
        } else if (line.includes('| DEBUG')) {
            return COLORS.DEBUG + line + COLORS.RESET;
        } else if (line.includes('| INFO')) {
            return COLORS.INFO + line + COLORS.RESET;
        } else if (line.startsWith('//')) {
            // Comment/placeholder lines
            return COLORS.DEBUG + line + COLORS.RESET;
        }
        return line;
    }

    /**
     * Write content to terminal with colorization
     */
    function writeToTerminal(term, content) {
        const lines = content.split('\n');
        lines.forEach((line, index) => {
            if (line.trim()) {
                term.writeln(colorizeLine(line));
            } else if (index < lines.length - 1) {
                // Preserve empty lines except trailing
                term.writeln('');
            }
        });
    }

    /**
     * Initialize terminal for a panel
     */
    function initTerminal(panelId) {
        const container = document.getElementById(panelId);
        if (!container) return null;

        const term = new Terminal({
            theme: {
                background: '#0a0a0a',
                foreground: '#e0e0e0',
                cursor: '#606060',
                selection: '#333333',
                black: '#0a0a0a',
                red: '#cc6666',
                green: '#66cc66',
                yellow: '#cccc66',
                blue: '#6699cc',
                magenta: '#cc66cc',
                cyan: '#66cccc',
                white: '#e0e0e0',
                brightBlack: '#606060',
                brightRed: '#ff6666',
                brightGreen: '#66ff66',
                brightYellow: '#ffff66',
                brightBlue: '#6699ff',
                brightMagenta: '#ff66ff',
                brightCyan: '#66ffff',
                brightWhite: '#ffffff',
            },
            fontSize: 11,
            fontFamily: "'IBM Plex Mono', monospace",
            cursorBlink: false,
            disableStdin: true,
            scrollback: 2000,
            convertEol: true,
        });

        const fit = new FitAddon.FitAddon();
        term.loadAddon(fit);
        term.open(container);
        fit.fit();

        return { term, fit };
    }

    /**
     * Initialize all terminals
     */
    function initAllTerminals() {
        panels.forEach(panel => {
            const result = initTerminal(panel.id);
            if (result) {
                terminals[panel.id] = result.term;
                fitAddons[panel.id] = result.fit;
                
                // Show waiting message
                result.term.writeln(COLORS.DEBUG + '// Connecting to log stream...' + COLORS.RESET);
            }
        });
    }

    /**
     * Handle window resize
     */
    function handleResize() {
        Object.values(fitAddons).forEach(fit => {
            try {
                fit.fit();
            } catch (e) {
                // Ignore fit errors
            }
        });
    }

    /**
     * Connect to WebSocket
     */
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
        
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
            console.log('[Logs] WebSocket connected');
            // Clear waiting messages
            Object.values(terminals).forEach(term => {
                term.clear();
            });
        };
        
        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                const term = terminals[data.panel];
                
                if (term && data.content) {
                    if (data.type === 'initial') {
                        // Initial load - clear and write
                        term.clear();
                        writeToTerminal(term, data.content);
                    } else {
                        // Update - append
                        writeToTerminal(term, data.content);
                    }
                }
            } catch (e) {
                console.error('[Logs] Error parsing message:', e);
            }
        };
        
        ws.onclose = function() {
            console.log('[Logs] WebSocket disconnected, reconnecting in 3s...');
            // Show disconnected state
            Object.values(terminals).forEach(term => {
                term.writeln('');
                term.writeln(COLORS.WARNING + '// Disconnected. Reconnecting...' + COLORS.RESET);
            });
            
            // Reconnect after delay
            setTimeout(connectWebSocket, 3000);
        };
        
        ws.onerror = function(error) {
            console.error('[Logs] WebSocket error:', error);
        };
        
        return ws;
    }

    // Initialize
    initAllTerminals();
    window.addEventListener('resize', handleResize);
    
    // Small delay to let terminals render, then connect
    setTimeout(connectWebSocket, 100);
});
