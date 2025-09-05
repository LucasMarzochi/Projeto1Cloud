import os
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.exc import OperationalError
import time

# ---------- Config ----------
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASS = os.getenv("DB_PASS", "app_pass")
DB_HOST = os.getenv("DB_HOST", "database")
DB_NAME = os.getenv("DB_NAME", "app_db")
DB_URL  = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = "HS256"
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "120"))

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ---------- Models ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    tasks = relationship("Task", back_populates="owner", cascade="all,delete")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    status = Column(Enum("todo","doing","done", name="task_status"), default="todo")
    priority = Column(Enum("low","medium","high", name="task_priority"), default="medium")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="tasks")

# ---------- Schemas ----------
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

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
        from_attributes = True

# ---------- Helpers ----------
def hash_pw(p: str) -> str: return pwd.hash(p)
def check_pw(p: str, h: str) -> bool: return pwd.verify(p, h)

def mk_token(user: User) -> str:
    now = datetime.utcnow()
    payload = {"sub": str(user.id), "email": user.email, "name": user.name,
               "iat": now, "exp": now + timedelta(minutes=JWT_EXPIRES_MIN)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def get_db() -> Session:
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_current_user(authorization: Optional[str] = Header(default=None),
                     db: Session = Depends(get_db)) -> User:
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

# ---------- App ----------
app = FastAPI(title="Tuesday API")

@app.on_event("startup")
def _auto_migrate_with_retry():
    # tenta criar as tabelas com retry (MySQL pode demorar a ficar pronto)
    for _ in range(30):
        try:
            Base.metadata.create_all(engine)
            return
        except OperationalError:
            time.sleep(2)

@app.get("/health")
def health():
    return {"status": "ok", "service": "api"}

# ---- Auth ----
@app.post("/auth/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=payload.email).first():
        raise HTTPException(status_code=409, detail="email in use")
    u = User(email=payload.email, name=payload.name, password_hash=hash_pw(payload.password))
    db.add(u); db.commit(); db.refresh(u)
    return {"accessToken": mk_token(u)}

@app.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=payload.email).first()
    if not u or not check_pw(payload.password, u.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"accessToken": mk_token(u)}

# ---- Tasks ----
@app.get("/api/tasks", response_model=List[TaskOut])
def list_tasks(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Task).filter_by(owner_id=current.id).order_by(Task.start_at).all()

@app.post("/api/tasks", status_code=201)
def create_task(payload: TaskIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = Task(owner_id=current.id, **payload.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return {"id": t.id}

@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, payload: TaskIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Task).filter_by(id=task_id, owner_id=current.id).first()
    if not t: raise HTTPException(status_code=404, detail="not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    return {"id": t.id}

@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Task).filter_by(id=task_id, owner_id=current.id).first()
    if not t: raise HTTPException(status_code=404, detail="not found")
    db.delete(t); db.commit()
    return
