# /srv/app/main.py
import os, re, time
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, field_validator
from jose import jwt, JWTError

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Enum, ForeignKey, Text, inspect, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.exc import OperationalError, IntegrityError, ProgrammingError

# ---------------- Password hashing ----------------
# usa pbkdf2_sha256 (puro Python) por padrão; se bcrypt estiver presente, também é aceito
from passlib.context import CryptContext
PWD_CTX = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# ---------------- Config do DB ----------------
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASS = os.getenv("DB_PASS", "app_pass")
DB_NAME = os.getenv("DB_NAME", "app_db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

# Pode definir DB_HOSTS="database,192.168.90.30" (ordem de tentativa)
DB_HOSTS = [h.strip() for h in os.getenv("DB_HOSTS", os.getenv("DB_HOST", "database")).split(",") if h.strip()]

def make_db_url(host: str) -> str:
    return (f"mysql+pymysql://{DB_USER}:{DB_PASS}@{host}:{DB_PORT}/{DB_NAME}"
            f"?charset=utf8mb4&connect_timeout=5")

_engine = None        # engine atual
_engine_host = None   # host atual (para debug/health)

def _create_engine_for(host: str):
    return create_engine(
        make_db_url(host),
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=5,
        max_overflow=10,
        future=True,
    )

def _dispose_engine():
    global _engine
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass
    _engine = None

def pick_engine_with_retry(max_attempts: int = 90):
    """
    Escolhe um host válido com retry (até ~90s).
    """
    global _engine, _engine_host
    wait = 1
    for _ in range(max_attempts):
        for host in DB_HOSTS:
            try:
                eng = _create_engine_for(host)
                with eng.connect() as conn:
                    conn.execute(text("SELECT 1"))
                _engine, _engine_host = eng, host
                return
            except Exception:
                continue
        time.sleep(wait)
        wait = min(5, wait + 1)
    raise RuntimeError("Could not connect to any DB host")

def get_engine():
    global _engine
    if _engine is None:
        pick_engine_with_retry()
    return _engine

# sessionmaker sem bind fixo; ligamos no engine a cada request
SessionLocal = sessionmaker(autoflush=False, autocommit=False, future=True)

def db_session() -> Session:
    """
    Dependência de sessão. Se o pool cair, transforma em 503 e
    força recriação do engine no próximo request.
    """
    try:
        db = SessionLocal(bind=get_engine())
        try:
            yield db
        finally:
            db.close()
    except OperationalError:
        _dispose_engine()
        raise HTTPException(status_code=503, detail="database unavailable")

# ---------------- JWT ----------------
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = "HS256"
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "120"))

# ---------------- Models ----------------
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    tasks = relationship("Task", back_populates="owner", cascade="all,delete")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    status = Column(Enum("todo","doing","done", name="task_status"), default="todo")
    priority = Column(Enum("low","medium","high", name="task_priority"), default="medium")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="tasks")

# ---------------- Schemas ----------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class RegisterIn(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.fullmatch(v):
            raise ValueError("invalid email format")
        return v

class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.fullmatch(v):
            raise ValueError("invalid email format")
        return v

class TaskIn(BaseModel):
    title: str
    description: Optional[str] = None
    start_at: datetime
    end_at: datetime
    status: Optional[str] = "todo"
    priority: Optional[str] = "medium"

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    start_at: datetime
    end_at: datetime
    status: str
    priority: str
    class Config:
        from_attributes = True  # Pydantic v2

# ---------------- Helpers ----------------
def hash_pw(p: str) -> str:
    return PWD_CTX.hash(p)

def check_pw(p: str, h: str) -> bool:
    try:
        return PWD_CTX.verify(p, h)
    except Exception:
        return False

def mk_token(user: User) -> str:
    now = datetime.utcnow()
    payload = {"sub": str(user.id), "email": user.email, "name": user.name,
               "iat": now, "exp": now + timedelta(minutes=JWT_EXPIRES_MIN)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def get_current_user(authorization: Optional[str] = Header(default=None),
                     db: Session = Depends(db_session)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = authorization[7:]
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        uid = int(data["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid token")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user

def ensure_schema(db: Session) -> None:
    """
    Garante que 'users' e 'tasks' existam. Evita 500 se o primeiro request
    chegar antes do create_all do startup.
    """
    try:
        bind = db.get_bind()
        insp = inspect(bind)
        need = (not insp.has_table("users")) or (not insp.has_table("tasks"))
    except Exception:
        need = True
    if need:
        Base.metadata.create_all(bind=bind)

# ---------------- App & startup ----------------
app = FastAPI(title="Tuesday API")

@app.on_event("startup")
def _startup_migrate():
    # escolhe host OK e cria tabelas com retry curto
    pick_engine_with_retry()
    for _ in range(60):
        try:
            Base.metadata.create_all(get_engine())
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            time.sleep(1)

# ---------------- Endpoints ----------------
@app.get("/health")
def health():
    try:
        with get_engine().connect() as conn:
            ok = conn.execute(text("SELECT 1")).scalar() == 1
        return {"status": "ok" if ok else "degraded", "service": "api", "db_host": _engine_host}
    except Exception:
        return {"status": "degraded", "service": "api", "db_host": _engine_host}

# ---- Auth ----
@app.post("/auth/register")
def register(payload: RegisterIn, db: Session = Depends(db_session)):
    try:
        ensure_schema(db)
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=409, detail="email already in use")

        u = User(email=payload.email,
                 name=payload.name.strip(),
                 password_hash=hash_pw(payload.password))
        db.add(u); db.commit(); db.refresh(u)
        return {"accessToken": mk_token(u)}

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="email already in use")
    except (OperationalError, ProgrammingError):
        db.rollback(); _dispose_engine()
        raise HTTPException(status_code=503, detail="database unavailable")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"register failed: {type(e).__name__}")

@app.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(db_session)):
    try:
        ensure_schema(db)
        u = db.query(User).filter(User.email == payload.email).first()
    except (OperationalError, ProgrammingError):
        _dispose_engine()
        raise HTTPException(status_code=503, detail="database unavailable")
    if not u or not check_pw(payload.password, u.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"accessToken": mk_token(u)}

# ---- Tasks ----
@app.get("/api/tasks", response_model=List[TaskOut])
def list_tasks(current: User = Depends(get_current_user), db: Session = Depends(db_session)):
    try:
        ensure_schema(db)
        return (db.query(Task)
                .filter_by(owner_id=current.id)
                .order_by(Task.start_at).all())
    except (OperationalError, ProgrammingError):
        _dispose_engine()
        raise HTTPException(status_code=503, detail="database unavailable")

@app.post("/api/tasks", status_code=201)
def create_task(payload: TaskIn, current: User = Depends(get_current_user), db: Session = Depends(db_session)):
    if payload.end_at <= payload.start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")
    try:
        ensure_schema(db)
        t = Task(owner_id=current.id, **payload.model_dump())
        db.add(t); db.commit(); db.refresh(t)
        return {"id": t.id}
    except (OperationalError, ProgrammingError):
        db.rollback(); _dispose_engine()
        raise HTTPException(status_code=503, detail="database unavailable")

@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, payload: TaskIn, current: User = Depends(get_current_user), db: Session = Depends(db_session)):
    try:
        ensure_schema(db)
        t = db.query(Task).filter_by(id=task_id, owner_id=current.id).first()
    except (OperationalError, ProgrammingError):
        _dispose_engine()
        raise HTTPException(status_code=503, detail="database unavailable")
    if not t:
        raise HTTPException(status_code=404, detail="not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    try:
        db.commit()
        return {"id": t.id}
    except (OperationalError, ProgrammingError):
        db.rollback(); _dispose_engine()
        raise HTTPException(status_code=503, detail="database unavailable")

@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, current: User = Depends(get_current_user), db: Session = Depends(db_session)):
    try:
        ensure_schema(db)
        t = db.query(Task).filter_by(id=task_id, owner_id=current.id).first()
    except (OperationalError, ProgrammingError):
        _dispose_engine()
        raise HTTPException(status_code=503, detail="database unavailable")
    if not t:
        raise HTTPException(status_code=404, detail="not found")
    try:
        db.delete(t); db.commit()
        return
    except (OperationalError, ProgrammingError):
        db.rollback(); _dispose_engine()
        raise HTTPException(status_code=503, detail="database unavailable")
