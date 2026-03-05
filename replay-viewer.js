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

        // Get unique tournaments
        tournamentsSet = new Set([]);
        replayData.forEach(replay => {
            if ("tournamentShort" in replay)
                tournamentsSet.add(replay.tournamentShort);
            //if (!("tournamentShort" in replay))
            //    tournamentsSet.add(replay.tournament);
        });
        tournamentNames = Array.from(tournamentsSet).sort(
            new Intl.Collator([], {numeric: true}).compare
        );

        // Update tournament select
        tournamentNames.forEach(tournament => {
            const option = document.createElement("option");
            option.innerHTML = tournament;
            tournamentSelect.appendChild(option);
        });

        // Get unique player tags
        playerTagsSet = new Set([]);
        replayData.forEach(replay => {
            playerTagsSet.add(replay.player1);
            playerTagsSet.add(replay.player2);
        });
        playerTags = Array.from(playerTagsSet).sort((a, b) => {
            return a.toLowerCase().localeCompare(b.toLowerCase());
        });

        // Update player select
        playerTags.forEach(tag => {
            for (const selecter of [player1TagSelect, player2TagSelect]) {
                const option = document.createElement("option");
                option.innerHTML = tag;
                selecter.appendChild(option);
            }
        });

        // Update character select
        for (const character of Object.keys(characterIcons)) {
            for (const selecter of [player1CharacterSelect, player2CharacterSelect]) {
                const option = document.createElement("option");
                option.innerHTML = character;
                selecter.appendChild(option);
            }
        };
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
        characterIcons[char] || "❓"
    ).join(' ');

    const player2Chars = (replay.player2Characters || []).map(char =>
        characterIcons[char] || "❓"
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

function getSearchableMatch(replay, searchTerm) {
    if (!searchTerm) return true;

    const searchPieces = searchTerm.toLowerCase().split(/\s+/);

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

        // Default search
        return searchableText.includes(piece);
    });
}

function getTournamentMatch(replay, tournament) {
    if (!tournament) return true;
    const tournamentMatch = replay.tournament == tournament;
    const tournamentShortMatch = replay.tournamentShort == tournament;
    return tournamentMatch || tournamentShortMatch;
}

function getPlayerMatch(replay, playerTag, character, skip) {
    if (!playerTag && !character) return [true, 0];
    if (!replay.player1 || !replay.player2) return [false, 0];

    const player1TagMatch = playerTag ? (replay.player1 == playerTag) : true;
    const player2TagMatch = playerTag ? (replay.player2 == playerTag) : true;

    var player1CharMatch = true;
    var player2CharMatch = true;
    if (character) {
        if (replay.player1Characters) {
            player1CharMatch = replay.player1Characters.includes(character);
        }
        else
        {
            player1CharMatch = false;
        }
        if (replay.player2Characters) {
            player2CharMatch = replay.player2Characters.includes(character);
        }
        {
            player2CharMatch = false;
        }
    }

    if (player1TagMatch && player1CharMatch && !skip.includes(1)) return [true, 1];
    if (player2TagMatch && player2CharMatch && !skip.includes(2)) return [true, 2];
    return [false, 0]
}

// Search functionality
function performSearch() {
    const searchTerm = searchInput.value.trim();
    const tournamentTerm = tournamentSelect.value;
    const player1TagTerm = player1TagSelect.value;
    const player2TagTerm = player2TagSelect.value;
    const player1Character = player1CharacterSelect.value;
    const player2Character = player2CharacterSelect.value;

    loadingMessage.style.display = 'block';

    setTimeout(() => {
        loadingMessage.style.display = 'none';

        const filtered = replayData.filter(replay => {
            const searchMatch = getSearchableMatch(replay, searchTerm);
            const tournamentMatch = getTournamentMatch(replay, tournamentTerm);
            const [player1Match, player1MatchedPlayer] = getPlayerMatch(
                replay, player1TagTerm, player1Character, []
            );
            const [player2Match, player2MatchedPlayer] = getPlayerMatch(
                replay, player2TagTerm, player2Character, [player1MatchedPlayer]
            );
            return searchMatch && tournamentMatch && player1Match && player2Match;
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

const characterIcons = {
    "Bowser": "🐢",
    "Captain Falcon": "🏎️",
    "Donkey Kong": "🦍",
    "Dr. Mario": "💊",
    "Falco": "🦅",
    "Fox": "🦊",
    "Ganondorf": "👹",
    "Ice Climbers": "🧊",
    "Jigglypuff": "🎈",
    "Kirby": "⭐",
    "Link": "🗡️",
    "Luigi": "🎰",
    "Mario": "🇮🇹",
    "Marth": "🤺",
    "Mewtwo": "🧠",
    "Mr. Game & Watch": "🫥",
    "Ness": "🧢",
    "Peach": "👑",
    "Pichu": "🐣",
    "Pikachu": "⚡",
    "Roy": "🔥",
    "Samus": "🚀",
    "Sheik": "🥷",
    "Yoshi": "🦖",
    "Young Link": "🏹",
    "Zelda": "🔮",
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
const tournamentSelect = document.getElementById('tournament');
const player1TagSelect = document.getElementById('player1Tag');
const player2TagSelect = document.getElementById('player2Tag');
const player1CharacterSelect = document.getElementById('player1Character');
const player2CharacterSelect = document.getElementById('player2Character');
const resultsContainer = document.getElementById('replaysResults');
const paginationTopContainer = document.getElementById('paginationTop');
const paginationBottomContainer = document.getElementById('paginationBottom');
const loadingMessage = resultsContainer.querySelector('.loading-message');
const noResultsMessage = resultsContainer.querySelector('.no-results-message');

// Start the app
document.addEventListener('DOMContentLoaded', init);
