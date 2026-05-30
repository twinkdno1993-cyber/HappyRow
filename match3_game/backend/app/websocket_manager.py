import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket
from .game_logic import generate_field, apply_move

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.waiting_queue: List[Dict] = []
        self.rooms: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        for i, player in enumerate(self.waiting_queue):
            if player["websocket"] == websocket:
                self.waiting_queue.pop(i)
                break
        
        for room_id, room in list(self.rooms.items()):
            if room["p1"] == websocket or room["p2"] == websocket:
                if room_id in self.rooms:
                    del self.rooms[room_id]
                break

    async def matchmake(self, websocket: WebSocket, user_id: int, nickname: str):
        if len(self.waiting_queue) > 0:
            opponent = self.waiting_queue.pop(0)
            room_id = f"room_{user_id}_{opponent['user_id']}"
            
            field = generate_field()
            self.rooms[room_id] = {
                "p1": websocket,
                "p2": opponent["websocket"],
                "p1_id": user_id,
                "p2_id": opponent["user_id"],
                "p1_nick": nickname,
                "p2_nick": opponent["nickname"],
                "state": field,
                "scores": {websocket: 0, opponent["websocket"]: 0},
                "timer": 60,
                "running": True,
                "room_id": room_id
            }
            
            game_data = {
                "type": "game_start",
                "room_id": room_id,
                "field": field,
                "opponent_nick": opponent["nickname"],
                "timer": 60
            }
            await websocket.send_json(game_data)
            game_data["opponent_nick"] = nickname
            await opponent["websocket"].send_json(game_data)
            
            asyncio.create_task(self.game_timer(room_id))
        else:
            self.waiting_queue.append({
                "websocket": websocket,
                "user_id": user_id,
                "nickname": nickname
            })
            await websocket.send_json({"type": "waiting", "message": "Ищем соперника..."})

    async def game_timer(self, room_id: str):
        room = self.rooms.get(room_id)
        if not room:
            return
        
        for remaining in range(60, 0, -1):
            if not room["running"]:
                return
            room["timer"] = remaining
            await room["p1"].send_json({"type": "timer", "time": remaining})
            await room["p2"].send_json({"type": "timer", "time": remaining})
            await asyncio.sleep(1)
        
        if room["running"]:
            await self.end_game(room_id)

    async def end_game(self, room_id: str):
        room = self.rooms.get(room_id)
        if not room:
            return
        
        room["running"] = False
        score1 = room["scores"][room["p1"]]
        score2 = room["scores"][room["p2"]]
        
        if score1 > score2:
            winner_ws = room["p1"]
            loser_ws = room["p2"]
            winner_score = score1
            loser_score = score2
        elif score2 > score1:
            winner_ws = room["p2"]
            loser_ws = room["p1"]
            winner_score = score2
            loser_score = score1
        else:
            await room["p1"].send_json({"type": "game_over", "winner": "Ничья!", "score": score1})
            await room["p2"].send_json({"type": "game_over", "winner": "Ничья!", "score": score2})
            del self.rooms[room_id]
            return
        
        await winner_ws.send_json({"type": "game_over", "winner": "Победа!", "score": winner_score})
        await loser_ws.send_json({"type": "game_over", "winner": "Поражение!", "score": loser_score})
        
        # Обновление рейтинга
        from .database import SessionLocal
        from .rating import update_pts_after_match
        db = SessionLocal()
        try:
            update_pts_after_match(db, room["p1_id"], room["p2_id"], score1, score2)
        except:
            pass
        finally:
            db.close()
        
        del self.rooms[room_id]

    async def handle_move(self, room_id: str, websocket: WebSocket, move_data: dict):
        room = self.rooms.get(room_id)
        if not room or not room["running"]:
            await websocket.send_json({"type": "error", "message": "Игра не активна"})
            return
        
        new_field, points_earned = apply_move(
            room["state"],
            move_data["from_row"],
            move_data["from_col"],
            move_data["to_row"],
            move_data["to_col"]
        )
        
        if points_earned > 0:
            room["state"] = new_field
            room["scores"][websocket] += points_earned
            
            update_data = {
                "type": "update",
                "field": new_field,
                "scores": {
                    "you": room["scores"][websocket],
                    "opponent": room["scores"][room["p1"] if room["p2"] == websocket else room["p2"]]
                }
            }
            await room["p1"].send_json(update_data)
            await room["p2"].send_json(update_data)


manager = ConnectionManager()