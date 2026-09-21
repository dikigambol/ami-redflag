import os
import json
import base64
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# Initialize Firebase Admin SDK (Supports Vercel Env Variables & Local File)
cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
cred_json_env = (
    os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    or os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    or os.getenv("FIREBASE_CREDENTIALS_JSON")
)
cred_b64_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_B64")

if not firebase_admin._apps:
    cred = None

    # 1. Cek kredensial dari Base64 Environment Variable (Rekomendasi Vercel: bebas escape newline)
    if cred_b64_env:
        try:
            raw_decoded = base64.b64decode(cred_b64_env).decode("utf-8")
            cert_dict = json.loads(raw_decoded)
            cred = credentials.Certificate(cert_dict)
        except Exception as e:
            print(f"[Firebase] Gagal memuat kredensial dari Base64 env: {e}")

    # 2. Cek kredensial dari Raw JSON Environment Variable
    if not cred and cred_json_env:
        try:
            cert_dict = json.loads(cred_json_env)
            if "private_key" in cert_dict and isinstance(cert_dict["private_key"], str):
                cert_dict["private_key"] = cert_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cert_dict)
        except Exception as e:
            print(f"[Firebase] Gagal memuat kredensial dari JSON env: {e}")

    # 3. Cek file lokal serviceAccountKey.json (Development lokal)
    if not cred and os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
        except Exception as e:
            print(f"[Firebase] Gagal memuat file sertifikat lokal: {e}")

    if cred:
        firebase_app = firebase_admin.initialize_app(cred)
    else:
        # Fallback default Google Application Credentials jika tersedia
        firebase_app = firebase_admin.initialize_app()
else:
    firebase_app = firebase_admin.get_app()

db = firestore.client()

# Collection References
USERS_COL = "users"
SESSIONS_COL = "game_sessions"
VISITORS_COL = "visitors"
STATS_COL = "site_stats"


class User:
    def __init__(
        self,
        id: str,
        google_id: Optional[str] = None,
        email: str = "",
        name: Optional[str] = None,
        picture: Optional[str] = None,
        trial_used: int = 0,
        max_trials: int = 3,
        created_at: Any = None,
        last_login: Any = None,
    ):
        self.id = str(id)
        self.google_id = google_id
        self.email = email
        self.name = name
        self.picture = picture
        self.trial_used = trial_used if trial_used is not None else 0
        self.max_trials = max_trials if max_trials is not None else 3
        self.created_at = created_at
        self.last_login = last_login

    def to_dict(self) -> Dict[str, Any]:
        remaining = max(0, self.max_trials - self.trial_used)
        
        c_at = self.created_at
        if hasattr(c_at, "isoformat"):
            c_at = c_at.isoformat()
        elif isinstance(c_at, datetime):
            c_at = c_at.isoformat()
            
        l_login = self.last_login
        if hasattr(l_login, "isoformat"):
            l_login = l_login.isoformat()
        elif isinstance(l_login, datetime):
            l_login = l_login.isoformat()

        return {
            "id": self.id,
            "google_id": self.google_id,
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "trial_used": self.trial_used,
            "max_trials": self.max_trials,
            "remaining_trials": remaining,
            "has_quota": remaining > 0,
            "created_at": str(c_at) if c_at else None,
            "last_login": str(l_login) if l_login else None,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: Dict[str, Any]) -> "User":
        return cls(
            id=doc_id,
            google_id=data.get("google_id"),
            email=data.get("email", ""),
            name=data.get("name"),
            picture=data.get("picture"),
            trial_used=data.get("trial_used", 0),
            max_trials=data.get("max_trials", 3),
            created_at=data.get("created_at"),
            last_login=data.get("last_login"),
        )


class GameSession:
    def __init__(
        self,
        id: str,
        user_id: str,
        player_name: str = "Pengguna",
        player_gender: str = "Laki-laki",
        status: str = "in_progress",
        redflag_score: Optional[int] = None,
        category: Optional[str] = None,
        title_eval: Optional[str] = None,
        analisis: Optional[str] = None,
        saran: Optional[str] = None,
        dimensi: Optional[Dict[str, Any]] = None,
        created_at: Any = None,
    ):
        self.id = str(id)
        self.user_id = str(user_id)
        self.player_name = player_name
        self.player_gender = player_gender
        self.status = status
        self.redflag_score = redflag_score
        self.category = category
        self.title_eval = title_eval
        self.analisis = analisis
        self.saran = saran
        self.dimensi = dimensi or {}
        self.created_at = created_at

    def to_dict(self) -> Dict[str, Any]:
        c_at_str = None
        if self.created_at:
            if hasattr(self.created_at, "strftime"):
                c_at_str = self.created_at.strftime("%d %b %Y, %H:%M")
            else:
                c_at_str = str(self.created_at)[:16]

        return {
            "id": self.id,
            "user_id": self.user_id,
            "player_name": self.player_name or "Pengguna",
            "player_gender": self.player_gender or "Laki-laki",
            "status": self.status,
            "redflag_score": self.redflag_score,
            "category": self.category or "Assessment Selesai",
            "title_eval": self.title_eval or "Evaluasi Percakapan",
            "analisis": self.analisis,
            "saran": self.saran,
            "dimensi": self.dimensi,
            "created_at": c_at_str,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: Dict[str, Any]) -> "GameSession":
        return cls(
            id=doc_id,
            user_id=data.get("user_id", ""),
            player_name=data.get("player_name", "Pengguna"),
            player_gender=data.get("player_gender", "Laki-laki"),
            status=data.get("status", "in_progress"),
            redflag_score=data.get("redflag_score"),
            category=data.get("category"),
            title_eval=data.get("title_eval"),
            analisis=data.get("analisis"),
            saran=data.get("saran"),
            dimensi=data.get("dimensi") or {},
            created_at=data.get("created_at"),
        )


# ==============================================================================
# FIRESTORE DATABASE OPERATIONS
# ==============================================================================

def init_db():
    """Initializes site stats collections if not yet existing."""
    try:
        total_doc = db.collection(STATS_COL).document("total_views").get()
        if not total_doc.exists:
            db.collection(STATS_COL).document("total_views").set({"stat_value": 0})

        unique_doc = db.collection(STATS_COL).document("unique_visitors").get()
        if not unique_doc.exists:
            db.collection(STATS_COL).document("unique_visitors").set({"stat_value": 0})
        print(f"[Firebase] Firestore connected and initialized (Project: {firebase_app.project_id})")
    except Exception as e:
        print(f"[Firebase] Init notice: {e}")


def get_or_create_user(
    google_id: str,
    email: str,
    name: Optional[str] = None,
    picture: Optional[str] = None,
) -> User:
    """Finds existing user by google_id or email, or creates a new one in Firestore."""
    users_ref = db.collection(USERS_COL)
    user_doc = None
    doc_id = None

    # 1. Search by google_id
    if google_id:
        query = users_ref.where("google_id", "==", str(google_id)).limit(1).get()
        if query:
            user_doc = query[0]
            doc_id = user_doc.id

    # 2. Search by email if not found by google_id
    if not user_doc and email:
        query = users_ref.where("email", "==", email.lower().strip()).limit(1).get()
        if query:
            user_doc = query[0]
            doc_id = user_doc.id

    now = datetime.utcnow()

    if user_doc:
        data = user_doc.to_dict()
        updates = {"last_login": now}
        if google_id and not data.get("google_id"):
            updates["google_id"] = str(google_id)
        if picture and not data.get("picture"):
            updates["picture"] = picture
        if name and not data.get("name"):
            updates["name"] = name
        users_ref.document(doc_id).update(updates)
        data.update(updates)
        return User.from_doc(doc_id, data)
    else:
        new_data = {
            "google_id": str(google_id) if google_id else None,
            "email": email.lower().strip(),
            "name": name or (email.split("@")[0] if email else "User"),
            "picture": picture,
            "trial_used": 0,
            "max_trials": 3,
            "created_at": now,
            "last_login": now,
        }
        _, new_ref = users_ref.add(new_data)
        return User.from_doc(new_ref.id, new_data)


def get_user_by_id(user_id: str) -> Optional[User]:
    """Retrieves user by Firestore document ID."""
    if not user_id:
        return None
    doc = db.collection(USERS_COL).document(str(user_id)).get()
    if doc.exists:
        return User.from_doc(doc.id, doc.to_dict())
    return None


def increment_user_trial(user_id: str):
    """Increments the user's trial_used count by 1."""
    if not user_id:
        return
    db.collection(USERS_COL).document(str(user_id)).update({
        "trial_used": firestore.Increment(1)
    })


def create_game_session(
    user_id: str,
    player_name: str,
    player_gender: str
) -> str:
    """Creates a new game session in Firestore with status 'in_progress'."""
    now = datetime.utcnow()
    sess_data = {
        "user_id": str(user_id),
        "player_name": player_name,
        "player_gender": player_gender,
        "status": "in_progress",
        "redflag_score": None,
        "category": None,
        "title_eval": None,
        "analisis": None,
        "saran": None,
        "dimensi": {},
        "created_at": now,
    }
    _, ref = db.collection(SESSIONS_COL).add(sess_data)
    return ref.id


def complete_game_session(
    user_id: str,
    eval_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Optional[str]:
    """
    Saves complete evaluation resume to Firestore.
    If session_id is not specified, updates the latest 'in_progress' session for the user.
    """
    sessions_ref = db.collection(SESSIONS_COL)
    target_doc_id = None

    if session_id:
        target_doc_id = session_id
    else:
        # Query in_progress sessions for this user without requiring multi-field index
        try:
            query = sessions_ref.where("user_id", "==", str(user_id)).get()
            in_prog = [d for d in query if d.to_dict().get("status") == "in_progress"]
            if in_prog:
                in_prog.sort(key=lambda d: str(d.to_dict().get("created_at") or ""), reverse=True)
                target_doc_id = in_prog[0].id
        except Exception as e:
            print(f"[Firebase] complete_game_session lookup notice: {e}")

    if not target_doc_id:
        # Fallback: create a completed session document directly
        now = datetime.utcnow()
        new_sess = {
            "user_id": str(user_id),
            "player_name": "Pengguna",
            "player_gender": "Laki-laki",
            "status": "completed",
            "redflag_score": eval_data.get("skor_red_flag"),
            "category": eval_data.get("kategori"),
            "title_eval": eval_data.get("julukan"),
            "analisis": eval_data.get("analisis"),
            "saran": eval_data.get("saran"),
            "dimensi": eval_data.get("dimensi") or {},
            "created_at": now,
            "completed_at": now,
        }
        _, ref = sessions_ref.add(new_sess)
        return ref.id

    updates = {
        "status": "completed",
        "redflag_score": eval_data.get("skor_red_flag"),
        "category": eval_data.get("kategori"),
        "title_eval": eval_data.get("julukan"),
        "analisis": eval_data.get("analisis"),
        "saran": eval_data.get("saran"),
        "dimensi": eval_data.get("dimensi") or {},
        "completed_at": datetime.utcnow(),
    }
    sessions_ref.document(target_doc_id).update(updates)
    return target_doc_id


def get_user_history(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieves completed simulation sessions with full evaluation data for a user."""
    try:
        sessions_ref = db.collection(SESSIONS_COL)
        query = sessions_ref.where("user_id", "==", str(user_id)).get()
        result = []
        for doc in query:
            data = doc.to_dict()
            if data.get("status") == "completed":
                sess = GameSession.from_doc(doc.id, data)
                result.append(sess.to_dict())
        # Sort in memory by created_at desc (no composite index needed)
        result.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return result[:limit]
    except Exception as e:
        print(f"[Firebase] get_user_history error: {e}")
        return []


def record_visit(visitor_id: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
    """Records page visits and unique visitors in Firestore."""
    is_new = False
    vis_ref = db.collection(VISITORS_COL)
    
    if visitor_id:
        doc = vis_ref.document(str(visitor_id)).get()
        if not doc.exists:
            is_new = True
            vis_ref.document(str(visitor_id)).set({
                "visitor_id": str(visitor_id),
                "ip_address": ip_address,
                "user_agent": (user_agent or "")[:450],
                "created_at": datetime.utcnow(),
            })
    else:
        is_new = True

    stats_ref = db.collection(STATS_COL)
    stats_ref.document("total_views").update({"stat_value": firestore.Increment(1)})
    if is_new:
        stats_ref.document("unique_visitors").update({"stat_value": firestore.Increment(1)})

    t_val = 1
    u_val = 1
    try:
        t_doc = stats_ref.document("total_views").get()
        if t_doc.exists:
            t_val = t_doc.to_dict().get("stat_value", 1)
        u_doc = stats_ref.document("unique_visitors").get()
        if u_doc.exists:
            u_val = u_doc.to_dict().get("stat_value", 1)
    except Exception:
        pass

    return {
        "visitor_id": visitor_id,
        "total_views": t_val,
        "unique_visitors": u_val,
    }


def get_site_stats() -> Dict[str, int]:
    """Fetches total_views and unique_visitors from Firestore."""
    stats_ref = db.collection(STATS_COL)
    t_val = 0
    u_val = 0
    try:
        t_doc = stats_ref.document("total_views").get()
        if t_doc.exists:
            t_val = t_doc.to_dict().get("stat_value", 0)
        u_doc = stats_ref.document("unique_visitors").get()
        if u_doc.exists:
            u_val = u_doc.to_dict().get("stat_value", 0)
    except Exception:
        pass
    return {
        "total_views": t_val,
        "unique_visitors": u_val,
    }
