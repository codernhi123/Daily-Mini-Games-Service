document.addEventListener('DOMContentLoaded', () => {
    // Get the two main screens
    const mainMenuScreen = document.getElementById('main-menu-screen');
    const leaderboardScreen = document.getElementById('leaderboard-screen');

    // Get the main navigation buttons
    const viewLeaderboardBtn = document.getElementById('view-leaderboard-btn');
    const leaderboardBackBtn = document.getElementById('leaderboard-back-btn');
    const startGameBtn = document.getElementById('start-game-btn'); // For later

    // Get the leaderboard toggle buttons
    const game1Btn = document.getElementById('game1-btn');
    const game2Btn = document.getElementById('game2-btn');
    const globalBtn = document.getElementById('global-btn');
    const friendBtn = document.getElementById('friend-btn');

    // Get the content display areas
    const leaderboardBody = document.getElementById('leaderboard-body');
    const headerText = document.getElementById('header-text');
    const inactiveBody = document.getElementById('inactive-body')

    // Get current stat
    const now = new Date();
    const time_now = now.toISOString();

    const when = encodeURIComponent(time_now);

    // Track the state
    let currentLeaderboardType = 'global'; // Scope
    let currentLeaderboardGame = 'Trivia'; // Game

    async function getMyId() {
        try {
            // COOKIE CHANGE: No headers needed! The browser sends the cookie automatically.
            const response = await fetch("/v2/authentications/me");

            if (!response.ok) {
                // If this fails, it usually means the cookie is missing/expired (User not logged in)
                console.log("User not logged in (Auth check failed)");
                return null;
            }
            
            const user_data = await response.json();
            return user_data.id;
        } catch (error) {
            console.error("Could not get User ID:", error);
            return null;
        }
    }

    async function fetchInactiveData(user_id, game_name, when) {
        inactiveBody.innerHTML = '<tr><td colspan="2">Loading...</td></tr>';

        let apiUrl = '';
        apiUrl = `/leaderboard/inactive/${user_id}/${game_name}/${when}`;

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const users = await response.json();
            renderInactive(users);
        } catch (error) {
            console.error('Failed to fetch inactive friends:', error);
            if (user_id != null) 
                inactiveBody.innerHTML = '<tr><td colspan="2">Failed to load</td></tr>';
            else 
                inactiveBody.innerHTML = '<tr><td colspan="2">Login to see who has not played</td></tr>';
        }
    }

    function renderInactive(users) {
        inactiveBody.innerHTML = '';

        if (users.length === 0) {
            inactiveBody.innerHTML = '<tr><td colspan="2">No available friend has missed their game!</td></tr>';
            return;
        }

        users.forEach(element => {
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="2">${element.user_id}</td>`;
            inactiveBody.appendChild(row);
        });
    }

    async function fetchLeaderboardData(type, user_id, game_name, when) {
        leaderboardBody.innerHTML = '<tr><td colspan="2">Loading...</td></tr>';

        let apiUrl = '';
        if (type === 'global') apiUrl = `/leaderboard/view-global-leaderboard/${game_name}/${when}`;
        else apiUrl = `/leaderboard/view-friend-leaderboard/${user_id}/${game_name}/${when}`;

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const scores = await response.json();
            renderLeaderboard(scores);
        } catch (error) {
            console.error('Failed to fetch leaderboard:', error);
            if (user_id != null) 
                leaderboardBody.innerHTML = '<tr><td colspan="2">Failed to load scores.</td></tr>';
            else 
                leaderboardBody.innerHTML = '<tr><td colspan="2">Login to see friends.</td></tr>';
        }
    }

    function renderLeaderboard(scores) {
        leaderboardBody.innerHTML = '';

        if (scores.length === 0) {
            leaderboardBody.innerHTML = '<tr><td colspan="2">No scores yet!</td></tr>';
            return;
        }

        scores.forEach(element => {
            const row = document.createElement('tr');
            row.innerHTML = `<td>${element.user_name}</td><td>${element.scores}</td>`;
            leaderboardBody.appendChild(row);
        });
    }

    function updateToggleButtons() {
        if (currentLeaderboardType === 'global') {
            globalBtn.classList.add('active');
            friendBtn.classList.remove('active');
        } else {
            globalBtn.classList.remove('active');
            friendBtn.classList.add('active');
        }

        if (currentLeaderboardGame === 'Trivia') {
            game1Btn.classList.add('active');
            game2Btn.classList.remove('active');
        } else {
            game1Btn.classList.remove('active');
            game2Btn.classList.add('active');
        }
    }

    startGameBtn.addEventListener('click', () => {
        window.location.href = '/go-to-frontend';
    });

    viewLeaderboardBtn.addEventListener('click', async () => {
        mainMenuScreen.style.display = 'none';// Hide the main menu
        leaderboardScreen.style.display = 'flex';// Show the leaderboard

        currentLeaderboardType = 'global';
        currentLeaderboardGame = 'Trivia';
        updateToggleButtons();
        
        const user_id = await getMyId();
        fetchLeaderboardData(currentLeaderboardType, user_id, currentLeaderboardGame, when);
        fetchInactiveData(user_id, currentLeaderboardGame, when);
    });

    leaderboardBackBtn.addEventListener('click', () => {
        mainMenuScreen.style.display = 'flex';// Show the main menu
        leaderboardScreen.style.display = 'none';// Hide the leaderboard
    });

    globalBtn.addEventListener('click', async () => {
        if (currentLeaderboardType !== 'global') {
            currentLeaderboardType = 'global';
            updateToggleButtons();
            const user_id = await getMyId();
            fetchLeaderboardData(currentLeaderboardType, user_id, currentLeaderboardGame, when);
            fetchInactiveData(user_id, currentLeaderboardGame, when);
        }
    });

    friendBtn.addEventListener('click', async () => {
        if (currentLeaderboardType !== 'friend') {
            currentLeaderboardType = 'friend';
            updateToggleButtons();
            const user_id = await getMyId();
            fetchLeaderboardData(currentLeaderboardType, user_id, currentLeaderboardGame, when);
            fetchInactiveData(user_id, currentLeaderboardGame, when);
        }
    });

    game1Btn.addEventListener('click', async () => {
        if (currentLeaderboardGame !== 'Trivia') {
            currentLeaderboardGame = 'Trivia';
            updateToggleButtons();
            const user_id = await getMyId();
            fetchLeaderboardData(currentLeaderboardType, user_id, currentLeaderboardGame, when);
            fetchInactiveData(user_id, currentLeaderboardGame, when);
        }
    });

    game2Btn.addEventListener('click', async () => {
        if (currentLeaderboardGame !== 'Memory') {
            currentLeaderboardGame = 'Memory';
            updateToggleButtons();
            const user_id = await getMyId();
            fetchLeaderboardData(currentLeaderboardType, user_id, currentLeaderboardGame, when);
            fetchInactiveData(user_id, currentLeaderboardGame, when);
        }
    });

    // ... will add more listeners here for game1Btn, game2Btn, etc. ...
});