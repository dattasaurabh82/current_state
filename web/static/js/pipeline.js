/**
 * Pipeline Visualization - WaveSurfer.js Integration
 * 
 * Handles audio waveform visualization and real-time file updates.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Store wavesurfer instances
    const wavesurfers = {};
    let currentlyPlaying = null;

    /**
     * Format time in M:SS format
     */
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds === Infinity) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Initialize WaveSurfer for a single audio item
     */
    function initWaveSurfer(index, url) {
        const container = document.getElementById(`waveform-${index}`);
        if (!container || wavesurfers[index]) return;

        const wavesurfer = WaveSurfer.create({
            container: container,
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

        // Load audio
        wavesurfer.load(url);

        // Get parent audio-item element
        const audioItem = container.closest('.audio-item');
        const playBtn = audioItem.querySelector('.play-btn');
        const currentTimeEl = audioItem.querySelector('.current-time');
        const durationEl = audioItem.querySelector('.duration');

        // Update duration when ready
        wavesurfer.on('ready', function() {
            durationEl.textContent = formatTime(wavesurfer.getDuration());
        });

        // Update current time during playback
        wavesurfer.on('audioprocess', function() {
            currentTimeEl.textContent = formatTime(wavesurfer.getCurrentTime());
        });

        // Handle play/pause button
        playBtn.addEventListener('click', function() {
            // Stop any other playing instance
            if (currentlyPlaying && currentlyPlaying !== index) {
                wavesurfers[currentlyPlaying].pause();
                const otherBtn = document.querySelector(`[data-index="${currentlyPlaying}"]`);
                if (otherBtn) otherBtn.textContent = '▶';
            }

            wavesurfer.playPause();
            
            if (wavesurfer.isPlaying()) {
                playBtn.textContent = '⏸';
                currentlyPlaying = index;
            } else {
                playBtn.textContent = '▶';
                currentlyPlaying = null;
            }
        });

        // Reset button when audio ends
        wavesurfer.on('finish', function() {
            playBtn.textContent = '▶';
            currentlyPlaying = null;
        });

        // Click on waveform to seek
        wavesurfer.on('seek', function() {
            currentTimeEl.textContent = formatTime(wavesurfer.getCurrentTime());
        });

        wavesurfers[index] = wavesurfer;
    }

    /**
     * Initialize all waveforms on the page
     */
    function initAllWaveforms() {
        const audioItems = document.querySelectorAll('.audio-item[data-url]');
        audioItems.forEach((item, i) => {
            const url = item.dataset.url;
            const index = i + 1; // 1-indexed to match template
            initWaveSurfer(index, url);
        });
    }

    /**
     * Rebuild audio list when files change
     */
    function rebuildAudioList(files) {
        // Destroy existing wavesurfers
        Object.values(wavesurfers).forEach(ws => ws.destroy());
        Object.keys(wavesurfers).forEach(key => delete wavesurfers[key]);
        currentlyPlaying = null;

        const container = document.getElementById('audio-files-container');
        
        if (files.length === 0) {
            container.innerHTML = '<p class="text-dim">No audio files found</p>';
            return;
        }

        let html = '';
        files.forEach((audio, i) => {
            const index = i + 1;
            html += `
                <div class="audio-item" data-filename="${audio.filename}" data-url="${audio.url}">
                    <div class="audio-item-header">
                        <span class="audio-item-date">${audio.date}</span>
                        <span class="text-muted">${audio.time}</span>
                        <span class="audio-item-size text-dim">${audio.size}</span>
                    </div>
                    <div class="audio-item-filename text-secondary text-sm">${audio.filename}</div>
                    <div class="waveform-container">
                        <div class="waveform" id="waveform-${index}"></div>
                        <div class="waveform-controls">
                            <button class="waveform-btn play-btn" data-index="${index}">▶</button>
                            <span class="waveform-time"><span class="current-time">0:00</span> / <span class="duration">0:00</span></span>
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;

        // Re-initialize waveforms
        setTimeout(initAllWaveforms, 100);
    }

    /**
     * Poll for audio file changes
     */
    async function pollAudioFiles() {
        try {
            const response = await fetch('/api/audio-files');
            const data = await response.json();

            // Update count display
            document.getElementById('audio-count').textContent = data.count + ' files';

            // If count changed, rebuild the list
            if (data.count !== window.lastAudioCount) {
                window.lastAudioCount = data.count;
                rebuildAudioList(data.files);
            }
        } catch (e) {
            console.error('[Pipeline] Error polling audio files:', e);
        }
    }

    // Initialize waveforms
    initAllWaveforms();

    // Start polling every 5 seconds
    setInterval(pollAudioFiles, 5000);
});
