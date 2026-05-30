// Глобальные переменные
let canvas, ctx;
let board = [];
let selectedRow = null, selectedCol = null;
let currentScore = 0;
let gameRunning = true;
let animationInProgress = false;

const BOARD_SIZE = 8;
const TILE_SIZE = 60;
const TILE_TYPES = ['🔴', '🔵', '🟢', '🟡', '🟣', '🟠'];
const TILE_COLORS = {
    '🔴': '#ff4757',
    '🔵': '#45aaf2',
    '🟢': '#2ed573',
    '🟡': '#ffa502',
    '🟣': '#a55eea',
    '🟠': '#ff7f50'
};

function initGame() {
    canvas = document.getElementById('gameCanvas');
    if (!canvas) return;
    ctx = canvas.getContext('2d');
    
    canvas.width = BOARD_SIZE * TILE_SIZE;
    canvas.height = BOARD_SIZE * TILE_SIZE;
    
    canvas.addEventListener('click', handleCanvasClick);
}

function updateBoard(newBoard) {
    board = newBoard;
    drawBoard();
}

function drawBoard() {
    if (!ctx) return;
    
    for (let row = 0; row < BOARD_SIZE; row++) {
        for (let col = 0; col < BOARD_SIZE; col++) {
            const x = col * TILE_SIZE;
            const y = row * TILE_SIZE;
            
            // Рисуем фон
            ctx.fillStyle = TILE_COLORS[board[row][col]] || '#2d3436';
            ctx.fillRect(x, y, TILE_SIZE - 2, TILE_SIZE - 2);
            
            // Рисуем символ
            ctx.fillStyle = 'white';
            ctx.font = `${TILE_SIZE * 0.5}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(board[row][col], x + TILE_SIZE/2, y + TILE_SIZE/2);
            
            // Выделение выбранной клетки
            if (selectedRow === row && selectedCol === col) {
                ctx.strokeStyle = '#ffd700';
                ctx.lineWidth = 4;
                ctx.strokeRect(x, y, TILE_SIZE - 2, TILE_SIZE - 2);
            }
        }
    }
}

function handleCanvasClick(e) {
    if (!gameRunning || animationInProgress) return;
    
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    const mouseX = (e.clientX - rect.left) * scaleX;
    const mouseY = (e.clientY - rect.top) * scaleY;
    
    const col = Math.floor(mouseX / TILE_SIZE);
    const row = Math.floor(mouseY / TILE_SIZE);
    
    if (row < 0 || row >= BOARD_SIZE || col < 0 || col >= BOARD_SIZE) return;
    
    if (selectedRow === null) {
        // Выбираем клетку
        selectedRow = row;
        selectedCol = col;
        drawBoard();
    } else {
        // Пытаемся сделать ход
        const fromRow = selectedRow;
        const fromCol = selectedCol;
        selectedRow = null;
        selectedCol = null;
        
        // Проверяем, что клетки соседние
        if (Math.abs(fromRow - row) + Math.abs(fromCol - col) === 1) {
            makeMove(fromRow, fromCol, row, col);
        } else {
            drawBoard();
        }
    }
}

function makeMove(fromRow, fromCol, toRow, toCol) {
    animationInProgress = true;
    
    // Отправляем ход на сервер
    if (typeof sendMove === 'function') {
        sendMove(fromRow, fromCol, toRow, toCol);
    } else {
        console.error('sendMove function not defined');
        animationInProgress = false;
    }
}

function updateScore(score) {
    currentScore = score;
    const scoreElement = document.getElementById('score');
    if (scoreElement) {
        scoreElement.textContent = score;
    }
}

function updateTimer(time) {
    const timerElement = document.getElementById('timer');
    if (timerElement) {
        timerElement.textContent = time;
        
        if (time <= 10) {
            timerElement.style.color = '#ff4757';
        } else {
            timerElement.style.color = '#333';
        }
    }
}

function showGameOver(winner, finalScore) {
    gameRunning = false;
    const message = winner === 'Победа!' ? '🎉 Вы победили! 🎉' : 
                    winner === 'Поражение!' ? '😔 Вы проиграли... 😔' :
                    winner === 'Ничья!' ? '🤝 Ничья! 🤝' : 'Игра окончена!';
    
    alert(`${message}\nВаш счет: ${finalScore}`);
    
    if (typeof endGame === 'function') {
        endGame();
    }
}

function resetGame() {
    gameRunning = true;
    selectedRow = null;
    selectedCol = null;
    animationInProgress = false;
    currentScore = 0;
    updateScore(0);
}