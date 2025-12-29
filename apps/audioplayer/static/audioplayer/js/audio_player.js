// Audio Player for Multi-Track Playalong Pieces
// Uses Web Audio API for synchronized playback with individual track controls

let audioContexts = [];
let gainNodes = [];
let masterGainNodes = [];
let audioBuffers = [];
let sources = [];
let soloStates = [];
let muteStates = [];
let volumeStates = [];
let masterVolumeStates = [];
let activeAudioBufferSources = [];

// Playback state for seek control
let playbackStartTime = [];    // audioContext.currentTime when playback started
let playbackOffset = [];        // offset in seconds where playback started from
let duration = [];              // total duration of audio
let isPaused = [];              // whether playback is currently paused
let pausedPosition = [];        // position where pause occurred (to detect seeks)
let animationFrameId = [];      // requestAnimationFrame ID for progress updates
let isDragging = [];            // whether user is currently dragging the seek slider

/**
 * Initialize all audio players for pieces in a lesson
 */
async function initPlayers(piecesData) {
    console.log("initPlayers called, piecesData:", piecesData);

    // Sort pieces by order
    piecesData.sort((a, b) => a.order - b.order);

    let playersContainer = document.getElementById('players-container');
    playersContainer.innerHTML = '';

    piecesData.forEach((piece, pieceIndex) => {
        // Add horizontal divider between pieces
        if (pieceIndex > 0) {
            let hr = document.createElement('hr');
            hr.classList.add('piece-divider');
            playersContainer.appendChild(hr);
        }

        // Create player container
        let playerContainer = document.createElement('div');
        playerContainer.classList.add('player-container');

        // Piece title with optional badge
        let pieceTitle = document.createElement('h2');
        pieceTitle.classList.add('piece-title');
        pieceTitle.textContent = piece.title;
        if (piece.is_optional) {
            let optionalBadge = document.createElement('span');
            optionalBadge.classList.add('optional-badge');
            optionalBadge.textContent = 'OPTIONAL';
            pieceTitle.appendChild(optionalBadge);
        }
        playerContainer.appendChild(pieceTitle);

        // Piece description if provided
        if (piece.description) {
            let description = document.createElement('div');
            description.classList.add('piece-description');
            description.textContent = piece.description;
            playerContainer.appendChild(description);
        }

        // Custom instructions if provided
        if (piece.instructions) {
            let instructions = document.createElement('div');
            instructions.classList.add('piece-instructions');
            instructions.textContent = piece.instructions;
            playerContainer.appendChild(instructions);
        }

        // Controls section
        let controls = document.createElement('div');
        controls.classList.add('controls');
        controls.id = `controls${pieceIndex + 1}`;

        // Play/Stop button
        let playButton = document.createElement('button');
        playButton.id = `playButton${pieceIndex + 1}`;
        playButton.classList.add('button', 'off');
        playButton.textContent = 'Play';
        playButton.onclick = () => togglePlay(pieceIndex + 1, playButton);

        // Pause/Resume button
        let pauseButton = document.createElement('button');
        pauseButton.id = `pauseButton${pieceIndex + 1}`;
        pauseButton.classList.add('button', 'off');
        pauseButton.textContent = 'Pause';
        pauseButton.onclick = () => togglePause(pieceIndex + 1, pauseButton);

        // Seek control
        let seekContainer = document.createElement('div');
        seekContainer.classList.add('seek-container');
        seekContainer.style.cssText = 'display: flex; align-items: center; gap: 10px; margin: 10px 0; padding: 10px; background: #fff; border: 1px solid #e0e0e0; border-radius: 6px;';

        let currentTimeDisplay = document.createElement('span');
        currentTimeDisplay.id = `currentTime${pieceIndex + 1}`;
        currentTimeDisplay.textContent = '0:00';
        currentTimeDisplay.style.cssText = 'min-width: 45px; text-align: right; font-family: monospace; font-size: 13px;';

        let seekSlider = document.createElement('input');
        seekSlider.type = 'range';
        seekSlider.id = `seekSlider${pieceIndex + 1}`;
        seekSlider.min = '0';
        seekSlider.max = '1000';  // Use 1000 steps for smooth seeking
        seekSlider.value = '0';
        seekSlider.classList.add('seek-slider');
        seekSlider.style.cssText = 'flex: 1;';

        // Handle dragging - visual feedback only
        seekSlider.addEventListener('mousedown', () => {
            isDragging[pieceIndex + 1] = true;
        });
        seekSlider.addEventListener('touchstart', () => {
            isDragging[pieceIndex + 1] = true;
        });

        // Update time display while dragging
        seekSlider.oninput = () => {
            if (isDragging[pieceIndex + 1]) {
                const previewTime = (seekSlider.value / 1000) * duration[pieceIndex + 1];
                const currentTimeDisplay = document.getElementById(`currentTime${pieceIndex + 1}`);
                if (currentTimeDisplay) {
                    currentTimeDisplay.textContent = formatTime(previewTime);
                }
            }
        };

        // Actually perform seek when released
        seekSlider.onchange = () => {
            isDragging[pieceIndex + 1] = false;
            handleSeek(pieceIndex + 1, seekSlider.value);
        };

        // Also handle mouse/touch release outside slider
        document.addEventListener('mouseup', () => {
            if (isDragging[pieceIndex + 1]) {
                isDragging[pieceIndex + 1] = false;
            }
        });
        document.addEventListener('touchend', () => {
            if (isDragging[pieceIndex + 1]) {
                isDragging[pieceIndex + 1] = false;
            }
        });

        let totalTimeDisplay = document.createElement('span');
        totalTimeDisplay.id = `totalTime${pieceIndex + 1}`;
        totalTimeDisplay.textContent = '0:00';
        totalTimeDisplay.style.cssText = 'min-width: 45px; font-family: monospace; font-size: 13px;';

        seekContainer.appendChild(currentTimeDisplay);
        seekContainer.appendChild(seekSlider);
        seekContainer.appendChild(totalTimeDisplay);

        // Master volume control
        let masterVolumeSlider = document.createElement('input');
        masterVolumeSlider.type = 'range';
        masterVolumeSlider.min = '0';
        masterVolumeSlider.max = '100';
        masterVolumeSlider.value = '100';
        masterVolumeSlider.classList.add('master-volume-slider');
        masterVolumeSlider.oninput = () => updateMasterVolume(pieceIndex + 1, masterVolumeSlider);

        let masterVolumeLabel = document.createElement('div');
        masterVolumeLabel.textContent = 'Master Volume';
        masterVolumeLabel.classList.add('master-volume-label');

        controls.appendChild(playButton);
        controls.appendChild(pauseButton);
        controls.appendChild(seekContainer);
        controls.appendChild(masterVolumeLabel);
        controls.appendChild(masterVolumeSlider);

        // Tracks container
        let tracksContainer = document.createElement('div');
        tracksContainer.id = `tracks${pieceIndex + 1}`;

        // Create controls for each stem/track
        piece.stems.forEach((stem, trackIndex) => {
            let trackColumn = document.createElement('div');
            trackColumn.classList.add('track-column');

            let trackTitle = document.createElement('div');
            trackTitle.classList.add('track-title');
            trackTitle.textContent = stem.instrument_name;

            let muteButton = document.createElement('button');
            muteButton.classList.add('button', 'off');
            muteButton.textContent = 'Mute';
            muteButton.onclick = () => toggleMute(pieceIndex + 1, muteButton, trackIndex);

            let soloButton = document.createElement('button');
            soloButton.id = `soloButton${pieceIndex + 1}-${trackIndex}`;
            soloButton.classList.add('button', 'off');
            soloButton.textContent = 'Solo';
            soloButton.onclick = () => toggleSolo(pieceIndex + 1, soloButton, trackIndex);

            let volumeSlider = document.createElement('input');
            volumeSlider.type = 'range';
            volumeSlider.min = '0';
            volumeSlider.max = '100';
            volumeSlider.value = '100';
            volumeSlider.classList.add('volume-slider');
            volumeSlider.oninput = () => updateVolume(pieceIndex + 1, trackIndex, volumeSlider);

            let volumeLabel = document.createElement('div');
            volumeLabel.textContent = 'Volume';
            volumeLabel.classList.add('volume-label');

            trackColumn.appendChild(trackTitle);
            trackColumn.appendChild(muteButton);
            trackColumn.appendChild(soloButton);
            trackColumn.appendChild(volumeLabel);
            trackColumn.appendChild(volumeSlider);

            tracksContainer.appendChild(trackColumn);
        });

        playerContainer.appendChild(controls);
        playerContainer.appendChild(tracksContainer);

        // Add sheet music image if available
        if (piece.svg_image) {
            let svgImage = document.createElement('img');
            svgImage.src = piece.svg_image;
            svgImage.classList.add('svg-image');
            svgImage.alt = `Sheet music for ${piece.title}`;
            playerContainer.appendChild(svgImage);
        }

        // Add PDF download button if available
        if (piece.pdf_score) {
            let pdfContainer = document.createElement('div');
            pdfContainer.classList.add('pdf-download-container');
            pdfContainer.style.textAlign = 'center';
            pdfContainer.style.marginTop = '20px';

            let pdfLink = document.createElement('a');
            pdfLink.href = piece.pdf_score;
            pdfLink.target = '_blank';
            pdfLink.download = '';
            pdfLink.classList.add('btn', 'btn-primary', 'btn-outline');

            let pdfIcon = document.createElement('i');
            pdfIcon.classList.add('fas', 'fa-file-pdf');
            pdfIcon.style.marginRight = '8px';

            let pdfText = document.createTextNode(
                piece.pdf_score_title || 'Download Printable Score (PDF)'
            );

            pdfLink.appendChild(pdfIcon);
            pdfLink.appendChild(pdfText);
            pdfContainer.appendChild(pdfLink);
            playerContainer.appendChild(pdfContainer);
        }

        playersContainer.appendChild(playerContainer);

        // Initialize audio context and load audio files
        init(pieceIndex + 1, piece.stems.map(stem => stem.audio_file));
    });
}

/**
 * Toggle play/stop
 */
function togglePlay(instance, button) {
    if (button.textContent === 'Play') {
        button.textContent = 'Stop';
        button.classList.add('playing');
        playAll(instance);
    } else {
        button.textContent = 'Play';
        button.classList.remove('playing');
        stopAll(instance);
    }
}

/**
 * Toggle pause/resume
 */
function togglePause(instance, button) {
    if (button.textContent === 'Pause') {
        button.textContent = 'Resume';
        pauseAll(instance);
    } else {
        button.textContent = 'Pause';
        resumeAll(instance);
    }
}

/**
 * Toggle mute for a track
 */
function toggleMute(instance, button, trackIndex) {
    let isMuted = muteStates[instance][trackIndex];
    muteStates[instance][trackIndex] = !isMuted;
    button.textContent = isMuted ? 'Mute' : 'Unmute';
    updateGain(instance, trackIndex);
}

/**
 * Toggle solo for a track
 */
function toggleSolo(instance, button, trackIndex) {
    let isSoloed = soloStates[instance][trackIndex];
    soloStates[instance][trackIndex] = !isSoloed;
    button.textContent = isSoloed ? 'Solo' : 'Unsolo';
    updateSolo(instance);
}

/**
 * Update volume for a track
 */
function updateVolume(instance, trackIndex, slider) {
    volumeStates[instance][trackIndex] = slider.value / 100;
    updateGain(instance, trackIndex);
}

/**
 * Update master volume
 */
function updateMasterVolume(instance, slider) {
    masterVolumeStates[instance] = slider.value / 100;
    masterGainNodes[instance].gain.value = masterVolumeStates[instance];
}

/**
 * Initialize audio context and load audio files
 */
async function init(instance, trackUrls) {
    audioContexts[instance] = new (window.AudioContext || window.webkitAudioContext)();
    gainNodes[instance] = [];
    masterGainNodes[instance] = audioContexts[instance].createGain();
    masterGainNodes[instance].connect(audioContexts[instance].destination);
    masterVolumeStates[instance] = 1.0;

    audioBuffers[instance] = [];
    sources[instance] = [];
    soloStates[instance] = [];
    muteStates[instance] = [];
    volumeStates[instance] = [];
    activeAudioBufferSources[instance] = [];

    // Initialize playback state
    playbackStartTime[instance] = 0;
    playbackOffset[instance] = 0;
    duration[instance] = 0;
    isPaused[instance] = false;
    pausedPosition[instance] = 0;
    animationFrameId[instance] = null;
    isDragging[instance] = false;

    for (let i = 0; i < trackUrls.length; i++) {
        soloStates[instance][i] = false;
        muteStates[instance][i] = false;
        volumeStates[instance][i] = 1.0;

        try {
            let response = await fetch(trackUrls[i]);
            let arrayBuffer = await response.arrayBuffer();
            let audioBuffer = await audioContexts[instance].decodeAudioData(arrayBuffer);

            audioBuffers[instance][i] = audioBuffer;
            gainNodes[instance][i] = audioContexts[instance].createGain();
            gainNodes[instance][i].connect(masterGainNodes[instance]);
            gainNodes[instance][i].gain.value = volumeStates[instance][i];

            // Set duration from first track (all tracks should be same length)
            if (i === 0) {
                duration[instance] = audioBuffer.duration;
                const totalTimeEl = document.getElementById(`totalTime${instance}`);
                if (totalTimeEl) {
                    totalTimeEl.textContent = formatTime(audioBuffer.duration);
                }
            }
        } catch (error) {
            console.error(`Error loading audio file ${trackUrls[i]}:`, error);
        }
    }

    masterGainNodes[instance].gain.value = masterVolumeStates[instance];
}

/**
 * Play all tracks synchronized from a specific offset
 */
function playAll(instance, offset = 0) {
    // Stop any existing playback
    stopAllSources(instance);

    // Set playback state
    playbackOffset[instance] = offset;
    playbackStartTime[instance] = audioContexts[instance].currentTime;
    isPaused[instance] = false;

    // Create and start buffer sources from the offset
    activeAudioBufferSources[instance] = audioBuffers[instance].map((buffer, index) => {
        let source = audioContexts[instance].createBufferSource();
        source.buffer = buffer;
        source.connect(gainNodes[instance][index]);
        source.onended = () => {
            // When playback ends naturally
            if (index === 0) {  // Only handle once (first track)
                playbackOffset[instance] = 0;
                isPaused[instance] = false;
                updateProgressUI(instance);
                const playBtn = document.getElementById(`playButton${instance}`);
                if (playBtn) {
                    playBtn.textContent = 'Play';
                    playBtn.classList.remove('playing');
                }
            }
        };
        source.start(0, offset);
        return source;
    });

    // Start updating progress display
    updateProgress(instance);
}

/**
 * Stop playback and reset to beginning
 */
function stopAll(instance) {
    // Resume context first if suspended (to allow clean stop)
    if (audioContexts[instance].state === 'suspended') {
        audioContexts[instance].resume();
    }

    stopAllSources(instance);
    playbackOffset[instance] = 0;
    pausedPosition[instance] = 0;
    isPaused[instance] = false;
    updateProgressUI(instance);
}

/**
 * Stop all audio buffer sources without changing state
 */
function stopAllSources(instance) {
    // Cancel progress updates
    if (animationFrameId[instance]) {
        cancelAnimationFrame(animationFrameId[instance]);
        animationFrameId[instance] = null;
    }

    // Stop all sources
    if (activeAudioBufferSources[instance]) {
        activeAudioBufferSources[instance].forEach(source => {
            try {
                source.stop();
            } catch (e) {
                // Already stopped
            }
        });
    }
    activeAudioBufferSources[instance] = [];
}

/**
 * Pause playback
 */
function pauseAll(instance) {
    if (audioContexts[instance].state === 'running' && !isPaused[instance]) {
        // Calculate current position before pausing
        const elapsed = audioContexts[instance].currentTime - playbackStartTime[instance];
        playbackOffset[instance] = playbackOffset[instance] + elapsed;
        pausedPosition[instance] = playbackOffset[instance]; // Remember where we paused

        // Suspend audio context
        audioContexts[instance].suspend();
        isPaused[instance] = true;

        // Stop progress updates
        if (animationFrameId[instance]) {
            cancelAnimationFrame(animationFrameId[instance]);
            animationFrameId[instance] = null;
        }

        // Update UI to show paused position
        updateProgressUI(instance);
    }
}

/**
 * Resume playback
 */
function resumeAll(instance) {
    if (audioContexts[instance].state === 'suspended' && isPaused[instance]) {
        // Check if user seeked while paused
        if (Math.abs(playbackOffset[instance] - pausedPosition[instance]) > 0.1) {
            // Position changed - need to restart playback from new position
            // Wait for context to resume before starting playback
            audioContexts[instance].resume().then(() => {
                isPaused[instance] = false;
                playAll(instance, playbackOffset[instance]); // Restart from new position

                // Ensure Play button shows correct state
                const playBtn = document.getElementById(`playButton${instance}`);
                if (playBtn) {
                    playBtn.textContent = 'Stop';
                    playBtn.classList.add('playing');
                }
            });
        } else {
            // No seek - just resume normally
            audioContexts[instance].resume().then(() => {
                playbackStartTime[instance] = audioContexts[instance].currentTime;
                isPaused[instance] = false;

                // Restart progress updates
                updateProgress(instance);
            });
        }
    }
}

/**
 * Update gain for a specific track
 */
function updateGain(instance, trackIndex) {
    let gainValue = muteStates[instance][trackIndex] ? 0 : volumeStates[instance][trackIndex];

    // Check if any track is soloed
    let isAnySoloed = soloStates[instance].some(solo => solo);
    if (isAnySoloed && !soloStates[instance][trackIndex]) {
        gainValue = 0;
    }

    gainNodes[instance][trackIndex].gain.value = gainValue;
}

/**
 * Update solo states for all tracks
 */
function updateSolo(instance) {
    let isAnySoloed = soloStates[instance].some(solo => solo);

    gainNodes[instance].forEach((gainNode, index) => {
        let gainValue = (isAnySoloed && !soloStates[instance][index]) ? 0 :
                        (muteStates[instance][index] ? 0 : volumeStates[instance][index]);
        gainNode.gain.value = gainValue;
    });
}

/**
 * Get current playback position in seconds
 */
function getCurrentPosition(instance) {
    if (isPaused[instance]) {
        return playbackOffset[instance];
    }
    const elapsed = audioContexts[instance].currentTime - playbackStartTime[instance];
    return playbackOffset[instance] + elapsed;
}

/**
 * Handle seek slider input
 */
function handleSeek(instance, sliderValue) {
    // Immediately cancel any pending progress updates to prevent race condition
    if (animationFrameId[instance]) {
        cancelAnimationFrame(animationFrameId[instance]);
        animationFrameId[instance] = null;
    }

    const seekPosition = (sliderValue / 1000) * duration[instance];

    if (isPaused[instance]) {
        // Just update the offset if paused
        playbackOffset[instance] = seekPosition;
        updateProgressUI(instance);
    } else {
        // Restart playback from new position if playing
        playAll(instance, seekPosition);
        // Make sure Play button still shows "Stop"
        const playBtn = document.getElementById(`playButton${instance}`);
        if (playBtn) {
            playBtn.textContent = 'Stop';
            playBtn.classList.add('playing');
        }
    }
}

/**
 * Update progress bar and time display
 */
function updateProgress(instance) {
    if (isPaused[instance]) return;

    const currentPos = getCurrentPosition(instance);

    // Check if we've reached the end
    if (currentPos >= duration[instance]) {
        stopAll(instance);
        const playBtn = document.getElementById(`playButton${instance}`);
        if (playBtn) {
            playBtn.textContent = 'Play';
            playBtn.classList.remove('playing');
        }
        return;
    }

    // Update UI
    updateProgressUI(instance, currentPos);

    // Schedule next update
    animationFrameId[instance] = requestAnimationFrame(() => updateProgress(instance));
}

/**
 * Update the progress UI elements
 */
function updateProgressUI(instance, position = null) {
    const pos = position !== null ? position : getCurrentPosition(instance);

    const seekSlider = document.getElementById(`seekSlider${instance}`);
    const currentTimeDisplay = document.getElementById(`currentTime${instance}`);

    // Don't update slider position if user is dragging it
    if (seekSlider && duration[instance] > 0 && !isDragging[instance]) {
        seekSlider.value = (pos / duration[instance]) * 1000;
    }

    // Don't update time display if user is dragging (they see preview time)
    if (currentTimeDisplay && !isDragging[instance]) {
        currentTimeDisplay.textContent = formatTime(pos);
    }
}

/**
 * Format time in seconds to MM:SS
 */
function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Load and initialize on page load
 */
window.onload = async () => {
    const lessonId = document.getElementById('lesson-id')?.value;
    const isPrivateLesson = document.getElementById('is-private-lesson')?.value === 'true';
    const pieceId = document.getElementById('piece-id')?.value;
    const isLibraryPlayer = document.getElementById('is-library-player')?.value === 'true';

    // Determine which mode we're in and construct the appropriate URL
    let url;
    if (isLibraryPlayer && pieceId) {
        console.log("Fetching piece from library:", pieceId);
        url = `/audioplayer/library/piece/${pieceId}/pieces-json/`;
    } else if (lessonId) {
        console.log("Fetching pieces for lesson:", lessonId, "Private lesson:", isPrivateLesson);
        // Use different URL pattern for private lessons vs course lessons
        url = isPrivateLesson
            ? `/audioplayer/private-lesson/${lessonId}/pieces-json/`
            : `/audioplayer/lesson/${lessonId}/pieces-json/`;
    } else {
        console.error('No lesson ID or piece ID found');
        return;
    }

    try {
        let response = await fetch(url);
        console.log("Response status:", response.status);

        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        let data = await response.json();
        console.log("Data:", data);

        // Handle both lesson data format and library piece format
        const piecesData = data.pieces_data || data.pieces;

        if (piecesData && piecesData.length > 0) {
            initPlayers(piecesData);
        } else {
            document.getElementById('players-container').innerHTML =
                '<p style="text-align: center; color: #666; padding: 40px;">No playalong pieces available.</p>';
        }
    } catch (error) {
        console.error("Fetch error:", error);
        document.getElementById('players-container').innerHTML =
            '<p style="text-align: center; color: #c0392b; padding: 40px;">Error loading playalong pieces. Please try refreshing the page.</p>';
    }
};
