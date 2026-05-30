from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from . import database
from .database import get_db, User, SessionLocal
from .auth import hash_password, verify_password, create_access_token, decode_token, generate_verification_code
from .email_utils import send_verification_email
from .rating import update_pts_after_match, update_solo_record
from .websocket_manager import manager
from .game_logic import generate_field

load_dotenv()

app = FastAPI(title="ВесёлыйРяд API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ---------- Pydantic модели ----------
class UserRegister(BaseModel):
    email: EmailStr
    nickname: str
    password: str

class VerifyEmail(BaseModel):
    email: str
    code: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class SoloScoreSubmit(BaseModel):
    score: int

class AvatarUpload(BaseModel):
    avatar_url: str

# ---------- Вспомогательные функции ----------
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user

def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(403, "Доступ запрещён. Только для администраторов.")
    return current_user

# ---------- Публичные эндпоинты ----------
@app.get("/")
def root():
    return {"message": "ВесёлыйРяд API", "version": "1.0.0"}

@app.get("/api/generate-field")
def generate_game_field():
    return {"field": generate_field()}

@app.post("/api/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.email == user.email) | (User.nickname == user.nickname)
    ).first()
    if existing:
        raise HTTPException(400, "Email or nickname already taken")
    
    code = generate_verification_code()
    new_user = User(
        email=user.email,
        nickname=user.nickname,
        hashed_password=hash_password(user.password),
        verification_code=code,
        email_verified=0
    )
    db.add(new_user)
    db.commit()
    
    send_verification_email(user.email, code)
    return {"message": "Verification code sent to email"}

@app.post("/api/verify-email")
def verify_email(verify: VerifyEmail, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == verify.email).first()
    if not user or user.verification_code != verify.code:
        raise HTTPException(400, "Invalid code")
    user.email_verified = 1
    user.verification_code = None
    db.commit()
    return {"message": "Email verified successfully"}

@app.post("/api/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(401, "Wrong credentials")
    if not db_user.email_verified:
        raise HTTPException(403, "Email not verified")
    
    token = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "nickname": current_user.nickname,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url,
        "pts_multiplayer": current_user.pts_multiplayer,
        "pts_solo_record": current_user.pts_solo_record,
        "is_admin": current_user.is_admin == 1
    }

@app.get("/api/profile/{user_id}")
def get_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "pts_multiplayer": user.pts_multiplayer,
        "pts_solo_record": user.pts_solo_record
    }

@app.post("/api/avatar")
async def update_avatar(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        data = await request.json()
        avatar_url = data.get("avatar_url")
        if avatar_url:
            current_user.avatar_url = avatar_url
            db.commit()
            return {"message": "Avatar updated", "avatar_url": current_user.avatar_url}
        return {"error": "No avatar data"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/solo-score")
def submit_solo_score(score_data: SoloScoreSubmit, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    was_record = update_solo_record(db, current_user.id, score_data.score)
    return {
        "message": "Score saved",
        "was_record": was_record,
        "current_record": current_user.pts_solo_record
    }

@app.get("/api/leaderboard/multi")
def leaderboard_multi(limit: int = 50, db: Session = Depends(get_db)):
    top = db.query(User).order_by(User.pts_multiplayer.desc()).limit(limit).all()
    return [{"nickname": u.nickname, "pts": u.pts_multiplayer, "avatar": u.avatar_url} for u in top]

@app.get("/api/leaderboard/solo")
def leaderboard_solo(limit: int = 50, db: Session = Depends(get_db)):
    top = db.query(User).order_by(User.pts_solo_record.desc()).limit(limit).all()
    return [{"nickname": u.nickname, "record": u.pts_solo_record, "avatar": u.avatar_url} for u in top]

# ---------- АДМИН ЭНДПОИНТЫ ----------
@app.get("/api/admin/users")
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "nickname": u.nickname,
            "email": u.email,
            "pts_multiplayer": u.pts_multiplayer,
            "pts_solo_record": u.pts_solo_record,
            "email_verified": u.email_verified == 1,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "is_admin": u.is_admin == 1
        }
        for u in users
    ]

@app.get("/api/admin/users/{user_id}")
def get_user_by_id(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    return {
        "id": user.id,
        "nickname": user.nickname,
        "email": user.email,
        "pts_multiplayer": user.pts_multiplayer,
        "pts_solo_record": user.pts_solo_record,
        "email_verified": user.email_verified == 1,
        "is_admin": user.is_admin == 1
    }

@app.delete("/api/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    db.delete(user)
    db.commit()
    return {"message": f"Пользователь {user.nickname} удалён"}

@app.post("/api/admin/make-admin/{user_id}")
def make_admin(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    user.is_admin = 1
    db.commit()
    return {"message": f"Пользователь {user.nickname} теперь администратор"}

@app.post("/api/admin/remove-admin/{user_id}")
def remove_admin(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    user.is_admin = 0
    db.commit()
    return {"message": f"Пользователь {user.nickname} больше не администратор"}

@app.post("/api/admin/reset-solo")
def reset_solo_ranking(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    db.query(User).update({User.pts_solo_record: 0})
    db.commit()
    return {"message": "Соло рейтинг сброшен"}

@app.post("/api/admin/reset-multi")
def reset_multi_ranking(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    db.query(User).update({User.pts_multiplayer: 1000})
    db.commit()
    return {"message": "Мультиплеер рейтинг сброшен к 1000"}

@app.post("/api/admin/reset-solo-user/{user_id}")
def reset_solo_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    user.pts_solo_record = 0
    db.commit()
    return {"message": f"Соло рекорд {user.nickname} сброшен"}

@app.post("/api/admin/reset-multi-user/{user_id}")
def reset_multi_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    user.pts_multiplayer = 1000
    db.commit()
    return {"message": f"PTS {user.nickname} сброшен до 1000"}

@app.get("/api/admin/stats")
def get_stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    total_users = db.query(User).count()
    total_verified = db.query(User).filter(User.email_verified == 1).count()
    total_admins = db.query(User).filter(User.is_admin == 1).count()
    avg_multi = db.query(User.pts_multiplayer).all()
    avg_solo = db.query(User.pts_solo_record).all()
    
    from statistics import mean
    return {
        "total_users": total_users,
        "verified_users": total_verified,
        "total_admins": total_admins,
        "avg_multiplayer_pts": round(mean([m[0] for m in avg_multi]), 2) if avg_multi else 1000,
        "avg_solo_record": round(mean([s[0] for s in avg_solo]), 2) if avg_solo else 0,
        "top_multiplayer": db.query(User).order_by(User.pts_multiplayer.desc()).first().nickname if total_users > 0 else None,
        "top_solo": db.query(User).order_by(User.pts_solo_record.desc()).first().nickname if total_users > 0 else None
    }

# ---------- WebSocket ----------
@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    user_id = int(payload.get("sub"))
    
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    
    if not user:
        await websocket.close(code=1008, reason="User not found")
        return
    
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            import json
            message = json.loads(data)
            
            if message["type"] == "find_match":
                await manager.matchmake(websocket, user_id, user.nickname)
            elif message["type"] == "move":
                await manager.handle_move(message["room_id"], websocket, message)
            elif message["type"] == "cancel_search":
                for i, p in enumerate(manager.waiting_queue):
                    if p["websocket"] == websocket:
                        manager.waiting_queue.pop(i)
                        await websocket.send_json({"type": "search_cancelled"})
                        break
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ---------- Startup (создание тестовых пользователей) ----------
@app.on_event("startup")
def startup():
    database.Base.metadata.create_all(bind=database.engine)
    
    db = SessionLocal()
    try:
        # Администратор
        admin_user = db.query(User).filter(User.email == "test@match3.com").first()
        if not admin_user:
            admin_user = User(
                email="test@match3.com",
                nickname="Администратор",
                hashed_password=hash_password("123456"),
                email_verified=1,
                pts_multiplayer=1000,
                pts_solo_record=0,
                is_admin=1
            )
            db.add(admin_user)
            print("✅ Тестовый АДМИН: test@match3.com / 123456")
        
        # Обычный игрок
        player_user = db.query(User).filter(User.email == "player@test.com").first()
        if not player_user:
            player_user = User(
                email="player@test.com",
                nickname="Игрок",
                hashed_password=hash_password("123456"),
                email_verified=1,
                pts_multiplayer=1000,
                pts_solo_record=0,
                is_admin=0
            )
            db.add(player_user)
            print("✅ Тестовый ИГРОК: player@test.com / 123456")
        
        db.commit()
        
    except Exception as e:
        print(f"Ошибка при создании тестовых пользователей: {e}")
    finally:
        db.close()
    
    print("✅ Database ready")
    print("🚀 Сервер запущен на http://localhost:8000")
    print("📖 API docs: http://localhost:8000/docs")