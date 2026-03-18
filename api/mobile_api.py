"""
Mobile API for @seller_fuck_bot
FastAPI REST API с JWT аутентификацией и WebSocket поддержкой
"""

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import uvicorn
import asyncio
import json
from enum import Enum

# ==================== CONFIG ====================
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

DATABASE_URL = "sqlite:///./mobile_api.db"

# ==================== DATABASE SETUP ====================
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== ENUMS ====================
class MarketplaceType(str, Enum):
    WILDBERRIES = "wildberries"
    OZON = "ozon"
    AVITO = "avito"

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ContentType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"

class ContentStatus(str, Enum):
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    ERROR = "error"

class ABTestStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class SubscriptionTier(str, Enum):
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

# ==================== DATABASE MODELS ====================
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String, default=SubscriptionTier.STARTER)
    subscription_expires = Column(DateTime, nullable=True)
    tokens_balance = Column(Integer, default=0)
    
    # Relations
    analyses = relationship("Analysis", back_populates="user")
    contents = relationship("Content", back_populates="user")
    ab_tests = relationship("ABTest", back_populates="user")
    dashboard_data = relationship("DashboardData", back_populates="user", uselist=False)

class DashboardData(Base):
    __tablename__ = "dashboard_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Общие метрики
    total_sales = Column(Float, default=0.0)
    total_orders = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    
    # Wildberries
    wb_sales = Column(Float, default=0.0)
    wb_orders = Column(Integer, default=0)
    wb_revenue = Column(Float, default=0.0)
    wb_stock = Column(Integer, default=0)
    wb_rating = Column(Float, default=0.0)
    
    # Ozon
    ozon_sales = Column(Float, default=0.0)
    ozon_orders = Column(Integer, default=0)
    ozon_revenue = Column(Float, default=0.0)
    ozon_stock = Column(Integer, default=0)
    ozon_rating = Column(Float, default=0.0)
    
    # Avito
    avito_sales = Column(Float, default=0.0)
    avito_orders = Column(Integer, default=0)
    avito_revenue = Column(Float, default=0.0)
    avito_views = Column(Integer, default=0)
    avito_contacts = Column(Integer, default=0)
    
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="dashboard_data")

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    article = Column(String, nullable=False)
    marketplace = Column(String, nullable=False)
    status = Column(String, default=AnalysisStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Результаты анализа
    competitors_data = Column(JSON, nullable=True)
    price_analysis = Column(JSON, nullable=True)
    rating_analysis = Column(JSON, nullable=True)
    recommendations = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="analyses")

class Content(Base):
    __tablename__ = "contents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content_type = Column(String, nullable=False)  # photo или video
    status = Column(String, default=ContentStatus.QUEUED)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Параметры генерации
    product_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    style = Column(String, default="modern")
    
    # Результат
    file_path = Column(String, nullable=True)
    preview_url = Column(String, nullable=True)
    
    user = relationship("User", back_populates="contents")

class ABTest(Base):
    __tablename__ = "ab_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    status = Column(String, default=ABTestStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Параметры теста
    product_article = Column(String, nullable=False)
    marketplace = Column(String, nullable=False)
    variant_a = Column(JSON, nullable=False)  # {title, description, images}
    variant_b = Column(JSON, nullable=False)
    
    # Результаты
    variant_a_views = Column(Integer, default=0)
    variant_a_clicks = Column(Integer, default=0)
    variant_a_orders = Column(Integer, default=0)
    variant_b_views = Column(Integer, default=0)
    variant_b_clicks = Column(Integer, default=0)
    variant_b_orders = Column(Integer, default=0)
    winner = Column(String, nullable=True)  # 'A', 'B' или 'draw'
    
    user = relationship("User", back_populates="ab_tests")

# Создаём таблицы
Base.metadata.create_all(bind=engine)

# ==================== PYDANTIC MODELS ====================
# Auth models
class UserRegister(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenRefresh(BaseModel):
    refresh_token: str

# Dashboard models
class DashboardSummary(BaseModel):
    total_sales: float
    total_orders: int
    total_revenue: float
    conversion_rate: float
    last_updated: datetime

class DashboardWB(BaseModel):
    sales: float
    orders: int
    revenue: float
    stock: int
    rating: float
    last_updated: datetime

class DashboardOzon(BaseModel):
    sales: float
    orders: int
    revenue: float
    stock: int
    rating: float
    last_updated: datetime

class DashboardAvito(BaseModel):
    sales: float
    orders: int
    revenue: float
    views: int
    contacts: int
    last_updated: datetime

# Analysis models
class AnalysisCreate(BaseModel):
    article: str
    marketplace: MarketplaceType

class AnalysisResponse(BaseModel):
    id: int
    article: str
    marketplace: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class AnalysisResult(BaseModel):
    id: int
    article: str
    marketplace: str
    status: str
    competitors_data: Optional[Dict]
    price_analysis: Optional[Dict]
    rating_analysis: Optional[Dict]
    recommendations: Optional[str]
    completed_at: Optional[datetime]

# Content models
class ContentCreate(BaseModel):
    content_type: ContentType
    product_name: str
    description: Optional[str] = None
    style: Optional[str] = "modern"

class ContentResponse(BaseModel):
    id: int
    content_type: str
    status: str
    product_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ContentResult(BaseModel):
    id: int
    content_type: str
    status: str
    product_name: str
    preview_url: Optional[str]
    file_path: Optional[str]
    completed_at: Optional[datetime]

# A/B Test models
class ABTestVariant(BaseModel):
    title: str
    description: str
    images: List[str]

class ABTestCreate(BaseModel):
    name: str
    product_article: str
    marketplace: MarketplaceType
    variant_a: ABTestVariant
    variant_b: ABTestVariant

class ABTestResponse(BaseModel):
    id: int
    name: str
    status: str
    product_article: str
    marketplace: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ABTestStatusResponse(BaseModel):
    id: int
    name: str
    status: str
    variant_a_stats: Dict[str, int]
    variant_b_stats: Dict[str, int]
    winner: Optional[str]

# ==================== SECURITY ====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ==================== DEPENDENCIES ====================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    phone: str = payload.get("sub")
    if phone is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.phone == phone).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

# ==================== FASTAPI APP ====================
app = FastAPI(
    title="Seller Fuck Bot API",
    description="Mobile API для анализа маркетплейсов и генерации контента",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== AUTH ENDPOINTS ====================
@app.post("/api/v1/auth/register", response_model=TokenResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь
    existing_user = db.query(User).filter(User.phone == user_data.phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Создаём пользователя
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        phone=user_data.phone,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Создаём дашборд для пользователя
    dashboard = DashboardData(user_id=new_user.id)
    db.add(dashboard)
    db.commit()
    
    # Генерируем токены
    access_token = create_access_token({"sub": new_user.phone})
    refresh_token = create_refresh_token({"sub": new_user.phone})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Вход в систему"""
    user = db.query(User).filter(User.phone == user_data.phone).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token({"sub": user.phone})
    refresh_token = create_refresh_token({"sub": user.phone})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """Обновление access token с помощью refresh token"""
    payload = decode_token(token_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    phone: str = payload.get("sub")
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token({"sub": user.phone})
    refresh_token = create_refresh_token({"sub": user.phone})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

# ==================== DASHBOARD ENDPOINTS ====================
@app.get("/api/v1/dashboard", response_model=DashboardSummary)
def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить общую сводку по всем маркетплейсам"""
    dashboard = db.query(DashboardData).filter(DashboardData.user_id == current_user.id).first()
    
    if not dashboard:
        dashboard = DashboardData(user_id=current_user.id)
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)
    
    return DashboardSummary(
        total_sales=dashboard.total_sales,
        total_orders=dashboard.total_orders,
        total_revenue=dashboard.total_revenue,
        conversion_rate=dashboard.conversion_rate,
        last_updated=dashboard.last_updated
    )

@app.get("/api/v1/dashboard/wb", response_model=DashboardWB)
def get_dashboard_wb(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Детальная статистика по Wildberries"""
    dashboard = db.query(DashboardData).filter(DashboardData.user_id == current_user.id).first()
    
    return DashboardWB(
        sales=dashboard.wb_sales,
        orders=dashboard.wb_orders,
        revenue=dashboard.wb_revenue,
        stock=dashboard.wb_stock,
        rating=dashboard.wb_rating,
        last_updated=dashboard.last_updated
    )

@app.get("/api/v1/dashboard/ozon", response_model=DashboardOzon)
def get_dashboard_ozon(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Детальная статистика по Ozon"""
    dashboard = db.query(DashboardData).filter(DashboardData.user_id == current_user.id).first()
    
    return DashboardOzon(
        sales=dashboard.ozon_sales,
        orders=dashboard.ozon_orders,
        revenue=dashboard.ozon_revenue,
        stock=dashboard.ozon_stock,
        rating=dashboard.ozon_rating,
        last_updated=dashboard.last_updated
    )

@app.get("/api/v1/dashboard/avito", response_model=DashboardAvito)
def get_dashboard_avito(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Детальная статистика по Авито"""
    dashboard = db.query(DashboardData).filter(DashboardData.user_id == current_user.id).first()
    
    return DashboardAvito(
        sales=dashboard.avito_sales,
        orders=dashboard.avito_orders,
        revenue=dashboard.avito_revenue,
        views=dashboard.avito_views,
        contacts=dashboard.avito_contacts,
        last_updated=dashboard.last_updated
    )

# ==================== ANALYSIS ENDPOINTS ====================
@app.post("/api/v1/analyze", response_model=AnalysisResponse)
def create_analysis(
    analysis_data: AnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Запустить анализ конкурентов"""
    # Проверяем лимиты пользователя
    user_tier = current_user.subscription_tier
    
    # TODO: Реализовать проверку лимитов по тарифу
    
    new_analysis = Analysis(
        user_id=current_user.id,
        article=analysis_data.article,
        marketplace=analysis_data.marketplace.value,
        status=AnalysisStatus.PENDING
    )
    db.add(new_analysis)
    db.commit()
    db.refresh(new_analysis)
    
    # TODO: Запустить фоновую задачу анализа
    
    return AnalysisResponse.model_validate(new_analysis)

@app.get("/api/v1/analyze/{analysis_id}/status")
def get_analysis_status(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статус анализа"""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "id": analysis.id,
        "status": analysis.status,
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at
    }

@app.get("/api/v1/analyze/{analysis_id}/result", response_model=AnalysisResult)
def get_analysis_result(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить результат анализа"""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.status != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Analysis is not completed yet. Current status: {analysis.status}"
        )
    
    return AnalysisResult.model_validate(analysis)

# ==================== CONTENT ENDPOINTS ====================
@app.post("/api/v1/content/create", response_model=ContentResponse)
def create_content(
    content_data: ContentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать задачу на генерацию фото/видео"""
    new_content = Content(
        user_id=current_user.id,
        content_type=content_data.content_type.value,
        product_name=content_data.product_name,
        description=content_data.description,
        style=content_data.style
    )
    db.add(new_content)
    db.commit()
    db.refresh(new_content)
    
    # TODO: Запустить фоновую генерацию контента
    
    return ContentResponse.model_validate(new_content)

@app.get("/api/v1/content/{content_id}/status")
def get_content_status(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статус генерации контента"""
    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {
        "id": content.id,
        "content_type": content.content_type,
        "status": content.status,
        "product_name": content.product_name,
        "created_at": content.created_at,
        "completed_at": content.completed_at
    }

@app.get("/api/v1/content/{content_id}/download")
def download_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Скачать сгенерированный контент"""
    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.status != ContentStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"Content is not ready yet. Current status: {content.status}"
        )
    
    # TODO: Реализовать скачивание файла
    return {
        "id": content.id,
        "download_url": content.file_path,
        "preview_url": content.preview_url
    }

# ==================== A/B TEST ENDPOINTS ====================
@app.post("/api/v1/abtest/create", response_model=ABTestResponse)
def create_abtest(
    test_data: ABTestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать A/B тест"""
    new_test = ABTest(
        user_id=current_user.id,
        name=test_data.name,
        product_article=test_data.product_article,
        marketplace=test_data.marketplace.value,
        variant_a=test_data.variant_a.model_dump(),
        variant_b=test_data.variant_b.model_dump()
    )
    db.add(new_test)
    db.commit()
    db.refresh(new_test)
    
    return ABTestResponse.model_validate(new_test)

@app.get("/api/v1/abtest/active", response_model=List[ABTestResponse])
def get_active_abtests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список активных A/B тестов"""
    tests = db.query(ABTest).filter(
        ABTest.user_id == current_user.id,
        ABTest.status == ABTestStatus.ACTIVE
    ).all()
    
    return [ABTestResponse.model_validate(t) for t in tests]

@app.get("/api/v1/abtest/{test_id}/status", response_model=ABTestStatusResponse)
def get_abtest_status(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статус A/B теста"""
    test = db.query(ABTest).filter(
        ABTest.id == test_id,
        ABTest.user_id == current_user.id
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    return ABTestStatusResponse(
        id=test.id,
        name=test.name,
        status=test.status,
        variant_a_stats={
            "views": test.variant_a_views,
            "clicks": test.variant_a_clicks,
            "orders": test.variant_a_orders
        },
        variant_b_stats={
            "views": test.variant_b_views,
            "clicks": test.variant_b_clicks,
            "orders": test.variant_b_orders
        },
        winner=test.winner
    )

@app.post("/api/v1/abtest/{test_id}/stop")
def stop_abtest(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Остановить A/B тест"""
    test = db.query(ABTest).filter(
        ABTest.id == test_id,
        ABTest.user_id == current_user.id
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    
    test.status = ABTestStatus.COMPLETED
    test.completed_at = datetime.utcnow()
    
    # Определяем победителя
    a_conversion = test.variant_a_orders / test.variant_a_views if test.variant_a_views > 0 else 0
    b_conversion = test.variant_b_orders / test.variant_b_views if test.variant_b_views > 0 else 0
    
    if a_conversion > b_conversion:
        test.winner = "A"
    elif b_conversion > a_conversion:
        test.winner = "B"
    else:
        test.winner = "draw"
    
    db.commit()
    
    return {
        "id": test.id,
        "status": test.status,
        "winner": test.winner,
        "message": f"Test stopped. Winner: Variant {test.winner}"
    }

# ==================== WEBSOCKET ENDPOINTS ====================
class ConnectionManager:
    """Менеджер WebSocket соединений"""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
    
    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].remove(websocket)
    
    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            disconnected = []
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            for conn in disconnected:
                self.active_connections[channel].remove(conn)

manager = ConnectionManager()

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket для real-time обновлений дашборда"""
    await manager.connect(websocket, "dashboard")
    try:
        while True:
            # Получаем сообщение от клиента (пинг или запрос обновления)
            data = await websocket.receive_json()
            
            # Отправляем обновление дашборда
            await websocket.send_json({
                "type": "dashboard_update",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "total_sales": 0,
                    "total_orders": 0,
                    "total_revenue": 0,
                    "conversion_rate": 0
                }
            })
            
            await asyncio.sleep(5)  # Обновление каждые 5 секунд
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, "dashboard")

@app.websocket("/ws/abtest/{test_id}")
async def websocket_abtest(websocket: WebSocket, test_id: str):
    """WebSocket для real-time обновлений A/B теста"""
    channel = f"abtest_{test_id}"
    await manager.connect(websocket, channel)
    try:
        while True:
            # Отправляем обновления статистики теста
            await websocket.send_json({
                "type": "abtest_update",
                "test_id": test_id,
                "timestamp": datetime.utcnow().isoformat(),
                "stats": {
                    "variant_a": {"views": 0, "clicks": 0, "orders": 0},
                    "variant_b": {"views": 0, "clicks": 0, "orders": 0}
                }
            })
            
            await asyncio.sleep(10)  # Обновление каждые 10 секунд
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)

# ==================== HEALTH CHECK ====================
@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
def root():
    return {
        "name": "Seller Fuck Bot API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/v1/auth/*",
            "dashboard": "/api/v1/dashboard/*",
            "analyze": "/api/v1/analyze/*",
            "content": "/api/v1/content/*",
            "abtest": "/api/v1/abtest/*"
        }
    }

# ==================== MAIN ====================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
