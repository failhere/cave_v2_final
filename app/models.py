from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False)
    password_hash = Column(String(255), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Zone(Base):
    __tablename__ = 'zones'
    id = Column(String(100), primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0, index=True)


class Lot(Base):
    __tablename__ = 'lots'
    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    vintage = Column(Integer)
    wine_type = Column(String(100), default='')
    comment = Column(Text, default='')
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Tank(Base):
    __tablename__ = 'tanks'
    id = Column(String(100), primary_key=True)
    label = Column(String(100), nullable=False)
    zone_id = Column(String(100), ForeignKey('zones.id'), nullable=False, index=True)
    container_type = Column(String(50), nullable=False, default='cuve')
    material = Column(String(50), nullable=False, default='inox')
    capacity_hl = Column(Float, nullable=False)
    current_volume_hl = Column(Float, nullable=False, default=0)
    current_lot_id = Column(Integer, ForeignKey('lots.id'))
    manual_status = Column(String(50))
    comment = Column(Text, default='')
    active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0, index=True)

    zone = relationship('Zone')
    current_lot = relationship('Lot')


class Movement(Base):
    __tablename__ = 'movements'
    id = Column(Integer, primary_key=True)
    movement_type = Column(String(50), nullable=False, index=True)
    operation_name = Column(String(150))
    source_tank_id = Column(String(100), ForeignKey('tanks.id'))
    destination_tank_id = Column(String(100), ForeignKey('tanks.id'))
    volume_hl = Column(Float)
    grape_weight_kg = Column(Float)
    mustimeter_raw = Column(Float)
    corrected_density_20c = Column(Float)
    sugar_g_l = Column(Float)
    must_temperature_c = Column(Float)
    tav_potential = Column(Float)
    juice_yield_l_per_kg = Column(Float)
    juice_yield_pct = Column(Float)
    lot_id = Column(Integer, ForeignKey('lots.id'))
    comment = Column(Text, default='')
    impact_volume = Column(Boolean, nullable=False, default=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship('User')
    lot = relationship('Lot')
    source_tank = relationship('Tank', foreign_keys=[source_tank_id])
    destination_tank = relationship('Tank', foreign_keys=[destination_tank_id])


class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    event_type = Column(String(80), nullable=False)
    status = Column(String(50), nullable=False, default='prevu')
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime)
    tank_id = Column(String(100), ForeignKey('tanks.id'))
    lot_id = Column(Integer, ForeignKey('lots.id'))
    assigned_user_id = Column(Integer, ForeignKey('users.id'))
    comment = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tank = relationship('Tank')
    lot = relationship('Lot')
    assigned_user = relationship('User')


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    action_type = Column(String(80), nullable=False, index=True)
    tank_id = Column(String(100), ForeignKey('tanks.id'))
    lot_id = Column(Integer, ForeignKey('lots.id'))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    tank = relationship('Tank')
    lot = relationship('Lot')
    user = relationship('User')
