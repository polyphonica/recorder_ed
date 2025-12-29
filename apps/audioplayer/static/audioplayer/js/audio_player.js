// Audio Player for Multi-Track Playalong Pieces
// Uses Waveform Playlist v4 for synchronized multi-track playback

// Store playlist instances for each piece
let playlists = [];
let eventEmitters = [];

/**
 * Initialize all audio players for pieces in a lesson
 */
async function initPlayers(piecesData) {
    console.log("initPlayers called, piecesData:", piecesData);

    // Sort pieces by order
    piecesData.sort((a, b) => a.order - b.order);

    let playersContainer = document.getElementById('players-container');
    playersContainer.innerHTML = '';

    for (let pieceIndex = 0; pieceIndex < piecesData.length; pieceIndex++) {
        const piece = piecesData[pieceIndex];

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
        playButton.classList.add('button');
        playButton.textContent = 'Play';
        playButton.onclick = () => togglePlay(pieceIndex + 1, playButton);

        // Pause/Resume button
        let pauseButton = document.createElement('button');
        pauseButton.id = `pauseButton${pieceIndex + 1}`;
        pauseButton.classList.add('button');
        pauseButton.textContent = 'Pause';
        pauseButton.disabled = true;
        pauseButton.onclick = () => togglePause(pieceIndex + 1, pauseButton);

        // Seek control with time displays
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
        seekSlider.max = '1000';
        seekSlider.value = '0';
        seekSlider.classList.add('seek-slider');
        seekSlider.style.cssText = 'flex: 1;';

        // Seek on input
        seekSlider.oninput = (e) => {
            const instance = pieceIndex + 1;
            const position = (e.target.value / 1000); // 0 to 1
            if (eventEmitters[instance]) {
                eventEmitters[instance].emit('select', position * getDuration(instance), position * getDuration(instance));
            }
        };

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

        // Waveform container (hidden - we don't show waveforms but playlist needs a container)
        let playlistContainer = document.createElement('div');
        playlistContainer.id = `playlist${pieceIndex + 1}`;
        playlistContainer.style.display = 'none'; // Hide the waveform display

        // Tracks container for our custom UI
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
            muteButton.id = `muteButton${pieceIndex + 1}-${trackIndex}`;
            muteButton.classList.add('button');
            muteButton.textContent = 'Mute';
            muteButton.onclick = () => toggleMute(pieceIndex + 1, muteButton, trackIndex);

            let soloButton = document.createElement('button');
            soloButton.id = `soloButton${pieceIndex + 1}-${trackIndex}`;
            soloButton.classList.add('button');
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
        playerContainer.appendChild(playlistContainer);
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

        // Initialize waveform-playlist for this piece
        await initPlaylist(pieceIndex + 1, piece.stems);
    }
}

/**
 * Initialize waveform-playlist instance for a piece
 */
async function initPlaylist(instance, stems) {
    const container = document.getElementById(`playlist${instance}`);

    // Create playlist instance with minimal UI (we're using our own controls)
    playlists[instance] = WaveformPlaylist({
        container: container,
        samplesPerPixel: 4096,
        mono: true,
        waveHeight: 0, // Hide waveform
        controls: {
            show: false // Hide built-in controls
        },
        colors: {
            waveOutlineColor: 'transparent'
        },
        zoomLevels: [512, 1024, 2048, 4096]
    });

    // Get event emitter for control
    eventEmitters[instance] = playlists[instance].getEventEmitter();

    // Load tracks
    const tracks = stems.map(stem => ({
        src: stem.audio_file,
        name: stem.instrument_name,
        gain: 1.0
    }));

    try {
        await playlists[instance].load(tracks);
        console.log(`Playlist ${instance} loaded successfully`);

        // Setup event listeners for time updates
        setupTimeUpdateListener(instance);

        // Update total duration display
        const duration = getDuration(instance);
        const totalTimeEl = document.getElementById(`totalTime${instance}`);
        if (totalTimeEl && duration) {
            totalTimeEl.textContent = formatTime(duration);
        }
    } catch (error) {
        console.error(`Error loading playlist ${instance}:`, error);
    }
}

/**
 * Setup time update listener for progress display
 */
function setupTimeUpdateListener(instance) {
    if (!eventEmitters[instance]) return;

    eventEmitters[instance].on('timeupdate', (position) => {
        const currentTimeEl = document.getElementById(`currentTime${instance}`);
        const seekSlider = document.getElementById(`seekSlider${instance}`);
        const duration = getDuration(instance);

        if (currentTimeEl) {
            currentTimeEl.textContent = formatTime(position);
        }

        if (seekSlider && duration > 0) {
            seekSlider.value = (position / duration) * 1000;
        }
    });

    // Listen for play state changes
    eventEmitters[instance].on('play', () => {
        const pauseBtn = document.getElementById(`pauseButton${instance}`);
        if (pauseBtn) {
            pauseBtn.disabled = false;
            pauseBtn.textContent = 'Pause';
        }
    });

    eventEmitters[instance].on('pause', () => {
        const pauseBtn = document.getElementById(`pauseButton${instance}`);
        if (pauseBtn) {
            pauseBtn.textContent = 'Resume';
        }
    });

    eventEmitters[instance].on('stop', () => {
        const playBtn = document.getElementById(`playButton${instance}`);
        const pauseBtn = document.getElementById(`pauseButton${instance}`);

        if (playBtn) {
            playBtn.textContent = 'Play';
            playBtn.classList.remove('playing');
        }
        if (pauseBtn) {
            pauseBtn.disabled = true;
            pauseBtn.textContent = 'Pause';
        }
    });
}

/**
 * Get duration of playlist
 */
function getDuration(instance) {
    if (!playlists[instance]) return 0;
    const playlist = playlists[instance].getInfo();
    return playlist && playlist.duration ? playlist.duration : 0;
}

/**
 * Toggle play/stop
 */
function togglePlay(instance, button) {
    if (!eventEmitters[instance]) return;

    if (button.textContent === 'Play') {
        button.textContent = 'Stop';
        button.classList.add('playing');
        eventEmitters[instance].emit('play');
    } else {
        button.textContent = 'Play';
        button.classList.remove('playing');
        eventEmitters[instance].emit('stop');
    }
}

/**
 * Toggle pause/resume
 */
function togglePause(instance, button) {
    if (!eventEmitters[instance]) return;

    if (button.textContent === 'Pause') {
        eventEmitters[instance].emit('pause');
    } else {
        eventEmitters[instance].emit('play');
    }
}

/**
 * Toggle mute for a track
 */
function toggleMute(instance, button, trackIndex) {
    if (!eventEmitters[instance]) return;

    const isMuted = button.textContent === 'Unmute';
    button.textContent = isMuted ? 'Mute' : 'Unmute';

    eventEmitters[instance].emit('mute', trackIndex);
}

/**
 * Toggle solo for a track
 */
function toggleSolo(instance, button, trackIndex) {
    if (!eventEmitters[instance]) return;

    const isSoloed = button.textContent === 'Unsolo';
    button.textContent = isSoloed ? 'Solo' : 'Unsolo';

    eventEmitters[instance].emit('solo', trackIndex);
}

/**
 * Update volume for a track
 */
function updateVolume(instance, trackIndex, slider) {
    if (!eventEmitters[instance]) return;

    const volume = slider.value; // 0-100
    eventEmitters[instance].emit('volumechange', volume, trackIndex);
}

/**
 * Update master volume
 */
function updateMasterVolume(instance, slider) {
    if (!eventEmitters[instance]) return;

    const volume = slider.value; // 0-100
    eventEmitters[instance].emit('mastervolumechange', volume);
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
            await initPlayers(piecesData);
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
