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

// Seek control state variables
let startTimes = [];          // When playback started (audioContext time)
let currentOffsets = [];      // Current offset in the audio (seconds)
let durations = [];          // Duration of the audio (seconds)
let isPlaying = [];          // Is currently playing
let animationFrameIds = [];  // For updating progress bar
let pausedOffsets = [];       // Position where playback was paused

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

        // Seek control section
        let seekContainer = document.createElement('div');
        seekContainer.classList.add('seek-container');
        seekContainer.style.cssText = 'display: flex; align-items: center; gap: 10px; margin: 10px 0;';

        // Current time display
        let currentTimeDisplay = document.createElement('span');
        currentTimeDisplay.id = `currentTime${pieceIndex + 1}`;
        currentTimeDisplay.classList.add('time-display');
        currentTimeDisplay.textContent = '0:00';
        currentTimeDisplay.style.cssText = 'min-width: 45px; text-align: right; font-family: monospace;';

        // Seek slider
        let seekSlider = document.createElement('input');
        seekSlider.type = 'range';
        seekSlider.id = `seekSlider${pieceIndex + 1}`;
        seekSlider.min = '0';
        seekSlider.max = '100';
        seekSlider.value = '0';
        seekSlider.classList.add('seek-slider');
        seekSlider.style.cssText = 'flex: 1;';
        seekSlider.oninput = () => seekTo(pieceIndex + 1, seekSlider);

        // Total time display
        let totalTimeDisplay = document.createElement('span');
        totalTimeDisplay.id = `totalTime${pieceIndex + 1}`;
        totalTimeDisplay.classList.add('time-display');
        totalTimeDisplay.textContent = '0:00';
        totalTimeDisplay.style.cssText = 'min-width: 45px; font-family: monospace;';

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

    // Initialize seek control state
    startTimes[instance] = 0;
    currentOffsets[instance] = 0;
    durations[instance] = 0;
    isPlaying[instance] = false;
    animationFrameIds[instance] = null;
    pausedOffsets[instance] = 0;

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

            // Set duration from the first track (all tracks should be same length)
            if (i === 0) {
                durations[instance] = audioBuffer.duration;
                const totalTimeDisplay = document.getElementById(`totalTime${instance}`);
                if (totalTimeDisplay) {
                    totalTimeDisplay.textContent = formatTime(audioBuffer.duration);
                }
            }
        } catch (error) {
            console.error(`Error loading audio file ${trackUrls[i]}:`, error);
        }
    }

    masterGainNodes[instance].gain.value = masterVolumeStates[instance];
}

/**
 * Play all tracks synchronized from current offset
 */
function playAll(instance, offset = null) {
    stopAll(instance);

    // Use provided offset or current offset
    const startOffset = offset !== null ? offset : currentOffsets[instance];

    // Don't play if we're at the end
    if (startOffset >= durations[instance]) {
        currentOffsets[instance] = 0;
        updateSeekUI(instance);
        return;
    }

    startTimes[instance] = audioContexts[instance].currentTime;
    currentOffsets[instance] = startOffset;
    isPlaying[instance] = true;

    activeAudioBufferSources[instance] = audioBuffers[instance].map((buffer, index) => {
        let source = audioContexts[instance].createBufferSource();
        source.buffer = buffer;
        source.connect(gainNodes[instance][index]);
        source.onended = () => {
            // Only reset UI if this is the last track to finish
            if (index === audioBuffers[instance].length - 1) {
                isPlaying[instance] = false;
                currentOffsets[instance] = 0;
                const playBtn = document.getElementById(`playButton${instance}`);
                if (playBtn) {
                    playBtn.textContent = 'Play';
                    playBtn.classList.remove('playing');
                }
                updateSeekUI(instance);
            }
        };
        source.start(0, startOffset);
        return source;
    });

    // Start updating the progress bar
    updateProgressBar(instance);
}

/**
 * Stop all tracks
 */
function stopAll(instance) {
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
    isPlaying[instance] = false;
    currentOffsets[instance] = 0;

    // Cancel animation frame
    if (animationFrameIds[instance]) {
        cancelAnimationFrame(animationFrameIds[instance]);
        animationFrameIds[instance] = null;
    }

    // Reset seek UI
    updateSeekUI(instance);
}

/**
 * Pause all tracks
 */
function pauseAll(instance) {
    if (audioContexts[instance].state === 'running') {
        // Calculate and save current offset before pausing
        const elapsed = audioContexts[instance].currentTime - startTimes[instance];
        currentOffsets[instance] = currentOffsets[instance] + elapsed;
        pausedOffsets[instance] = currentOffsets[instance]; // Save where we paused

        audioContexts[instance].suspend();
        isPlaying[instance] = false;

        // Cancel animation frame
        if (animationFrameIds[instance]) {
            cancelAnimationFrame(animationFrameIds[instance]);
            animationFrameIds[instance] = null;
        }
    }
}

/**
 * Resume all tracks
 */
function resumeAll(instance) {
    if (audioContexts[instance].state === 'suspended') {
        // Check if user seeked while paused
        if (Math.abs(currentOffsets[instance] - pausedOffsets[instance]) > 0.1) {
            // Position changed during pause - need to restart from new position
            // Save the seek position before stopAll resets it
            const seekPosition = currentOffsets[instance];
            // Resume the context so we can properly stop sources
            audioContexts[instance].resume();
            // Stop current sources (this will reset currentOffsets to 0)
            stopAll(instance);
            // Restart from the saved seek position
            playAll(instance, seekPosition);
        } else {
            // No seek during pause - just resume
            startTimes[instance] = audioContexts[instance].currentTime;
            audioContexts[instance].resume();
            isPlaying[instance] = true;

            // Resume progress bar updates
            updateProgressBar(instance);
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
 * Seek to a specific position in the audio
 */
function seekTo(instance, slider) {
    const seekPercentage = slider.value / 100;
    const newOffset = seekPercentage * durations[instance];

    if (isPlaying[instance]) {
        // If currently playing, restart from new position
        playAll(instance, newOffset);
        // Update the play button state
        const playBtn = document.getElementById(`playButton${instance}`);
        if (playBtn) {
            playBtn.textContent = 'Stop';
            playBtn.classList.add('playing');
        }
    } else {
        // If not playing, just update the offset
        currentOffsets[instance] = newOffset;
        updateSeekUI(instance);
    }
}

/**
 * Update the seek slider and time displays
 */
function updateSeekUI(instance) {
    const currentTime = currentOffsets[instance];
    const seekSlider = document.getElementById(`seekSlider${instance}`);
    const currentTimeDisplay = document.getElementById(`currentTime${instance}`);

    if (seekSlider && durations[instance] > 0) {
        seekSlider.value = (currentTime / durations[instance]) * 100;
    }

    if (currentTimeDisplay) {
        currentTimeDisplay.textContent = formatTime(currentTime);
    }
}

/**
 * Update progress bar during playback
 */
function updateProgressBar(instance) {
    if (!isPlaying[instance]) return;

    // Calculate current position
    const elapsed = audioContexts[instance].currentTime - startTimes[instance];
    const currentTime = currentOffsets[instance] + elapsed;

    // Check if we've reached the end
    if (currentTime >= durations[instance]) {
        isPlaying[instance] = false;
        currentOffsets[instance] = 0;
        updateSeekUI(instance);
        return;
    }

    // Update temporary offset for display
    const tempOffset = currentOffsets[instance];
    currentOffsets[instance] = currentTime;
    updateSeekUI(instance);
    currentOffsets[instance] = tempOffset;

    // Continue updating
    animationFrameIds[instance] = requestAnimationFrame(() => updateProgressBar(instance));
}

/**
 * Format time in seconds to MM:SS format
 */
function formatTime(seconds) {
    if (!isFinite(seconds)) return '0:00';

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
