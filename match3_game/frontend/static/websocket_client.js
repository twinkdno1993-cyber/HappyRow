let ws = null;
let currentRoomId = null;
let isSearching = false;

function connectWebSocket(token) {
    const wsUrl = `ws://localhost:8000/ws/${token}`;
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        console.log('WebSocket connected');
        document.getElementById('ws-status').textContent = '🟢 Connected';
        document.getElementById('ws-status').style.color = 'green';
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        document.getElementById('ws-status').textContent = '🔴 Error';
        document.getElementById('ws-status').style.color = 'red';
    };
    
    ws.onclose = function() {
        console.log('WebSocket disconnected');
        document.getElementById('ws-status').textContent = '⚫ Disconnected';
        document.getElementById('ws-status').style.color = 'gray';
        isSearching = false;
    };
}

function findMatch() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        alert('WebSocket not connected. Please login again.');
        return;
    }
    
    isSearching = true;
    ws.send(JSON.stringify({
        type: 'find_match'
    }));
    
    const findBtn = document.getElementById('find-match-btn');
    if (findBtn) {
        findBtn.disabled = true;
        findBtn.textContent = 'Searching...';
    }
}

function cancelSearch() {
    if (ws && ws.readyState === WebSocket.OPEN && isSearching) {
        ws.send(JSON.stringify({
            type: 'cancel_search'
        }));
        isSearching = false;
        
        const findBtn = document.getElementById('find-match-btn');
        if (findBtn) {
            findBtn.disabled = false;
            findBtn.textContent = 'Find Match';
        }
    }
}

function sendMove(fromRow, fromCol, toRow, toCol) {
    if (!ws || ws.readyState !== WebSocket.OPEN || !currentRoomId) {
        console.error('Cannot send move: WebSocket not ready');
        return;
    }
    
    ws.send(JSON.stringify({
        type: 'move',
        room_id: currentRoomId,
        from_row: fromRow,
        from_col: fromCol,
        to_row: toRow,
        to_col: toCol
    }));
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'waiting':
            console.log('Waiting for opponent...');
            if (typeof showWaitingMessage === 'function') {
                showWaitingMessage(data.message);
            }
            break;
            
        case 'game_start':
            console.log('Game started! Room:', data.room_id);
            currentRoomId = data.room_id;
            isSearching = false;
            
            if (typeof updateBoard === 'function') {
                updateBoard(data.field);
            }
            if (typeof updateTimer === 'function') {
                updateTimer(data.timer);
            }
            if (typeof onGameStart === 'function') {
                onGameStart(data.opponent_nick);
            }
            
            const findBtn = document.getElementById('find-match-btn');
            if (findBtn) {
                findBtn.disabled = false;
                findBtn.textContent = 'Find Match';
            }
            break;
            
        case 'update':
            if (typeof updateBoard === 'function') {
                updateBoard(data.field);
            }
            if (typeof updateScore === 'function') {
                updateScore(data.scores.you);
            }
            if (typeof onAnimationComplete === 'function') {
                onAnimationComplete();
            }
            break;
            
        case 'timer':
            if (typeof updateTimer === 'function') {
                updateTimer(data.time);
            }
            break;
            
        case 'game_over':
            currentRoomId = null;
            if (typeof showGameOver === 'function') {
                showGameOver(data.winner, data.score);
            }
            if (typeof onGameEnd === 'function') {
                onGameEnd();
            }
            break;
            
        case 'room_closed':
            currentRoomId = null;
            console.log('Room closed:', data.message);
            break;
            
        case 'search_cancelled':
            isSearching = false;
            if (typeof onSearchCancelled === 'function') {
                onSearchCancelled();
            }
            break;
            
        default:
            console.log('Unknown message type:', data);
    }
}

function disconnectWebSocket() {
    if (ws) {
        ws.close();
        ws = null;
    }
}