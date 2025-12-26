import os
import math
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from fastapi import (
    FastAPI, UploadFile, File, Depends, BackgroundTasks, HTTPException
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
from pydantic import BaseModel, Field

import stripe

app = FastAPI()  # Critical: App instance was missing

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "dev_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./turnai_full_utils.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("turnai")

# -----------------------------------------------------------------------------
# Auth setup
# -----------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain, hashed): 
    try:
        return pwd_context.verify(plain[:72], hashed)
    except Exception:
        import hashlib
        return hashlib.sha256(plain[:72].encode()).hexdigest() == hashed

def hash_password(password): 
    try:
        return pwd_context.hash(password[:72])
    except Exception:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class Cleaner(Base):
    __tablename__ = "cleaners"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    rating = Column(Float, default=4.8)
    available = Column(Boolean, default=True)
    stripe_account_id = Column(String(100), unique=True)
    fcm_token = Column(String(255))
    password_hash = Column(String(255))
    assigned_jobs = relationship("Job", back_populates="assigned_cleaner")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    estimated_price = Column(Float, nullable=False)
    status = Column(String(20), default="pending")
    assigned_cleaner_id = Column(Integer, ForeignKey("cleaners.id"))
    payment_intent_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_cleaner = relationship("Cleaner", back_populates="assigned_jobs")

Base.metadata.create_all(bind=engine)

# -----------------------------------------------------------------------------
# Pydantic schemas
# -----------------------------------------------------------------------------
class CleanerCreate(BaseModel):
    name: str
    lat: float
    lon: float
    password: str
    stripe_account_id: Optional[str] = None
    fcm_token: Optional[str] = None

class JobCreate(BaseModel):
    description: str = Field(..., min_length=10, max_length=500)
    lat: float
    lon: float

class JobResponse(BaseModel):
    job_id: int
    estimated_price: float
    status: str
    assigned_to: Optional[int]
    issues: List[str]
    created_at: datetime

# -----------------------------------------------------------------------------
# Utils
# -----------------------------------------------------------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def analyze_images(files: List[UploadFile]) -> Dict[str, object]:
    base_price = 250.0
    issues = ["simulated clutter", "minor bathroom staining"]
    cleanliness_score = 82
    adjustment = (100 - cleanliness_score) * 3.5
    estimated_price = max(150.0, min(600.0, base_price + adjustment))
    return {"estimated_price": round(estimated_price, 2), "issues": issues}

def get_nearby_cleaners(db: Session, lat, lon, max_distance_km=25.0, limit=5):
    cleaners = db.query(Cleaner).filter(Cleaner.available.is_(True)).all()
    nearby = [(c, haversine_distance(lat, lon, c.lat, c.lon)) for c in cleaners]
    return [c for c, d in sorted(nearby, key=lambda x: (x[1], -x[0].rating)) if d <= max_distance_km][:limit]

async def notify_cleaners(cleaners: List[Cleaner], job_id: int):
    logger.info(f"Notify {len(cleaners)} cleaners about job {job_id}")

# -----------------------------------------------------------------------------
# Middlewares and routes
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"{request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Status {response.status_code}")
    return response

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/support")
def support():
    return {"ko_fi": "https://ko-fi.com/bryantolbert"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Cleaner).filter(Cleaner.name == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        # Debug info for troubleshooting
        print(f"Login attempt for: {form_data.username}")
        if user:
            print(f"User found, password verification failed")
            print(f"Stored hash: {user.password_hash}")
        else:
            print("User not found")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.name})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/cleaners/register")
def register_cleaner(data: CleanerCreate, db: Session = Depends(get_db)):
    db_cleaner = Cleaner(
        name=data.name, lat=data.lat, lon=data.lon,
        stripe_account_id=data.stripe_account_id, fcm_token=data.fcm_token,
        password_hash=hash_password(data.password)
    )
    db.add(db_cleaner)
    db.commit()
    db.refresh(db_cleaner)
    return {"cleaner_id": db_cleaner.id}

@app.post("/jobs/create", response_model=JobResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    job_data: JobCreate,
    photos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    ai_result = analyze_images(photos)
    new_job = Job(
        host_id=current_user,
        description=job_data.description,
        lat=job_data.lat,
        lon=job_data.lon,
        estimated_price=ai_result["estimated_price"]
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    nearby = get_nearby_cleaners(db, job_data.lat, job_data.lon)
    assigned_id = None
    if nearby:
        top = nearby[0]
        new_job.assigned_cleaner_id = top.id
        new_job.status = "assigned"
        db.commit()
        background_tasks.add_task(notify_cleaners, nearby[:3], new_job.id)
        assigned_id = top.id
    return JobResponse(
        job_id=new_job.id,
        estimated_price=new_job.estimated_price,
        status=new_job.status,
        assigned_to=assigned_id,
        issues=ai_result["issues"],
        created_at=new_job.created_at
  )
