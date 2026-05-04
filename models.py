from sqlalchemy import Column, String, Integer, DateTime
from database import Base
from datetime import datetime


class DynamicQR(Base):
    __tablename__ = "dynamic_qr"

    short_code = Column(String(16), primary_key=True, index=True)
    destination_url = Column(String(2048), nullable=False)
    edit_token = Column(String(64), nullable=False)
    scan_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_scan = Column(DateTime, nullable=True)


class AppRedirect(Base):
    __tablename__ = "app_redirect"

    short_code = Column(String(16), primary_key=True, index=True)
    ios_url = Column(String(2048), nullable=True)
    android_url = Column(String(2048), nullable=True)
    fallback_url = Column(String(2048), nullable=True)
    scan_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_scan = Column(DateTime, nullable=True)


class SiteStats(Base):
    __tablename__ = "site_stats"

    id = Column(Integer, primary_key=True, default=1)
    visitor_count = Column(Integer, default=0)


class PageVisit(Base):
    __tablename__ = "page_visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visited_at = Column(DateTime, default=datetime.utcnow, index=True)
