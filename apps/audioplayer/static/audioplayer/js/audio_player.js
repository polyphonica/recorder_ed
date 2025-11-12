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
        } catch (error) {
            console.error(`Error loading audio file ${trackUrls[i]}:`, error);
        }
    }

    masterGainNodes[instance].gain.value = masterVolumeStates[instance];
}

/**
 * Play all tracks synchronized
 */
function playAll(instance) {
    stopAll(instance);

    activeAudioBufferSources[instance] = audioBuffers[instance].map((buffer, index) => {
        let source = audioContexts[instance].createBufferSource();
        source.buffer = buffer;
        source.connect(gainNodes[instance][index]);
        source.onended = () => {
            const playBtn = document.getElementById(`playButton${instance}`);
            if (playBtn) {
                playBtn.textContent = 'Play';
                playBtn.classList.remove('playing');
            }
        };
        source.start();
        return source;
    });
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
}

/**
 * Pause all tracks
 */
function pauseAll(instance) {
    if (audioContexts[instance].state === 'running') {
        audioContexts[instance].suspend();
    }
}

/**
 * Resume all tracks
 */
function resumeAll(instance) {
    if (audioContexts[instance].state === 'suspended') {
        audioContexts[instance].resume();
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
 * Load and initialize on page load
 */
window.onload = async () => {
    const lessonId = document.getElementById('lesson-id')?.value;
    const isPrivateLesson = document.getElementById('is-private-lesson')?.value === 'true';

    if (!lessonId) {
        console.error('No lesson ID found');
        return;
    }

    try {
        console.log("Fetching pieces for lesson:", lessonId, "Private lesson:", isPrivateLesson);
        // Use different URL pattern for private lessons vs course lessons
        const url = isPrivateLesson
            ? `/audioplayer/private-lesson/${lessonId}/pieces-json/`
            : `/audioplayer/lesson/${lessonId}/pieces-json/`;
        let response = await fetch(url);
        console.log("Response status:", response.status);

        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        let data = await response.json();
        console.log("Data:", data);

        if (data.pieces_data && data.pieces_data.length > 0) {
            initPlayers(data.pieces_data);
        } else {
            document.getElementById('players-container').innerHTML =
                '<p style="text-align: center; color: #666; padding: 40px;">No playalong pieces available for this lesson.</p>';
        }
    } catch (error) {
        console.error("Fetch error:", error);
        document.getElementById('players-container').innerHTML =
            '<p style="text-align: center; color: #c0392b; padding: 40px;">Error loading playalong pieces. Please try refreshing the page.</p>';
    }
};
