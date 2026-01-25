// Audio Player for Multi-Track Playalong Pieces
// Uses Waveform Playlist v4 for synchronized multi-track playback

// Store playlist instances for each piece
let playlists = [];
let eventEmitters = [];
let durations = []; // Store duration for each piece

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

        // Get duration from the playlist
        // The playlist stores duration in seconds - we need to access it from the internal state
        // Let's try to get it from the playlist object
        if (playlists[instance].duration) {
            durations[instance] = playlists[instance].duration;
        } else {
            // Fallback: wait for first timeupdate to capture duration
            durations[instance] = 0;
        }

        // Listen for audio sources loaded event to get duration
        eventEmitters[instance].on('audiosourcesloaded', () => {
            // Try to get duration from the playlist tracks
            if (playlists[instance] && playlists[instance].tracks && playlists[instance].tracks.length > 0) {
                const track = playlists[instance].tracks[0];
                if (track && track.duration) {
                    durations[instance] = track.duration;
                    const totalTimeEl = document.getElementById(`totalTime${instance}`);
                    if (totalTimeEl) {
                        totalTimeEl.textContent = formatTime(durations[instance]);
                    }
                }
            }
        });

        // Setup event listeners for time updates
        setupTimeUpdateListener(instance);

        // Update total duration display - will be updated on first timeupdate if not available now
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

        // If duration not yet set, try to get it from the playlist
        if (!durations[instance] || durations[instance] === 0) {
            // Try to access playlist internal state to get duration
            if (playlists[instance] && playlists[instance].tracks && playlists[instance].tracks[0]) {
                const track = playlists[instance].tracks[0];
                if (track.buffer && track.buffer.duration) {
                    durations[instance] = track.buffer.duration;
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

        // Reset playlist position to beginning after stopping
        // Use setTimeout to ensure stop has completed before seeking
        setTimeout(() => {
            if (eventEmitters[instance]) {
                eventEmitters[instance].emit('select', 0, 0);
            }
        }, 100);
    });
}

/**
 * Get duration of playlist
 */
function getDuration(instance) {
    return durations[instance] || 0;
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

    // Initialize waveform-playlist for this piece
    await initPlaylist(pieceIndex + 1, piece.stems);
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
