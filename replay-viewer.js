(function() {
    // Character emoji mapping
    const characterIcons = {
        fox: "🦊",
        falco: "🦅",
        marth: "🤺",
        sheik: "🥷",
        peach: "👑",
        falcon: "🏎️",
        jigglypuff: "🎈", puff: "🎈",
        pikachu: "⚡", pika: "⚡",
        samus: "🚀",
        yoshi: "🦖",
        luigi: "🎰",
        mario: "🇮🇹",
        ganondorf: "👹", ganon: "👹",
        zelda: "🔮",
        link: "🗡️",
        younglink: "🏹", yink: "🏹", yl: "🏹", ylink: "🏹",
        mewtwo: "🧠",
        ness: "🧢",
        iceclimbers: "🧊", ics: "🧊", icies: "🧊",
        bowser: "🐢",
        donkeykong: "🦍", dk: "🦍",
        drmario: "💊", doc: "💊",
        pichu: "🐣",
        roy: "🔥",
        kirby: "⭐",
        gnw: "🫥", gameandwatch: "🫥", gw: "🫥", gamewatch: "🫥"
    };

    // Configuration
    const config = {
        pageSize: 10,
        dataUrl: 'replays.json',
        aliasesUrl: 'aliases.json'
    };

    // State
    let replayData = [];
    let playerAliases = {};
    let currentPage = 1;
    let totalPages = 1;
    let currentSearchResults = [];

    // DOM elements
    const searchInput = document.getElementById('replaySearch');
    const searchButton = document.getElementById('searchButton');
    const resultsContainer = document.getElementById('replaysResults');
    const paginationTopContainer = document.getElementById('paginationTop');
    const paginationBottomContainer = document.getElementById('paginationBottom');
    const loadingMessage = resultsContainer.querySelector('.loading-message');
    const noResultsMessage = resultsContainer.querySelector('.no-results-message');

    // Initialize
    async function init() {
        await loadData();
        setupEventListeners();
        displayReplays(replayData);
    }

    // Load replay data and aliases
    async function loadData() {
        try {
            loadingMessage.style.display = 'block';

            const [replaysResponse, aliasesResponse] = await Promise.all([
                fetch(config.dataUrl),
                fetch(config.aliasesUrl)
            ]);

            if (!replaysResponse.ok) throw new Error('Failed to load replays');

            replayData = await replaysResponse.json();

            // Load aliases if available
            if (aliasesResponse.ok) {
                playerAliases = await aliasesResponse.json();
            }

            // Sort by upload date (newest first)
            replayData.sort((a, b) => {
                const dateA = new Date(a.date || '1970-01-01');
                const dateB = new Date(b.date || '1970-01-01');
                return dateB - dateA;
            });

        } catch (error) {
            console.error('Error loading data:', error);
            replayData = [];
            playerAliases = {};
        } finally {
            loadingMessage.style.display = 'none';
        }
    }

    // Setup event listeners
    function setupEventListeners() {
        searchButton.addEventListener('click', performSearch);
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }

    function createReplayItem(replay) {
        const div = document.createElement('div');
        div.className = 'replay-item';

        const player1Chars = (replay.player1Characters || []).map(char =>
            characterIcons[char.trim().toLowerCase().replace(/\s+/g, "")] || "❓"
        ).join(' ');

        const player2Chars = (replay.player2Characters || []).map(char =>
            characterIcons[char.trim().toLowerCase().replace(/\s+/g, "")] || "❓"
        ).join(' ');

        div.innerHTML = `
            <div class="replay-header">
                <div class="match-info">
                    <div class="player-info">
                        <span class="character-icons">${player1Chars}</span>
                        <span class="player-name">${replay.player1}</span>
                    </div>
                    <span class="vs-text">VS</span>
                    <div class="player-info">
                        <span class="player-name">${replay.player2}</span>
                        <span class="character-icons">${player2Chars}</span>
                    </div>
                </div>
                <div class="tournament-name">${replay.tournament}</div>
            </div>
            <div class="replay-video" data-loaded="false" data-youtubeid="${replay.youtubeId}" ${replay.timestamp ? `data-timestamp="${replay.timestamp}"` : ''}>
                <div class="video-wrapper"></div>
            </div>
        `;

        // Click handler for video toggle
        div.addEventListener('click', (e) => {
                if (e.target.closest('.replay-video')) return;

                const videoContainer = div.querySelector('.replay-video');

            // Close other open videos
            document.querySelectorAll('.replay-video.show').forEach(v => {
                if (v !== videoContainer) unloadVideo(v);
            });

            if (!videoContainer.classList.contains('show')) {
                loadVideo(videoContainer);
            } else {
                unloadVideo(videoContainer);
            }
        });

        return div;
    }

    function loadVideo(videoContainer) {
        if (videoContainer.dataset.loaded === 'true') {
            videoContainer.classList.add('show');
            return;
        }

        const youtubeId = videoContainer.dataset.youtubeid;
        const timestamp = videoContainer.dataset.timestamp;
        const wrapper = videoContainer.querySelector('.video-wrapper');

        const iframe = document.createElement('iframe');
        let embedUrl = `https://www.youtube.com/embed/${youtubeId}`;

        // Add timestamp if available
        if (timestamp && timestamp !== 'undefined') {
            embedUrl += `?start=${timestamp}`;
        }

        iframe.src = embedUrl;
        iframe.title = 'YouTube video player';
        iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
        iframe.allowFullscreen = true;
        iframe.loading = 'lazy';

        wrapper.appendChild(iframe);
        videoContainer.dataset.loaded = 'true';
        videoContainer.classList.add('show');
    }

    function unloadVideo(videoDiv) {
        videoDiv.classList.remove("show");
        const wrapper = videoDiv.querySelector(".video-wrapper");
        wrapper.innerHTML = ""; // remove iframe → stops playback & frees memory
        videoDiv.dataset.loaded = "false";
    }

    // render helpers
    function displayReplays(list, page = 1) {
        currentSearchResults = list;
        totalPages  = Math.max(1, Math.ceil(list.length / config.pageSize));
        currentPage = Math.min(Math.max(1, page), totalPages);

        const start = (currentPage - 1) * config.pageSize;
        const end   = start + config.pageSize;
        const slice = list.slice(start, end);

        resultsContainer.querySelectorAll(".replay-item").forEach(el => el.remove());

        if (slice.length === 0) {
            noResultsMessage.style.display = "block";
        } else {
            noResultsMessage.style.display = "none";
            slice.forEach(r => {
                const replayElement = createReplayItem(r);
                resultsContainer.appendChild(replayElement);
            });
        }

        updatePagination(paginationTopContainer);
        updatePagination(paginationBottomContainer);
    }


    // Update pagination controls
    function updatePagination(paginationContainer) {
        paginationContainer.innerHTML = '';

        if (totalPages <= 1) return;

        // Helper to create button
        const createButton = (text, page, disabled = false, active = false) => {
            const button = document.createElement('button');
            button.textContent = text;
            button.disabled = disabled;
            if (active) button.classList.add('active');
            if (!disabled) {
                button.addEventListener('click', () => displayReplays(currentSearchResults, page));
            }
            return button;
        };

        // Previous button
        paginationContainer.appendChild(
            createButton('← Previous', currentPage - 1, currentPage === 1)
        );

        // Page numbers
        const pageNumbers = [];
        pageNumbers.push(1);

        const startAround = Math.max(2, currentPage - 2);
        const endAround = Math.min(totalPages - 1, currentPage + 2);

        for (let p = startAround; p <= endAround; p++) {
            pageNumbers.push(p);
        }

        if (totalPages > 1) pageNumbers.push(totalPages);

        // Remove duplicates and sort
        const uniquePages = [...new Set(pageNumbers)].sort((a, b) => a - b);

        // Add page buttons with ellipsis
        let prevPage = null;
        uniquePages.forEach(page => {
            if (prevPage !== null && page - prevPage > 1) {
                const ellipsis = document.createElement('span');
                ellipsis.textContent = '…';
                ellipsis.className = 'ellipsis';
                paginationContainer.appendChild(ellipsis);
            }
            paginationContainer.appendChild(
                createButton(page, page, false, page === currentPage)
            );
            prevPage = page;
        });

        // Next button
        paginationContainer.appendChild(
            createButton('Next →', currentPage + 1, currentPage === totalPages)
        );
    }

    // Search functionality
    function performSearch() {
        const searchTerm = searchInput.value.trim();

        if (!searchTerm) {
            displayReplays(replayData);
            return;
        }

        loadingMessage.style.display = 'block';

        setTimeout(() => {
            loadingMessage.style.display = 'none';

            const searchPieces = searchTerm.toLowerCase().split(/\s+/);

            const filtered = replayData.filter(replay => {
                if (!replay.player1 || !replay.player2) return false;

                const searchableText = `${replay.player1} ${replay.player2} ${(replay.player1Characters || []).join(' ')} ${(replay.player2Characters || []).join(' ')} ${replay.tournament}`.toLowerCase();

                return searchPieces.every(piece => {
                    // Check aliases
                    const aliases = getPlayerAliases(piece);
                    if (aliases.length > 0) {
                        return aliases.some(alias => {
                            const lowerAlias = alias.toLowerCase();
                            return replay.player1.toLowerCase() === lowerAlias ||
                                   replay.player2.toLowerCase() === lowerAlias ||
                                   searchableText.includes(lowerAlias);
                        });
                    }

                    // Check if it's a character
                    if (characterIcons[piece]) {
                        const regex = new RegExp(`\\b${piece}\\b`);
                        return regex.test(searchableText);
                    }

                    // Default search
                    return searchableText.includes(piece);
                });
            });

            displayReplays(filtered);
        }, 200);
    }

    // Get player aliases
    function getPlayerAliases(searchTerm) {
        const normalized = searchTerm.toLowerCase().trim();

        if (playerAliases[normalized]) {
            return playerAliases[normalized];
        }

        for (const [mainPlayer, aliases] of Object.entries(playerAliases)) {
            const normalizedAliases = aliases.map(alias => alias.toLowerCase().trim());
            if (normalizedAliases.includes(normalized)) {
                return aliases;
            }
        }

        return [];
    }

    // Start the app
    document.addEventListener('DOMContentLoaded', init);
})();
