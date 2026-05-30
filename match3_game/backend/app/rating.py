from sqlalchemy.orm import Session
from .database import User, MatchHistory


def calculate_pts_change(winner_pts: int, loser_pts: int) -> int:
    expected_win = 1 / (1 + 10 ** ((loser_pts - winner_pts) / 400))
    change = int(25 * (1 - expected_win))
    return max(5, min(change, 40))


def update_pts_after_match(db: Session, winner_id: int, loser_id: int, winner_score: int, loser_score: int) -> dict:
    winner = db.query(User).filter(User.id == winner_id).first()
    loser = db.query(User).filter(User.id == loser_id).first()
    
    if not winner or not loser:
        return {"error": "User not found"}
    
    pts_change = calculate_pts_change(winner.pts_multiplayer, loser.pts_multiplayer)
    
    winner.pts_multiplayer += pts_change
    loser.pts_multiplayer -= pts_change
    
    match = MatchHistory(
        player1_id=winner_id,
        player2_id=loser_id,
        winner_id=winner_id,
        player1_score=winner_score,
        player2_score=loser_score,
        pts_change=pts_change
    )
    db.add(match)
    db.commit()
    
    return {
        "winner_new_pts": winner.pts_multiplayer,
        "loser_new_pts": loser.pts_multiplayer,
        "pts_change": pts_change
    }


def update_solo_record(db: Session, user_id: int, new_score: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    if new_score > user.pts_solo_record:
        user.pts_solo_record = new_score
        db.commit()
        return True
    return False