from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


# =========================
# Core / Existing models
# =========================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False)
    password_hash = Column(String(255), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Zone(Base):
    __tablename__ = "zones"

    id = Column(String(100), primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0, index=True)


class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    vintage = Column(Integer)
    wine_type = Column(String(100), default="")

    # --- V3 minimal extensions ---
    category = Column(String(50), nullable=False, default="vin_en_cours")
    color = Column(String(30), default="")
    appellation = Column(String(120), default="")
    certification_flags = Column(String(250), default="")
    status = Column(String(50), nullable=False, default="actif")

    comment = Column(Text, default="")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # helpful relationships
    origins = relationship("LotOrigin", back_populates="lot", cascade="all, delete-orphan")
    parent_links = relationship(
        "LotTraceLink",
        foreign_keys="LotTraceLink.child_lot_id",
        back_populates="child_lot",
        cascade="all, delete-orphan",
    )
    child_links = relationship(
        "LotTraceLink",
        foreign_keys="LotTraceLink.parent_lot_id",
        back_populates="parent_lot",
        cascade="all, delete-orphan",
    )


class Tank(Base):
    __tablename__ = "tanks"

    id = Column(String(100), primary_key=True)
    label = Column(String(100), nullable=False)
    zone_id = Column(String(100), ForeignKey("zones.id"), nullable=False, index=True)
    container_type = Column(String(50), nullable=False, default="cuve")
    material = Column(String(50), nullable=False, default="inox")
    capacity_hl = Column(Float, nullable=False)
    current_volume_hl = Column(Float, nullable=False, default=0)
    current_lot_id = Column(Integer, ForeignKey("lots.id"))
    manual_status = Column(String(50))
    comment = Column(Text, default="")
    active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0, index=True)

    zone = relationship("Zone")
    current_lot = relationship("Lot")


class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True)
    movement_type = Column(String(50), nullable=False, index=True)
    operation_name = Column(String(150))

    source_tank_id = Column(String(100), ForeignKey("tanks.id"))
    destination_tank_id = Column(String(100), ForeignKey("tanks.id"))

    volume_hl = Column(Float)

    # Existing harvest / intake fields kept for backward compatibility
    grape_weight_kg = Column(Float)
    mustimeter_raw = Column(Float)
    corrected_density_20c = Column(Float)
    sugar_g_l = Column(Float)
    must_temperature_c = Column(Float)
    tav_potential = Column(Float)
    juice_yield_l_per_kg = Column(Float)
    juice_yield_pct = Column(Float)

    lot_id = Column(Integer, ForeignKey("lots.id"))
    comment = Column(Text, default="")
    impact_volume = Column(Boolean, nullable=False, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User")
    lot = relationship("Lot")
    source_tank = relationship("Tank", foreign_keys=[source_tank_id])
    destination_tank = relationship("Tank", foreign_keys=[destination_tank_id])

    # traceability helper relationships
    harvest_entry = relationship("HarvestEntry", back_populates="source_movement", uselist=False)
    trace_links = relationship("LotTraceLink", back_populates="movement")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    event_type = Column(String(80), nullable=False)
    status = Column(String(50), nullable=False, default="prevu")
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime)
    tank_id = Column(String(100), ForeignKey("tanks.id"))
    lot_id = Column(Integer, ForeignKey("lots.id"))
    assigned_user_id = Column(Integer, ForeignKey("users.id"))
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tank = relationship("Tank")
    lot = relationship("Lot")
    assigned_user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    action_type = Column(String(80), nullable=False, index=True)
    tank_id = Column(String(100), ForeignKey("tanks.id"))
    lot_id = Column(Integer, ForeignKey("lots.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    tank = relationship("Tank")
    lot = relationship("Lot")
    user = relationship("User")


# =========================
# V3 minimal traceability
# =========================

class Parcel(Base):
    __tablename__ = "parcels"

    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)

    commune = Column(String(120), default="")
    appellation = Column(String(120), default="")
    area_ha = Column(Float)
    grape_variety = Column(String(120), default="")
    organic_status = Column(String(50), default="")
    notes = Column(Text, default="")

    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    harvest_entries = relationship(
        "HarvestEntry",
        back_populates="parcel",
        cascade="all, delete-orphan",
    )


class HarvestEntry(Base):
    __tablename__ = "harvest_entries"

    id = Column(Integer, primary_key=True)
    entry_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    parcel_id = Column(Integer, ForeignKey("parcels.id"), index=True)
    destination_tank_id = Column(String(100), ForeignKey("tanks.id"), index=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), index=True)

    grape_variety = Column(String(120), default="")
    harvest_mode = Column(String(50), default="")  # manuelle / mecanique
    grape_weight_kg = Column(Float)
    mustimeter_raw = Column(Float)
    corrected_density_20c = Column(Float)
    sugar_g_l = Column(Float)
    must_temperature_c = Column(Float)
    tav_potential = Column(Float)
    juice_yield_l_per_kg = Column(Float)
    juice_yield_pct = Column(Float)

    # back-reference to a legacy movement when the harvest entry was created from it
    source_movement_id = Column(Integer, ForeignKey("movements.id"), unique=True)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    parcel = relationship("Parcel", back_populates="harvest_entries")
    destination_tank = relationship("Tank")
    lot = relationship("Lot")
    source_movement = relationship("Movement", back_populates="harvest_entry")

    lot_origins = relationship(
        "LotOrigin",
        back_populates="harvest_entry",
        cascade="all, delete-orphan",
    )


class LotOrigin(Base):
    __tablename__ = "lot_origins"
    __table_args__ = (
        UniqueConstraint("lot_id", "harvest_entry_id", name="uq_lot_origin_pair"),
    )

    id = Column(Integer, primary_key=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False, index=True)
    harvest_entry_id = Column(Integer, ForeignKey("harvest_entries.id"), nullable=False, index=True)

    share_pct = Column(Float)
    volume_estimated_hl = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    lot = relationship("Lot", back_populates="origins")
    harvest_entry = relationship("HarvestEntry", back_populates="lot_origins")


class LotTraceLink(Base):
    __tablename__ = "lot_trace_links"

    id = Column(Integer, primary_key=True)

    parent_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False, index=True)
    child_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False, index=True)

    operation_type = Column(String(50), nullable=False, index=True)
    operation_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    movement_id = Column(Integer, ForeignKey("movements.id"), index=True)
    source_tank_id = Column(String(100), ForeignKey("tanks.id"), index=True)
    destination_tank_id = Column(String(100), ForeignKey("tanks.id"), index=True)

    volume_hl = Column(Float)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    parent_lot = relationship(
        "Lot",
        foreign_keys=[parent_lot_id],
        back_populates="child_links",
    )
    child_lot = relationship(
        "Lot",
        foreign_keys=[child_lot_id],
        back_populates="parent_links",
    )
    movement = relationship("Movement", back_populates="trace_links")
    source_tank = relationship("Tank", foreign_keys=[source_tank_id])
    destination_tank = relationship("Tank", foreign_keys=[destination_tank_id])
