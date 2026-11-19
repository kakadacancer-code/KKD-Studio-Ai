"""SQLite persistence: each worker gets its own SQLAlchemy session."""
from __future__ import annotations
import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
STORAGE = Path(os.getenv('KKD_STORAGE', str(ROOT / 'storage'))).resolve()
PROJECTS_DIR = STORAGE / 'projects'
MODELS_DIR = STORAGE / 'models'
for path in (STORAGE, PROJECTS_DIR, MODELS_DIR):
    path.mkdir(parents=True, exist_ok=True)

engine = create_engine(f'sqlite:///{STORAGE / "studio.db"}', connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def now():
    return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(240))
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default='created')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    segments: Mapped[list['Segment']] = relationship(back_populates='project', cascade='all,delete-orphan')

class Segment(Base):
    __tablename__ = 'segments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id'), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    zh: Mapped[str] = mapped_column(Text, default='')
    km: Mapped[str] = mapped_column(Text, default='')
    translation_status: Mapped[str] = mapped_column(String(24), default='pending')
    voice_status: Mapped[str] = mapped_column(String(24), default='pending')
    voice_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_duration: Mapped[float] = mapped_column(Float, default=0)
    voice_speed: Mapped[float] = mapped_column(Float, default=1.0)
    review_note: Mapped[str] = mapped_column(Text, default='')
    project: Mapped[Project] = relationship(back_populates='segments')

class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default='queued')
    total: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default='Queued')
    error: Mapped[str] = mapped_column(Text, default='')
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class TranscribedChunk(Base):
    __tablename__ = 'transcribed_chunks'
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True)
    chunk_index: Mapped[int] = mapped_column(Integer, primary_key=True)

class Export(Base):
    __tablename__ = 'exports'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

Base.metadata.create_all(engine)
with SessionLocal() as s:
    s.query(Job).filter(Job.status.in_(['running', 'queued', 'cancel_requested'])).update({'status': 'interrupted', 'message': 'Interrupted — restart the step to resume remaining work'}, synchronize_session=False)
    s.commit()
