/**
 * Live Logs - xterm.js Integration with WebSocket
 * 
 * Streams log files in real-time via WebSocket connection.
 * Each log panel displays a different log file with ANSI color coding.
 * 
 * Color scheme (matches Loguru format):
 * - ERROR: Bright red
 * - WARNING: Bright yellow  
 * - SUCCESS: Bright green
 * - INFO: Bright white
 * - DEBUG: Dim gray
 * 
 * @requires xterm.js
 * @requires xterm-addon-fit
 */

(function() {
    'use strict';

    // =========================================================================
    // Configuration
    // =========================================================================

    /**
     * Log panel configuration.
     * Must match LOG_FILES in logs.py on the server.
     */
    const LOG_PANELS = Object.freeze([
        { id: 'log-panel-1', name: 'full_cycle_btn.log' },
        { id: 'log-panel-2', name: 'player_service.log' },
        { id: 'log-panel-3', name: 'world_theme_music_player.log' },
        { id: 'log-panel-4', name: 'backup.log' },
    ]);

    /**
     * ANSI escape codes for log level colorization.
     */
    const ANSI_COLORS = Object.freeze({
        ERROR: '\x1b[91m',    // Bright red
        WARNING: '\x1b[93m',  // Bright yellow
        SUCCESS: '\x1b[92m',  // Bright green
        INFO: '\x1b[97m',     // Bright white
        DEBUG: '\x1b[90m',    // Dim gray
        RESET: '\x1b[0m',     // Reset to default
    });

    /**
     * Terminal theme (Dracula-inspired).
     */
    const TERMINAL_THEME = Object.freeze({
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
    });

    /**
     * Terminal configuration options.
     */
    const TERMINAL_OPTIONS = Object.freeze({
        theme: TERMINAL_THEME,
        fontSize: 11,
        fontFamily: "'IBM Plex Mono', monospace",
        cursorBlink: false,
        disableStdin: true,
        scrollback: 2000,
        convertEol: true,
    });

    /**
     * WebSocket reconnection delay in milliseconds.
     */
    const RECONNECT_DELAY_MS = 3000;

    // =========================================================================
    // State
    // =========================================================================

    /** @type {Object.<string, Terminal>} Terminal instances by panel ID */
    const terminals = {};

    /** @type {Object.<string, FitAddon>} FitAddon instances by panel ID */
    const fitAddons = {};

    /** @type {WebSocket|null} Current WebSocket connection */
    let webSocket = null;

    /** @type {boolean} Whether we're intentionally closing */
    let isClosing = false;

    // =========================================================================
    // Terminal Management
    // =========================================================================

    /**
     * Colorize a log line based on log level keywords.
     * 
     * Detects Loguru-style format: "YYYY-MM-DD HH:MM:SS.mmm | LEVEL | ..."
     * 
     * @param {string} line - Raw log line
     * @returns {string} Line with ANSI color codes
     */
    function colorizeLine(line) {
        if (line.includes('| ERROR')) {
            return ANSI_COLORS.ERROR + line + ANSI_COLORS.RESET;
        }
        if (line.includes('| WARNING')) {
            return ANSI_COLORS.WARNING + line + ANSI_COLORS.RESET;
        }
        if (line.includes('| SUCCESS')) {
            return ANSI_COLORS.SUCCESS + line + ANSI_COLORS.RESET;
        }
        if (line.includes('| DEBUG')) {
            return ANSI_COLORS.DEBUG + line + ANSI_COLORS.RESET;
        }
        if (line.includes('| INFO')) {
            return ANSI_COLORS.INFO + line + ANSI_COLORS.RESET;
        }
        if (line.startsWith('//')) {
            // Comment/placeholder lines
            return ANSI_COLORS.DEBUG + line + ANSI_COLORS.RESET;
        }
        return line;
    }

    /**
     * Write content to a terminal with colorization.
     * 
     * Splits content into lines and applies color coding to each.
     * 
     * @param {Terminal} term - xterm.js Terminal instance
     * @param {string} content - Content to write
     */
    function writeToTerminal(term, content) {
        if (!term || !content) return;

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
     * Initialize a terminal for a specific panel.
     * 
     * Creates xterm.js Terminal instance with FitAddon for auto-sizing.
     * 
     * @param {string} panelId - HTML element ID for the panel
     * @returns {boolean} True if initialization succeeded
     */
    function initTerminal(panelId) {
        const container = document.getElementById(panelId);
        if (!container) {
            console.warn(`[Logs] Panel container not found: ${panelId}`);
            return false;
        }

        // Don't reinitialize
        if (terminals[panelId]) {
            return true;
        }

        try {
            const term = new Terminal(TERMINAL_OPTIONS);
            const fit = new FitAddon.FitAddon();

            term.loadAddon(fit);
            term.open(container);
            fit.fit();

            terminals[panelId] = term;
            fitAddons[panelId] = fit;

            return true;
        } catch (error) {
            console.error(`[Logs] Failed to initialize terminal for ${panelId}:`, error);
            return false;
        }
    }

    /**
     * Initialize all terminal panels.
     */
    function initAllTerminals() {
        LOG_PANELS.forEach(panel => {
            if (initTerminal(panel.id)) {
                // Show connecting message
                terminals[panel.id].writeln(
                    ANSI_COLORS.DEBUG + '// Connecting to log stream...' + ANSI_COLORS.RESET
                );
            }
        });
    }

    /**
     * Resize all terminals to fit their containers.
     */
    function fitAllTerminals() {
        Object.entries(fitAddons).forEach(([panelId, fit]) => {
            try {
                fit.fit();
            } catch (error) {
                // Ignore fit errors (can happen during rapid resizes)
            }
        });
    }

    // =========================================================================
    // WebSocket Management
    // =========================================================================

    /**
     * Build WebSocket URL based on current page protocol and host.
     * 
     * @returns {string} WebSocket URL
     */
    function buildWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/ws/logs`;
    }

    /**
     * Handle incoming WebSocket message.
     * 
     * Expected message format:
     * {
     *   panel: "log-panel-1",
     *   filename: "cron.log",
     *   content: "...",
     *   type: "initial" | "update"
     * }
     * 
     * @param {MessageEvent} event - WebSocket message event
     */
    function handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            const term = terminals[data.panel];

            if (!term || !data.content) {
                return;
            }

            if (data.type === 'initial') {
                // Initial load - clear and write all content
                term.clear();
                writeToTerminal(term, data.content);
            } else {
                // Incremental update - append
                writeToTerminal(term, data.content);
            }
        } catch (error) {
            console.error('[Logs] Error parsing WebSocket message:', error);
        }
    }

    /**
     * Show disconnection message in all terminals.
     */
    function showDisconnectedState() {
        Object.values(terminals).forEach(term => {
            term.writeln('');
            term.writeln(ANSI_COLORS.WARNING + '// Disconnected. Reconnecting...' + ANSI_COLORS.RESET);
        });
    }

    /**
     * Clear all terminals (on successful reconnection).
     */
    function clearAllTerminals() {
        Object.values(terminals).forEach(term => {
            term.clear();
        });
    }

    /**
     * Connect to WebSocket server.
     * 
     * Automatically reconnects on disconnection.
     */
    function connectWebSocket() {
        if (isClosing) return;

        const wsUrl = buildWebSocketUrl();
        console.log('[Logs] Connecting to', wsUrl);

        try {
            webSocket = new WebSocket(wsUrl);
        } catch (error) {
            console.error('[Logs] Failed to create WebSocket:', error);
            setTimeout(connectWebSocket, RECONNECT_DELAY_MS);
            return;
        }

        webSocket.onopen = function() {
            console.log('[Logs] WebSocket connected');
            clearAllTerminals();
        };

        webSocket.onmessage = handleMessage;

        webSocket.onclose = function(event) {
            console.log('[Logs] WebSocket closed:', event.code, event.reason);
            webSocket = null;

            if (!isClosing) {
                showDisconnectedState();
                console.log(`[Logs] Reconnecting in ${RECONNECT_DELAY_MS}ms...`);
                setTimeout(connectWebSocket, RECONNECT_DELAY_MS);
            }
        };

        webSocket.onerror = function(error) {
            console.error('[Logs] WebSocket error:', error);
        };
    }

    /**
     * Disconnect from WebSocket server.
     */
    function disconnectWebSocket() {
        isClosing = true;
        if (webSocket) {
            webSocket.close();
            webSocket = null;
        }
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the logs module.
     * 
     * Sets up terminals, event listeners, and WebSocket connection.
     */
    function init() {
        console.log('[Logs] Initializing...');

        // Initialize terminals
        initAllTerminals();

        // Handle window resize
        window.addEventListener('resize', fitAllTerminals);

        // Handle page unload
        window.addEventListener('beforeunload', disconnectWebSocket);

        // Connect to WebSocket (small delay for terminals to render)
        setTimeout(connectWebSocket, 100);

        console.log('[Logs] Initialization complete');
    }

    // =========================================================================
    // Entry Point
    // =========================================================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
