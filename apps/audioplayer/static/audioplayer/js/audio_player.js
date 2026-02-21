// Audio Player for Multi-Track Playalong Pieces
// Uses Waveform Playlist v4 for synchronized multi-track playback

// Store playlist instances for each piece
let playlists = [];
let eventEmitters = [];
let durations = []; // Store duration for each piece
let isPlaying = []; // Track playback state for each piece
let lastPositions = []; // Track last known position for end detection
let endCheckTimers = []; // Timers for checking if playback ended

// Lazy-loading state: playlists are only initialized when the user clicks Play
let stemsData = [];          // Stores stem definitions per instance for deferred loading
let activeInstance = null;    // Which instance currently has a loaded playlist (or null)
let isInitializing = false;  // Guard against double-init during async load

/**
 * Initialize all audio players for pieces in a lesson (legacy function for backwards compatibility)
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

        await createPiecePlayer(piece, pieceIndex, playersContainer, false);
    }
}

/**
 * Initialize waveform-playlist instance for a piece
 */
async function initPlaylist(instance, stems) {
    const container = document.getElementById(`playlist${instance}`);

    // WaveformPlaylist is exported as an ES module, so we need to access .default
    const PlaylistConstructor = WaveformPlaylist.default || WaveformPlaylist;

    // Create playlist instance with minimal UI (we're using our own controls)
    playlists[instance] = PlaylistConstructor({
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

        // Get duration from the actual audio buffers (most accurate).
        // The playlist-level .duration includes timeline padding, so we
        // prefer the longest track's buffer duration instead.
        durations[instance] = 0;
        if (playlists[instance].tracks && playlists[instance].tracks.length > 0) {
            let maxBufferDuration = 0;
            playlists[instance].tracks.forEach(track => {
                if (track.buffer && track.buffer.duration) {
                    maxBufferDuration = Math.max(maxBufferDuration, track.buffer.duration);
                }
            });
            if (maxBufferDuration > 0) {
                durations[instance] = maxBufferDuration;
            }
        }

        // Fallback to playlist-level duration if buffers weren't available
        if (!durations[instance] && playlists[instance].duration) {
            durations[instance] = playlists[instance].duration;
        }

        // Setup event listeners for time updates
        setupTimeUpdateListener(instance);

        // Update total duration display
        const totalTimeEl = document.getElementById(`totalTime${instance}`);
        if (totalTimeEl && durations[instance]) {
            totalTimeEl.textContent = formatTime(durations[instance]);
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

        // If duration not yet set, get it from the audio buffers
        if (!durations[instance] || durations[instance] === 0) {
            if (playlists[instance] && playlists[instance].tracks) {
                let maxBufferDuration = 0;
                playlists[instance].tracks.forEach(track => {
                    if (track.buffer && track.buffer.duration) {
                        maxBufferDuration = Math.max(maxBufferDuration, track.buffer.duration);
                    }
                });
                if (maxBufferDuration > 0) {
                    durations[instance] = maxBufferDuration;
                    const totalTimeEl = document.getElementById(`totalTime${instance}`);
                    if (totalTimeEl) {
                        totalTimeEl.textContent = formatTime(durations[instance]);
                    }
                }
            }
        }

        const duration = getDuration(instance);

        if (currentTimeEl) {
            currentTimeEl.textContent = formatTime(position);
        }

        if (seekSlider && duration > 0) {
            const newValue = (position / duration) * 1000;
            seekSlider.value = newValue;
        }

        // Detect when playback reaches the end
        if (isPlaying[instance] && duration > 0 && position >= duration - 0.1) {
            // Playback has reached the end - reset UI
            resetPlayerUI(instance);
        }
    });

    // Listen for play state changes
    eventEmitters[instance].on('play', () => {
        isPlaying[instance] = true;
        lastPositions[instance] = -1;
        const pauseBtn = document.getElementById(`pauseButton${instance}`);
        if (pauseBtn) {
            pauseBtn.disabled = false;
            pauseBtn.textContent = 'Pause';
        }

        // Start watchdog timer to detect when playback ends
        startEndDetectionTimer(instance);
    });

    eventEmitters[instance].on('pause', () => {
        const pauseBtn = document.getElementById(`pauseButton${instance}`);
        if (pauseBtn) {
            pauseBtn.textContent = 'Resume';
        }
    });

    eventEmitters[instance].on('stop', () => {
        isPlaying[instance] = false;
        stopEndDetectionTimer(instance);

        const playBtn = document.getElementById(`playButton${instance}`);
        const pauseBtn = document.getElementById(`pauseButton${instance}`);
        const seekSlider = document.getElementById(`seekSlider${instance}`);
        const currentTimeEl = document.getElementById(`currentTime${instance}`);

        if (playBtn) {
            playBtn.textContent = 'Play';
            playBtn.classList.remove('playing');
        }
        if (pauseBtn) {
            pauseBtn.disabled = true;
            pauseBtn.textContent = 'Pause';
        }
        // Reset seek slider and time to beginning
        if (seekSlider) {
            seekSlider.value = 0;
        }
        if (currentTimeEl) {
            currentTimeEl.textContent = '0:00';
        }
    });

    // Handle audio finishing naturally (backup listener if 'finished' event fires)
    eventEmitters[instance].on('finished', () => {
        if (isPlaying[instance]) {
            resetPlayerUI(instance);
        }
    });
}

/**
 * Get duration of playlist
 */
function getDuration(instance) {
    return durations[instance] || 0;
}

/**
 * Reset player UI to initial state (for when playback ends)
 */
function resetPlayerUI(instance) {
    if (!isPlaying[instance]) return; // Already reset

    isPlaying[instance] = false;
    stopEndDetectionTimer(instance);

    const playBtn = document.getElementById(`playButton${instance}`);
    const pauseBtn = document.getElementById(`pauseButton${instance}`);
    const seekSlider = document.getElementById(`seekSlider${instance}`);
    const currentTimeEl = document.getElementById(`currentTime${instance}`);

    if (playBtn) {
        playBtn.textContent = 'Play';
        playBtn.classList.remove('playing');
    }
    if (pauseBtn) {
        pauseBtn.disabled = true;
        pauseBtn.textContent = 'Pause';
    }
    if (seekSlider) {
        seekSlider.value = 0;
    }
    if (currentTimeEl) {
        currentTimeEl.textContent = '0:00';
    }

    // Stop immediately to prevent the library from looping
    if (eventEmitters[instance]) {
        eventEmitters[instance].emit('stop');
    }

    // Reset cursor to beginning after stop has been processed
    setTimeout(() => {
        if (eventEmitters[instance] && !isPlaying[instance]) {
            eventEmitters[instance].emit('select', 0, 0);
        }
    }, 100);
}

/**
 * Start a timer to periodically check if playback has ended
 */
function startEndDetectionTimer(instance) {
    stopEndDetectionTimer(instance); // Clear any existing timer

    endCheckTimers[instance] = setInterval(() => {
        if (!isPlaying[instance]) {
            stopEndDetectionTimer(instance);
            return;
        }

        const duration = getDuration(instance);
        if (duration <= 0) return;

        // Get current position from the seek slider value
        const seekSlider = document.getElementById(`seekSlider${instance}`);
        if (!seekSlider) return;

        const currentPosition = (seekSlider.value / 1000) * duration;

        // Check if position has stopped advancing and we're near the end
        if (lastPositions[instance] !== undefined && lastPositions[instance] >= 0) {
            const positionDelta = Math.abs(currentPosition - lastPositions[instance]);
            const nearEnd = currentPosition >= duration - 0.5;

            // If position hasn't changed much and we're near the end, playback finished
            if (positionDelta < 0.1 && nearEnd) {
                console.log(`Playback ended for instance ${instance} at position ${currentPosition}/${duration}`);
                resetPlayerUI(instance);
                return;
            }
        }

        lastPositions[instance] = currentPosition;
    }, 250); // Check every 250ms
}

/**
 * Stop the end detection timer
 */
function stopEndDetectionTimer(instance) {
    if (endCheckTimers[instance]) {
        clearInterval(endCheckTimers[instance]);
        endCheckTimers[instance] = null;
    }
}

/**
 * Destroy a playlist instance to free AudioContext and memory.
 * Only one playlist should be loaded at a time to avoid browser limits.
 */
function destroyPlaylist(instance) {
    if (!playlists[instance]) return;

    // Stop any active playback
    if (isPlaying[instance] && eventEmitters[instance]) {
        try {
            eventEmitters[instance].emit('stop');
        } catch (e) {
            console.warn(`Error stopping playlist ${instance}:`, e);
        }
    }

    // Stop end detection timer
    stopEndDetectionTimer(instance);

    // Disconnect audio nodes from each track's playout
    if (playlists[instance].tracks) {
        playlists[instance].tracks.forEach(track => {
            if (track.playout) {
                try {
                    if (track.playout.masterGain) track.playout.masterGain.disconnect();
                    if (track.playout.volumeGain) track.playout.volumeGain.disconnect();
                } catch (e) { /* already disconnected */ }
            }
        });
    }

    // Close the AudioContext (library stores it as .ac)
    if (playlists[instance].ac && playlists[instance].ac.state !== 'closed') {
        try {
            playlists[instance].ac.close();
        } catch (e) {
            console.warn(`Error closing AudioContext for instance ${instance}:`, e);
        }
    }

    // Clear the hidden playlist container DOM
    const container = document.getElementById(`playlist${instance}`);
    if (container) {
        container.innerHTML = '';
    }

    // Null out state for this instance to allow garbage collection
    playlists[instance] = null;
    eventEmitters[instance] = null;
    durations[instance] = 0;
    isPlaying[instance] = false;
    lastPositions[instance] = 0;

    // Reset UI to initial state
    const playBtn = document.getElementById(`playButton${instance}`);
    const pauseBtn = document.getElementById(`pauseButton${instance}`);
    const seekSlider = document.getElementById(`seekSlider${instance}`);
    const currentTimeEl = document.getElementById(`currentTime${instance}`);
    const totalTimeEl = document.getElementById(`totalTime${instance}`);

    if (playBtn) {
        playBtn.textContent = 'Play';
        playBtn.classList.remove('playing');
    }
    if (pauseBtn) {
        pauseBtn.disabled = true;
        pauseBtn.textContent = 'Pause';
    }
    if (seekSlider) seekSlider.value = 0;
    if (currentTimeEl) currentTimeEl.textContent = '0:00';
    if (totalTimeEl) totalTimeEl.textContent = '0:00';

    // Reset mute/solo/volume buttons for all tracks
    let trackIdx = 0;
    while (true) {
        const muteBtn = document.getElementById(`muteButton${instance}-${trackIdx}`);
        const soloBtn = document.getElementById(`soloButton${instance}-${trackIdx}`);
        if (!muteBtn) break;
        muteBtn.textContent = 'Mute';
        if (soloBtn) soloBtn.textContent = 'Solo';
        trackIdx++;
    }
}

/**
 * Toggle play/stop (lazy-loads the playlist on first play)
 */
async function togglePlay(instance, button) {
    // If this instance is currently playing, stop it
    if (isPlaying[instance] && eventEmitters[instance]) {
        button.textContent = 'Play';
        button.classList.remove('playing');
        eventEmitters[instance].emit('stop');
        return;
    }

    // Guard against double-clicks during async init
    if (isInitializing) return;

    // Stop and destroy any OTHER active playlist to free resources
    if (activeInstance !== null && activeInstance !== instance) {
        destroyPlaylist(activeInstance);
        activeInstance = null;
    }

    // Lazy-init: if playlist not yet loaded, initialize it now
    if (!playlists[instance]) {
        if (!stemsData[instance] || stemsData[instance].length === 0) {
            console.error(`No stems data for instance ${instance}`);
            return;
        }

        isInitializing = true;
        button.textContent = 'Loading...';
        button.disabled = true;

        try {
            await initPlaylist(instance, stemsData[instance]);
        } catch (error) {
            console.error(`Error initializing playlist ${instance}:`, error);
            button.textContent = 'Play';
            button.disabled = false;
            isInitializing = false;
            return;
        }

        button.disabled = false;
        isInitializing = false;
    }

    // Play
    activeInstance = instance;
    button.textContent = 'Stop';
    button.classList.add('playing');
    eventEmitters[instance].emit('select', 0, 0); // Ensure playback always starts from the beginning
    eventEmitters[instance].emit('play');
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
    if (!playlists[instance] || !playlists[instance].tracks) return;

    const track = playlists[instance].tracks[trackIndex];
    if (!track) return;

    // Toggle mute state
    const isMuted = button.textContent === 'Unmute';
    const newMuteState = !isMuted;

    button.textContent = newMuteState ? 'Unmute' : 'Mute';

    // Set the track's gain to 0 to mute, or restore to saved volume to unmute
    if (!track.savedGain) {
        track.savedGain = track.gain || 1.0;
    }

    const targetGain = newMuteState ? 0 : track.savedGain;
    track.gain = targetGain;

    // Update the volumeGain node in playout
    if (track.playout && track.playout.volumeGain) {
        track.playout.volumeGain.gain.value = targetGain;
    }
}

/**
 * Toggle solo for a track
 */
function toggleSolo(instance, button, trackIndex) {
    if (!playlists[instance] || !playlists[instance].tracks) return;

    const tracks = playlists[instance].tracks;
    const isSoloed = button.textContent === 'Unsolo';
    const newSoloState = !isSoloed;

    button.textContent = newSoloState ? 'Unsolo' : 'Solo';

    // Check if any tracks are soloed
    let anySoloed = false;
    tracks.forEach((track, idx) => {
        if (idx === trackIndex) {
            track.soloed = newSoloState;
        }
        if (track.soloed) {
            anySoloed = true;
        }
    });

    // Update all track gains based on solo state
    tracks.forEach((track, idx) => {
        if (!track.savedGain) {
            track.savedGain = track.gain || 1.0;
        }

        const targetGain = anySoloed ? (track.soloed ? track.savedGain : 0) : track.savedGain;
        track.gain = targetGain;

        // Update the volumeGain node in playout
        if (track.playout && track.playout.volumeGain) {
            track.playout.volumeGain.gain.value = targetGain;
        }
    });
}

/**
 * Update volume for a track
 */
function updateVolume(instance, trackIndex, slider) {
    if (!playlists[instance] || !playlists[instance].tracks) return;

    const track = playlists[instance].tracks[trackIndex];
    if (!track) return;

    // Convert 0-100 to 0-1
    const volume = slider.value / 100;
    track.gain = volume;
    track.savedGain = volume; // Update saved gain so mute/unmute uses correct value

    // Update the volumeGain node in playout
    if (track.playout && track.playout.volumeGain) {
        track.playout.volumeGain.gain.value = volume;
    }
}

/**
 * Update master volume
 */
function updateMasterVolume(instance, slider) {
    if (!playlists[instance]) return;

    // Convert 0-100 to 0-1
    const volume = slider.value / 100;

    // Update master gain if available
    if (playlists[instance].masterGain) {
        playlists[instance].masterGain = volume;
    }

    // Update all tracks' master gain node if it exists
    if (playlists[instance].tracks) {
        playlists[instance].tracks.forEach(track => {
            if (track.playout && track.playout.masterGain) {
                track.playout.masterGain.gain.value = volume;
            }
        });
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
 * Initialize players for a collection of pieces
 * Renders a collection header followed by all pieces in the collection
 */
async function initCollectionPlayers(collectionsData, startingPieceIndex) {
    let playersContainer = document.getElementById('players-container');
    let currentPieceIndex = startingPieceIndex;

    for (let collectionIndex = 0; collectionIndex < collectionsData.length; collectionIndex++) {
        const collection = collectionsData[collectionIndex];

        // Add horizontal divider before collection (if not first item)
        if (currentPieceIndex > 0) {
            let hr = document.createElement('hr');
            hr.classList.add('piece-divider');
            hr.style.borderTop = '3px solid #4a5568';
            hr.style.margin = '2rem 0';
            playersContainer.appendChild(hr);
        }

        // Create collection header
        let collectionHeader = document.createElement('div');
        collectionHeader.classList.add('collection-header');
        collectionHeader.style.cssText = 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;';

        let collectionTitle = document.createElement('h2');
        collectionTitle.style.cssText = 'font-size: 1.5rem; font-weight: bold; margin: 0 0 0.5rem 0;';
        collectionTitle.innerHTML = '<i class="fas fa-folder-open" style="margin-right: 10px;"></i>' + collection.title;
        collectionHeader.appendChild(collectionTitle);

        let pieceCount = document.createElement('p');
        pieceCount.style.cssText = 'margin: 0; opacity: 0.9; font-size: 0.9rem;';
        pieceCount.textContent = `${collection.pieces.length} piece${collection.pieces.length !== 1 ? 's' : ''} in this collection`;
        collectionHeader.appendChild(pieceCount);

        // Collection instructions if provided
        if (collection.instructions) {
            let instructions = document.createElement('div');
            instructions.style.cssText = 'margin-top: 1rem; padding: 0.75rem; background: rgba(255,255,255,0.15); border-radius: 8px; font-size: 0.9rem;';
            instructions.textContent = collection.instructions;
            collectionHeader.appendChild(instructions);
        }

        // Collection PDF download if available
        if (collection.pdf_score) {
            let pdfContainer = document.createElement('div');
            pdfContainer.style.cssText = 'margin-top: 1rem;';

            let pdfLink = document.createElement('a');
            pdfLink.href = collection.pdf_score;
            pdfLink.target = '_blank';
            pdfLink.download = '';
            pdfLink.style.cssText = 'display: inline-flex; align-items: center; background: white; color: #667eea; padding: 0.5rem 1rem; border-radius: 6px; text-decoration: none; font-weight: 500;';

            let pdfIcon = document.createElement('i');
            pdfIcon.classList.add('fas', 'fa-file-pdf');
            pdfIcon.style.marginRight = '8px';

            let pdfText = document.createTextNode(
                collection.pdf_score_title || 'Download Full Collection Score (PDF)'
            );

            pdfLink.appendChild(pdfIcon);
            pdfLink.appendChild(pdfText);
            pdfContainer.appendChild(pdfLink);
            collectionHeader.appendChild(pdfContainer);
        }

        playersContainer.appendChild(collectionHeader);

        // Render each piece in the collection
        for (let i = 0; i < collection.pieces.length; i++) {
            const piece = collection.pieces[i];

            // Add divider between pieces within collection
            if (i > 0) {
                let hr = document.createElement('hr');
                hr.classList.add('piece-divider');
                hr.style.borderStyle = 'dashed';
                playersContainer.appendChild(hr);
            }

            // Create player for this piece (reusing existing logic)
            await createPiecePlayer(piece, currentPieceIndex, playersContainer, true);
            currentPieceIndex++;
        }
    }

    return currentPieceIndex;
}

/**
 * Create a player for a single piece
 * Extracted from initPlayers for reuse with collections
 */
async function createPiecePlayer(piece, pieceIndex, container, isInCollection = false) {
    // Create player container
    let playerContainer = document.createElement('div');
    playerContainer.classList.add('player-container');
    if (isInCollection) {
        playerContainer.style.marginLeft = '1rem';
        playerContainer.style.borderLeft = '3px solid #667eea';
        playerContainer.style.paddingLeft = '1rem';
    }

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

    // Seek on change (when user releases the slider)
    seekSlider.onchange = (e) => {
        const instance = pieceIndex + 1;
        const position = (e.target.value / 1000) * getDuration(instance);
        if (eventEmitters[instance]) {
            eventEmitters[instance].emit('select', position, position);
        }
    };

    // Update slider position while dragging (visual feedback only)
    seekSlider.oninput = (e) => {
        const instance = pieceIndex + 1;
        const position = (e.target.value / 1000) * getDuration(instance);
        const currentTimeEl = document.getElementById(`currentTime${instance}`);
        if (currentTimeEl) {
            currentTimeEl.textContent = formatTime(position);
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
    playlistContainer.style.display = 'none';

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

    // Add PDF download button if available (for standalone pieces, not in collections)
    if (piece.pdf_score && !isInCollection) {
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

    container.appendChild(playerContainer);

    // Store stems data for lazy loading (playlist will be initialized on first Play click)
    stemsData[pieceIndex + 1] = piece.stems;
}

/**
 * Load and initialize on page load
 */
window.onload = async () => {
    const lessonId = document.getElementById('lesson-id')?.value;
    const isPrivateLesson = document.getElementById('is-private-lesson')?.value === 'true';
    const pieceId = document.getElementById('piece-id')?.value;
    const isLibraryPlayer = document.getElementById('is-library-player')?.value === 'true';
    const collectionId = document.getElementById('collection-id')?.value;
    const isLibraryCollection = document.getElementById('is-library-collection')?.value === 'true';

    // Determine which mode we're in and construct the appropriate URL
    let url;
    if (isLibraryPlayer && pieceId) {
        console.log("Fetching piece from library:", pieceId);
        url = `/audioplayer/library/piece/${pieceId}/pieces-json/`;
    } else if (isLibraryCollection && collectionId) {
        console.log("Fetching collection from library:", collectionId);
        url = `/audioplayer/library/collection/${collectionId}/pieces-json/`;
    } else if (lessonId) {
        console.log("Fetching pieces for lesson:", lessonId, "Private lesson:", isPrivateLesson);
        // Use different URL pattern for private lessons vs course lessons
        url = isPrivateLesson
            ? `/audioplayer/private-lesson/${lessonId}/pieces-json/`
            : `/audioplayer/lesson/${lessonId}/pieces-json/`;
    } else {
        console.error('No lesson ID, piece ID, or collection ID found');
        return;
    }

    try {
        let response = await fetch(url);
        console.log("Response status:", response.status);

        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        let data = await response.json();
        console.log("Data:", data);

        // Handle both lesson data format and library piece format
        const piecesData = data.pieces_data || data.pieces || [];
        const collectionsData = data.collections_data || [];

        const hasContent = (piecesData && piecesData.length > 0) || (collectionsData && collectionsData.length > 0);

        if (hasContent) {
            let playersContainer = document.getElementById('players-container');
            playersContainer.innerHTML = '';

            let currentPieceIndex = 0;

            // First render individual pieces
            if (piecesData && piecesData.length > 0) {
                // Sort pieces by order
                piecesData.sort((a, b) => a.order - b.order);

                for (let i = 0; i < piecesData.length; i++) {
                    const piece = piecesData[i];

                    // Add divider between pieces
                    if (i > 0) {
                        let hr = document.createElement('hr');
                        hr.classList.add('piece-divider');
                        playersContainer.appendChild(hr);
                    }

                    await createPiecePlayer(piece, currentPieceIndex, playersContainer, false);
                    currentPieceIndex++;
                }
            }

            // Then render collections
            if (collectionsData && collectionsData.length > 0) {
                // Sort collections by order
                collectionsData.sort((a, b) => a.order - b.order);

                currentPieceIndex = await initCollectionPlayers(collectionsData, currentPieceIndex);
            }
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
