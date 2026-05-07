from sqlalchemy import Column, String, Integer, DateTime, Index
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


class QRScan(Base):
    __tablename__ = "qr_scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    short_code = Column(String(16), index=True, nullable=False)
    scanned_at = Column(DateTime, default=datetime.utcnow, index=True)
    country = Column(String(64), nullable=True)
    city = Column(String(128), nullable=True)
    device = Column(String(32), nullable=True)   # mobile / tablet / desktop
    os = Column(String(64), nullable=True)
    browser = Column(String(64), nullable=True)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rating = Column(Integer, nullable=True)   # 1-5 stars, optional
    message = Column(String(2000), nullable=False)
    page = Column(String(64), nullable=True)  # e.g. 'home', 'guide', 'manage'
    submitted_at = Column(DateTime, default=datetime.utcnow)


class SiteStats(Base):
    __tablename__ = "site_stats"

    id = Column(Integer, primary_key=True, default=1)
    visitor_count = Column(Integer, default=0)


class PageVisit(Base):
    __tablename__ = "page_visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visited_at = Column(DateTime, default=datetime.utcnow, index=True)
