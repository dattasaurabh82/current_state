/**
 * Pipeline Visualization - Audio Player with WaveSurfer.js
 * 
 * Handles audio waveform visualization and playback for generated music files.
 * Polls for new audio files and updates the UI accordingly.
 * 
 * Features:
 * - WaveSurfer.js waveform visualization
 * - Play/pause with visual feedback
 * - Time display (current / duration)
 * - Auto-polling for new files
 * - Only one track plays at a time
 * 
 * @requires WaveSurfer.js
 */

(function() {
    'use strict';

    // =========================================================================
    // Configuration
    // =========================================================================

    /**
     * WaveSurfer configuration options.
     */
    const WAVESURFER_OPTIONS = Object.freeze({
        waveColor: '#606060',
        progressColor: '#a0a0a0',
        cursorColor: '#ffffff',
        barWidth: 2,
        barGap: 1,
        barRadius: 1,
        height: 48,
        normalize: true,
        backend: 'WebAudio',
        mediaControls: false,
    });

    /**
     * Polling interval for new audio files (milliseconds).
     */
    const POLL_INTERVAL_MS = 5000;

    /**
     * API endpoint for audio file list.
     */
    const AUDIO_FILES_API = '/api/audio-files';

    // =========================================================================
    // State
    // =========================================================================

    /** @type {Object.<number, WaveSurfer>} WaveSurfer instances by index */
    const wavesurfers = {};

    /** @type {number|null} Index of currently playing track */
    let currentlyPlaying = null;

    /** @type {number|null} Polling interval ID */
    let pollIntervalId = null;

    /** @type {number} Last known audio file count */
    let lastAudioCount = -1;

    // =========================================================================
    // Utility Functions
    // =========================================================================

    /**
     * Format seconds as M:SS string.
     * 
     * @param {number} seconds - Time in seconds
     * @returns {string} Formatted time string
     */
    function formatTime(seconds) {
        if (!Number.isFinite(seconds) || seconds < 0) {
            return '0:00';
        }
        
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Safely query an element within a parent.
     * 
     * @param {Element} parent - Parent element
     * @param {string} selector - CSS selector
     * @returns {Element|null} Found element or null
     */
    function querySelector(parent, selector) {
        try {
            return parent.querySelector(selector);
        } catch (error) {
            console.warn(`[Pipeline] Invalid selector: ${selector}`);
            return null;
        }
    }

    // =========================================================================
    // WaveSurfer Management
    // =========================================================================

    /**
     * Initialize WaveSurfer for a single audio item.
     * 
     * @param {number} index - 1-based index of the audio item
     * @param {string} url - URL of the audio file
     * @returns {boolean} True if initialization succeeded
     */
    function initWaveSurfer(index, url) {
        const container = document.getElementById(`waveform-${index}`);
        if (!container) {
            console.warn(`[Pipeline] Waveform container not found: waveform-${index}`);
            return false;
        }

        // Don't reinitialize
        if (wavesurfers[index]) {
            return true;
        }

        try {
            const wavesurfer = WaveSurfer.create({
                container: container,
                ...WAVESURFER_OPTIONS,
            });

            // Get DOM elements
            const audioItem = container.closest('.audio-item');
            if (!audioItem) {
                console.warn(`[Pipeline] Audio item container not found for index ${index}`);
                return false;
            }

            const playBtn = querySelector(audioItem, '.play-btn');
            const currentTimeEl = querySelector(audioItem, '.current-time');
            const durationEl = querySelector(audioItem, '.duration');

            if (!playBtn || !currentTimeEl || !durationEl) {
                console.warn(`[Pipeline] Missing controls for audio item ${index}`);
                return false;
            }

            // Load audio
            wavesurfer.load(url);

            // Event: Audio ready
            wavesurfer.on('ready', function() {
                durationEl.textContent = formatTime(wavesurfer.getDuration());
            });

            // Event: Playback progress
            wavesurfer.on('audioprocess', function() {
                currentTimeEl.textContent = formatTime(wavesurfer.getCurrentTime());
            });

            // Event: Seek (click on waveform)
            wavesurfer.on('seek', function() {
                currentTimeEl.textContent = formatTime(wavesurfer.getCurrentTime());
            });

            // Event: Playback finished
            wavesurfer.on('finish', function() {
                playBtn.textContent = '▶';
                currentlyPlaying = null;
            });

            // Event: Play button click
            playBtn.addEventListener('click', function() {
                handlePlayPause(index, wavesurfer, playBtn);
            });

            wavesurfers[index] = wavesurfer;
            return true;

        } catch (error) {
            console.error(`[Pipeline] Failed to initialize WaveSurfer for index ${index}:`, error);
            return false;
        }
    }

    /**
     * Handle play/pause button click.
     * 
     * Ensures only one track plays at a time.
     * 
     * @param {number} index - Index of the clicked track
     * @param {WaveSurfer} wavesurfer - WaveSurfer instance
     * @param {Element} playBtn - Play button element
     */
    function handlePlayPause(index, wavesurfer, playBtn) {
        // Stop any other playing track
        if (currentlyPlaying !== null && currentlyPlaying !== index) {
            const otherWavesurfer = wavesurfers[currentlyPlaying];
            if (otherWavesurfer) {
                otherWavesurfer.pause();
            }

            const otherBtn = document.querySelector(`[data-index="${currentlyPlaying}"]`);
            if (otherBtn) {
                otherBtn.textContent = '▶';
            }
        }

        // Toggle play/pause
        wavesurfer.playPause();

        if (wavesurfer.isPlaying()) {
            playBtn.textContent = '⏸';
            currentlyPlaying = index;
        } else {
            playBtn.textContent = '▶';
            currentlyPlaying = null;
        }
    }

    /**
     * Initialize all waveforms on the page.
     */
    function initAllWaveforms() {
        const audioItems = document.querySelectorAll('.audio-item[data-url]');
        
        audioItems.forEach((item, i) => {
            const url = item.dataset.url;
            const index = i + 1; // 1-indexed to match template
            
            if (url) {
                initWaveSurfer(index, url);
            }
        });

        console.log(`[Pipeline] Initialized ${audioItems.length} waveforms`);
    }

    /**
     * Destroy all WaveSurfer instances.
     */
    function destroyAllWaveforms() {
        Object.values(wavesurfers).forEach(ws => {
            try {
                ws.destroy();
            } catch (error) {
                // Ignore destruction errors
            }
        });

        // Clear the object
        Object.keys(wavesurfers).forEach(key => delete wavesurfers[key]);
        currentlyPlaying = null;
    }

    // =========================================================================
    // Audio File Polling
    // =========================================================================

    /**
     * Rebuild the audio files list.
     * 
     * Called when the file count changes to update the UI.
     * 
     * @param {Array} files - Array of audio file objects
     */
    function rebuildAudioList(files) {
        // Destroy existing waveforms
        destroyAllWaveforms();

        const container = document.getElementById('audio-files-container');
        if (!container) {
            console.warn('[Pipeline] Audio files container not found');
            return;
        }

        if (!files || files.length === 0) {
            container.innerHTML = '<p class="text-dim">No audio files found</p>';
            return;
        }

        // Build HTML for all files
        const html = files.map((audio, i) => {
            const index = i + 1;
            return `
                <div class="audio-item" data-filename="${escapeHtml(audio.filename)}" data-url="${escapeHtml(audio.url)}">
                    <div class="audio-item-header">
                        <span class="audio-item-date">${escapeHtml(audio.date)}</span>
                        <span class="text-muted">${escapeHtml(audio.time)}</span>
                        <span class="audio-item-size text-dim">${escapeHtml(audio.size)}</span>
                    </div>
                    <div class="audio-item-filename text-secondary text-sm">${escapeHtml(audio.filename)}</div>
                    <div class="waveform-container">
                        <div class="waveform" id="waveform-${index}"></div>
                        <div class="waveform-controls">
                            <button class="waveform-btn play-btn" data-index="${index}">▶</button>
                            <span class="waveform-time"><span class="current-time">0:00</span> / <span class="duration">0:00</span></span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;

        // Re-initialize waveforms after DOM update
        setTimeout(initAllWaveforms, 100);
    }

    /**
     * Escape HTML special characters.
     * 
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    function escapeHtml(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * Poll the server for audio file updates.
     */
    async function pollAudioFiles() {
        try {
            const response = await fetch(AUDIO_FILES_API);
            
            if (!response.ok) {
                console.warn(`[Pipeline] Audio files API returned ${response.status}`);
                return;
            }

            const data = await response.json();

            // Update count display
            const countEl = document.getElementById('audio-count');
            if (countEl) {
                countEl.textContent = `${data.count} file${data.count !== 1 ? 's' : ''}`;
            }

            // Rebuild list if count changed
            if (data.count !== lastAudioCount) {
                console.log(`[Pipeline] Audio count changed: ${lastAudioCount} -> ${data.count}`);
                lastAudioCount = data.count;
                rebuildAudioList(data.files);
            }

        } catch (error) {
            console.error('[Pipeline] Error polling audio files:', error);
        }
    }

    /**
     * Start polling for audio file updates.
     */
    function startPolling() {
        if (pollIntervalId !== null) {
            return; // Already polling
        }

        pollIntervalId = setInterval(pollAudioFiles, POLL_INTERVAL_MS);
        console.log(`[Pipeline] Started polling every ${POLL_INTERVAL_MS}ms`);
    }

    /**
     * Stop polling for audio file updates.
     */
    function stopPolling() {
        if (pollIntervalId !== null) {
            clearInterval(pollIntervalId);
            pollIntervalId = null;
            console.log('[Pipeline] Stopped polling');
        }
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the pipeline module.
     */
    function init() {
        console.log('[Pipeline] Initializing...');

        // Get initial count from page
        const audioItems = document.querySelectorAll('.audio-item[data-url]');
        lastAudioCount = audioItems.length;

        // Initialize existing waveforms
        initAllWaveforms();

        // Start polling for updates
        startPolling();

        // Clean up on page unload
        window.addEventListener('beforeunload', function() {
            stopPolling();
            destroyAllWaveforms();
        });

        console.log('[Pipeline] Initialization complete');
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
