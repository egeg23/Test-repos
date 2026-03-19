# modules/database.py - SQLAlchemy models for PostgreSQL
"""
Database models for scalable architecture
Migrates from SQLite file storage to PostgreSQL
"""

import os
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, Text, JSON, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger('database')

Base = declarative_base()

# Database connection
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://seller_ai:secure_password_2026@localhost:5432/seller_ai_prod'
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # 20 connections in pool
    max_overflow=30,  # 30 additional connections under load
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Settings
    language = Column(String(10), default='ru')
    timezone = Column(String(50), default='Europe/Moscow')
    notifications_enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    cabinets = relationship("Cabinet", back_populates="user", cascade="all, delete-orphan")
    operations = relationship("Operation", back_populates="user")
    fuck_mode_config = relationship("FuckModeConfig", back_populates="user", uselist=False)


class Cabinet(Base):
    """Marketplace cabinet (WB/Ozon)"""
    __tablename__ = "cabinets"
    
    id = Column(String(100), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Cabinet info
    name = Column(String(255), nullable=False)
    platform = Column(String(20), nullable=False)  # 'wb' or 'ozon'
    is_active = Column(Boolean, default=True)
    
    # API credentials (encrypted in production)
    api_key = Column(Text, nullable=True)
    api_secret = Column(Text, nullable=True)
    
    # Settings
    settings = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sync = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="cabinets")
    products = relationship("Product", back_populates="cabinet", cascade="all, delete-orphan")


class Product(Base):
    """Product in marketplace cabinet"""
    __tablename__ = "products"
    
    id = Column(String(100), primary_key=True)
    cabinet_id = Column(String(100), ForeignKey("cabinets.id"), nullable=False)
    
    # Product info
    name = Column(String(500), nullable=False)
    sku = Column(String(100), nullable=True)
    barcode = Column(String(100), nullable=True)
    
    # Pricing
    current_price = Column(Float, default=0.0)
    cost_price = Column(Float, default=0.0)
    min_price = Column(Float, default=0.0)
    max_price = Column(Float, default=0.0)
    
    # Stock
    stock = Column(Integer, default=0)
    stock_days = Column(Float, default=0.0)
    
    # Rating
    rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)
    
    # Category
    category = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    has_buy_box = Column(Boolean, default=False)
    
    # Competitor data
    competitor_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cabinet = relationship("Cabinet", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")


class PriceHistory(Base):
    """Price change history"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(100), ForeignKey("products.id"), nullable=False)
    
    old_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    change_percent = Column(Float, nullable=False)
    
    # Context
    reason = Column(Text, nullable=True)
    triggered_by = Column(String(50), default='manual')  # 'manual', 'fuck_mode', 'api'
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="price_history")


class Operation(Base):
    """Operation log (from operation_log.py)"""
    __tablename__ = "operations"
    
    id = Column(String(50), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Operation details
    operation_type = Column(String(50), nullable=False)  # 'price_change', 'ad_change', etc.
    cabinet_id = Column(String(100), nullable=True)
    cabinet_name = Column(String(255), nullable=True)
    product_id = Column(String(100), nullable=True)
    product_name = Column(String(500), nullable=True)
    
    # Values
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    
    # Metadata
    reason = Column(Text, nullable=True)
    dry_run = Column(Boolean, default=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="operations")


class FuckModeConfig(Base):
    """Fuck Mode configuration per user"""
    __tablename__ = "fuck_mode_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Settings
    enabled = Column(Boolean, default=False)
    dry_run = Column(Boolean, default=True)
    max_price_change_percent = Column(Float, default=20.0)
    min_margin_percent = Column(Float, default=15.0)
    target_drr = Column(Float, default=15.0)
    
    # Platforms
    platforms = Column(JSON, default=lambda: ['wb', 'ozon'])
    
    # Notifications
    enabled_notifications = Column(Boolean, default=True)
    
    # Schedule
    check_interval_minutes = Column(Integer, default=30)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="fuck_mode_config")


class Competitor(Base):
    """Competitor data from Mpstats"""
    __tablename__ = "competitors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(100), ForeignKey("products.id"), nullable=False)
    
    # Competitor info
    nm_id = Column(String(100), nullable=False)
    name = Column(String(500), nullable=True)
    price = Column(Float, default=0.0)
    rating = Column(Float, default=0.0)
    reviews = Column(Integer, default=0)
    sales = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalyticsCache(Base):
    """Cached analytics data"""
    __tablename__ = "analytics_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(500), nullable=False, unique=True)
    data = Column(JSON, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database utilities
def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def init_database():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def migrate_from_json(json_dir: str = "/opt/clients"):
    """Migrate data from JSON files to PostgreSQL"""
    from pathlib import Path
    import json
    
    db = get_db()
    migrated = 0
    
    try:
        # Migrate users from USER_REGISTRY.json
        registry_path = Path(json_dir) / "USER_REGISTRY.json"
        if registry_path.exists():
            with open(registry_path) as f:
                registry = json.load(f)
            
            for user_id, user_data in registry.items():
                # Check if user exists
                existing = db.query(User).filter(User.id == int(user_id)).first()
                if not existing:
                    user = User(
                        id=int(user_id),
                        username=user_data.get('username'),
                        first_name=user_data.get('first_name'),
                        last_name=user_data.get('last_name'),
                        phone=user_data.get('phone'),
                        created_at=datetime.fromisoformat(user_data.get('registered_at', datetime.utcnow().isoformat()))
                    )
                    db.add(user)
                    migrated += 1
            
            db.commit()
            logger.info(f"Migrated {migrated} users from JSON")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    # Initialize database
    init_database()
    print("Database initialized successfully")
