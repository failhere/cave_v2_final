from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine, get_db
from .models import AuditLog, Event, Lot, Movement, Tank, User, Zone

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
SEED_PATH = DATA_DIR / 'cuverie_seed.json'

pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-in-production')

app = FastAPI(title='Suivi de cave', version='1.0.0')
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site='lax', https_only=False)
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'static')), name='static')
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))


ROLE_LABELS = {
    'admin': 'Admin',
    'maitre_de_chai': 'Maître de chai',
    'caviste': 'Caviste',
}
EDIT_ROLES = {'admin', 'maitre_de_chai'}
ALL_STATUSES = ['vide', 'occupee_non_pleine', 'occupee_pleine', 'fermentation', 'elevage', 'nettoyage', 'a_derougir', 'alerte']
MANUAL_STATUSES = {'fermentation', 'elevage', 'nettoyage', 'a_derougir', 'alerte'}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def zone_id(name: str) -> str:
    return name.lower().replace(' ', '_')

def normalize_material(value: Optional[str]) -> str:
    raw = (value or '').strip().lower()
    if 'inox' in raw:
        return 'inox'
    if 'beton' in raw or 'béton' in raw:
        return 'beton'
    if 'bois' in raw:
        return 'bois'
    return raw or 'inox'


def infer_empty_status_from_wine_type(wine_type: Optional[str]) -> Optional[str]:
    text = (wine_type or '').strip().lower()
    if not text:
        return None
    if 'blanc' in text or 'white' in text:
        return 'nettoyage'
    if 'rose' in text or 'rosé' in text or 'rouge' in text or 'red' in text:
        return 'a_derougir'
    return None


def clear_cleaning_status_if_filled(tank: Tank):
    if tank.current_volume_hl > 0 and tank.manual_status in {'nettoyage', 'a_derougir'}:
        tank.manual_status = None


def empty_tank_with_auto_status(tank: Tank, lot: Optional[Lot]):
    tank.current_volume_hl = 0
    tank.current_lot_id = None
    if normalize_material(getattr(tank, 'material', None)) == 'inox':
        tank.manual_status = infer_empty_status_from_wine_type(lot.wine_type if lot else None)
    else:
        tank.manual_status = None


def ensure_tank_not_blocked_for_fill(tank: Tank):
    if tank.manual_status == "a_derougir":
        raise HTTPException(
            status_code=400,
            detail=f"La cuve {tank.id} est à dérougir. Marquez-la comme dérougie avant de la réutiliser."
        )


TEMP_POINTS = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]
MV_POINTS = [1000, 1010, 1020, 1030, 1040, 1050, 1060, 1070, 1080, 1090, 1100, 1120, 1140, 1160, 1180, 1200]
MV_CORRECTIONS = {
    13: [-1.03, -1.16, -1.28, -1.40, -1.52, -1.62, -1.74, -1.85, -1.85, -2.07, -2.17, -2.38, -2.54, -2.77, -2.94, -3.11],
    14: [-0.92, -1.03, -1.14, -1.24, -1.34, -1.44, -1.54, -1.64, -1.73, -1.82, -1.92, -2.08, -2.25, -2.42, -2.57, -2.77],
    15: [-0.77, -0.87, -0.96, -1.04, -1.13, -1.21, -1.29, -1.37, -1.45, -1.53, -1.60, -1.75, -1.89, -2.03, -2.16, -2.28],
    16: [-0.65, -0.72, -0.79, -0.86, -0.93, -1.00, -1.06, -1.12, -1.19, -1.25, -1.31, -1.43, -1.54, -1.65, -1.75, -1.84],
    17: [-0.50, -0.56, -0.61, -0.66, -0.72, -0.76, -0.82, -0.86, -0.91, -0.96, -1.00, -1.09, -1.18, -1.25, -1.32, -1.39],
    18: [-0.35, -0.39, -0.43, -0.47, -0.49, -0.53, -0.56, -0.59, -0.63, -0.65, -0.69, -0.74, -0.80, -0.85, -0.90, -0.95],
    19: [-0.19, -0.21, -0.23, -0.25, -0.27, -0.28, -0.30, -0.31, -0.33, -0.35, -0.36, -0.39, -0.42, -0.43, -0.46, -0.50],
    20: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    21: [0.19, 0.21, 0.23, 0.24, 0.26, 0.28, 0.29, 0.31, 0.32, 0.34, 0.36, 0.39, 0.41, 0.44, 0.46, 0.48],
    22: [0.39, 0.42, 0.45, 0.49, 0.52, 0.55, 0.58, 0.61, 0.64, 0.67, 0.70, 0.76, 0.81, 0.87, 0.93, 0.97],
    23: [0.61, 0.66, 0.71, 0.76, 0.80, 0.85, 0.90, 0.95, 0.99, 1.04, 1.08, 1.16, 1.25, 1.32, 1.39, 1.46],
    24: [0.85, 0.91, 0.97, 1.03, 1.09, 1.15, 1.19, 1.25, 1.31, 1.37, 1.43, 1.54, 1.65, 1.76, 1.86, 1.95],
    25: [1.08, 1.15, 1.23, 1.30, 1.37, 1.44, 1.52, 1.59, 1.67, 1.74, 1.81, 1.95, 2.09, 2.21, 2.34, 2.45],
    26: [1.30, 1.40, 1.49, 1.58, 1.67, 1.76, 1.84, 1.93, 2.02, 2.10, 2.18, 2.32, 2.49, 2.64, 2.78, 2.91],
    27: [1.57, 1.68, 1.77, 1.88, 1.98, 2.07, 2.16, 2.26, 2.36, 2.46, 2.56, 2.74, 2.91, 3.07, 3.24, 3.39],
    28: [1.82, 1.93, 2.05, 2.16, 2.29, 2.39, 2.51, 2.63, 2.74, 2.85, 2.96, 3.16, 3.38, 3.57, 3.75, 3.92],
}


def normalize_mustimeter_reading(value: Optional[float]) -> Optional[float]:
    if value in (None, ''):
        return None
    value = float(value)
    if value <= 0:
        return None
    if value < 10:
        return value * 1000.0
    return value


def _interp(points: list[float], values: list[float], x: float) -> float:
    if x <= points[0]:
        return values[0]
    if x >= points[-1]:
        return values[-1]
    for i in range(len(points) - 1):
        x0, x1 = points[i], points[i + 1]
        if x0 <= x <= x1:
            y0, y1 = values[i], values[i + 1]
            if x1 == x0:
                return y0
            ratio = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * ratio
    return values[-1]


def mustimeter_correction(raw_reading: float, temperature_c: float) -> float:
    raw = max(MV_POINTS[0], min(MV_POINTS[-1], normalize_mustimeter_reading(raw_reading)))
    temp = max(TEMP_POINTS[0], min(TEMP_POINTS[-1], float(temperature_c)))
    if temp in MV_CORRECTIONS:
        return _interp(MV_POINTS, MV_CORRECTIONS[int(temp)], raw)
    lower_t = max(t for t in TEMP_POINTS if t <= temp)
    upper_t = min(t for t in TEMP_POINTS if t >= temp)
    lower_corr = _interp(MV_POINTS, MV_CORRECTIONS[lower_t], raw)
    upper_corr = _interp(MV_POINTS, MV_CORRECTIONS[upper_t], raw)
    if upper_t == lower_t:
        return lower_corr
    ratio = (temp - lower_t) / (upper_t - lower_t)
    return lower_corr + (upper_corr - lower_corr) * ratio


def corrected_density_20c(raw_reading: float, temperature_c: float) -> float:
    raw = normalize_mustimeter_reading(raw_reading)
    return raw + mustimeter_correction(raw, temperature_c)


def density_to_specific_gravity(density_value: float) -> float:
    if density_value is None:
        return None
    if density_value >= 100:
        return density_value / 1000.0
    return density_value


def density_to_brix(density_value: float) -> float:
    sg = density_to_specific_gravity(density_value)
    if sg is None or sg <= 0:
        return None
    return (((182.4601 * sg - 775.6821) * sg + 1262.7794) * sg - 669.5622)


def compute_potential_abv_from_density(density_value: float) -> float:
    brix = density_to_brix(density_value)
    if brix is None:
        return None
    return max(0.0, brix / 1.8)


def compute_sugar_g_l_from_tav(tav: Optional[float]) -> Optional[float]:
    if tav is None:
        return None
    return tav * 16.83


def compute_juice_yield(volume_hl: float, grape_weight_kg: float) -> tuple[Optional[float], Optional[float]]:
    if volume_hl is None or grape_weight_kg in (None, 0):
        return None, None
    liters = volume_hl * 100.0
    l_per_100kg = (liters / grape_weight_kg) * 100.0
    pct = (liters / grape_weight_kg) * 100.0
    return l_per_100kg, pct


def compute_entry_metrics(raw_reading: Optional[float], temperature_c: Optional[float], volume_hl: Optional[float], grape_weight_kg: Optional[float]) -> dict:
    corrected = None
    corrected_rounded = None
    tav = None
    sugar = None
    if raw_reading is not None and temperature_c is not None:
        corrected = corrected_density_20c(raw_reading, temperature_c)
        corrected_rounded = int(round(corrected))
        tav = compute_potential_abv_from_density(corrected_rounded)
        sugar = compute_sugar_g_l_from_tav(tav)
    y_l100, y_pct = compute_juice_yield(volume_hl, grape_weight_kg)
    return {
        'corrected_density_20c': corrected,
        'corrected_density_20c_rounded': corrected_rounded,
        'tav_potential': tav,
        'sugar_g_l': sugar,
        'juice_yield_l_per_100kg': y_l100,
        'juice_yield_pct': y_pct,
    }


def compute_display_status(tank: Tank) -> str:
    if tank.manual_status in MANUAL_STATUSES:
        return tank.manual_status
    if tank.current_volume_hl <= 0:
        return 'vide'
    ratio = (tank.current_volume_hl / tank.capacity_hl) if tank.capacity_hl else 0
    return 'occupee_pleine' if ratio >= 0.95 else 'occupee_non_pleine'


def serialize_tank(tank: Tank) -> dict:
    status = compute_display_status(tank)
    return {
        'id': tank.id,
        'label': tank.label,
        'zone': tank.zone.name if tank.zone else tank.zone_id,
        'capacity_hl': tank.capacity_hl,
        'current_volume_hl': round(tank.current_volume_hl or 0, 2),
        'fill_pct': round(((tank.current_volume_hl or 0) / tank.capacity_hl) * 100, 1) if tank.capacity_hl else 0,
        'display_status': status,
        'manual_status': tank.manual_status,
        'current_lot': ({'id': tank.current_lot.id, 'code': tank.current_lot.code} if tank.current_lot else None),
        'comment': tank.comment or '',
        'updated_at': tank.updated_at.isoformat() if tank.updated_at else None,
        'sort_order': tank.sort_order,
        'zone_sort_order': (tank.zone.sort_order if tank.zone else 0),
    }


def serialize_lot(lot: Lot, db: Session) -> dict:
    tanks = db.scalars(select(Tank).where(Tank.current_lot_id == lot.id).order_by(Tank.sort_order, Tank.label)).all()
    total = sum(t.current_volume_hl or 0 for t in tanks)
    return {
        'id': lot.id,
        'code': lot.code,
        'vintage': lot.vintage,
        'wine_type': lot.wine_type,
        'comment': lot.comment or '',
        'active': lot.active,
        'tank_ids': [t.id for t in tanks],
        'volume_total_hl': round(total, 2),
    }


def require_user(request: Request, db: Session) -> User:
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail='Non connecté')
    user = db.get(User, user_id)
    if not user or not user.active:
        request.session.clear()
        raise HTTPException(status_code=401, detail='Session invalide')
    return user


def require_role(user: User, roles: set[str]):
    if user.role not in roles:
        raise HTTPException(status_code=403, detail='Accès refusé')


def log_action(db: Session, user: User, action_type: str, message: str, tank_id: Optional[str] = None, lot_id: Optional[int] = None):
    db.add(AuditLog(action_type=action_type, tank_id=tank_id, lot_id=lot_id, user_id=user.id, message=message))


def init_db():
    Base.metadata.create_all(bind=engine)
    from sqlalchemy.orm import Session as _Session
    with _Session(engine) as db:
        if db.scalar(select(func.count(Zone.id))) == 0:
            seed = json.loads(SEED_PATH.read_text(encoding='utf-8'))
            for z in seed['zones']:
                db.add(Zone(id=zone_id(z['name']), name=z['name'], sort_order=z.get('sort_order', 0)))
            db.commit()
        if db.scalar(select(func.count(Tank.id))) == 0:
            seed = json.loads(SEED_PATH.read_text(encoding='utf-8'))
            for t in seed['tanks']:
                db.add(Tank(
                    id=t['id'],
                    label=t['label'],
                    zone_id=zone_id(t['zone']),
                    container_type=t.get('container_type', 'cuve'),
                    material=normalize_material(t.get('material', 'inox')),
                    capacity_hl=t['capacity_hl'],
                    current_volume_hl=0,
                    manual_status=None,
                    comment='',
                    sort_order=t.get('sort_order', 0)
                ))
            db.commit()
        required_users = [
            ('pierre', 'Pierre', 'admin', os.getenv('PIERRE_PASSWORD', 'Pierre2026!')),
            ('jean-michel', 'Jean-michel', 'maitre_de_chai', os.getenv('JEAN_MICHEL_PASSWORD', 'JeanMichel2026!')),
            ('sylvain', 'Sylvain', 'caviste', os.getenv('SYLVAIN_PASSWORD', 'Sylvain2026!')),
        ]
        for username, full_name, role, password in required_users:
            existing = db.scalar(select(User).where(User.username == username))
            if not existing:
                db.add(User(username=username, full_name=full_name, role=role, password_hash=hash_password(password), active=True))
        db.commit()


@app.on_event('startup')
def startup_event():
    init_db()


@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.post('/api/login')
def api_login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail='Identifiants invalides')
    request.session['user_id'] = user.id
    return {'ok': True, 'user': {'username': user.username, 'full_name': user.full_name, 'role': user.role, 'role_label': ROLE_LABELS[user.role]}}


@app.post('/api/logout')
def api_logout(request: Request):
    request.session.clear()
    return {'ok': True}


@app.get('/api/bootstrap')
def api_bootstrap(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    zones = db.scalars(select(Zone).order_by(Zone.sort_order, Zone.name)).all()
    users = db.scalars(select(User).where(User.active == True).order_by(User.full_name)).all()  # noqa: E712
    totals = db.execute(select(func.count(Tank.id), func.sum(Tank.capacity_hl), func.sum(Tank.current_volume_hl))).one()
    return {
        'user': {'username': user.username, 'full_name': user.full_name, 'role': user.role, 'role_label': ROLE_LABELS[user.role]},
        'zones': [{'id': z.id, 'name': z.name} for z in zones],
        'users': [{'id': u.id, 'username': u.username, 'full_name': u.full_name, 'role': u.role, 'role_label': ROLE_LABELS[u.role]} for u in users],
        'stats': {'tank_count': totals[0] or 0, 'capacity_total_hl': round(totals[1] or 0, 2), 'current_total_hl': round(totals[2] or 0, 2)},
        'editable': user.role in EDIT_ROLES,
    }


@app.get('/api/tanks')
def api_tanks(request: Request, zone: str = '', status: str = '', search: str = '', db: Session = Depends(get_db)):
    require_user(request, db)
    stmt = select(Tank).options(joinedload(Tank.zone), joinedload(Tank.current_lot)).order_by(Tank.sort_order, Tank.label)
    tanks = db.scalars(stmt).all()
    out = []
    term = search.lower().strip()
    for t in tanks:
        s = serialize_tank(t)
        if zone and t.zone_id != zone:
            continue
        if status and s['display_status'] != status:
            continue
        if term and term not in (t.id.lower() + ' ' + (s['current_lot']['code'].lower() if s['current_lot'] else '')):
            continue
        out.append(s)
    return out


@app.get('/api/lots')
def api_lots(request: Request, db: Session = Depends(get_db)):
    require_user(request, db)
    lots = db.scalars(select(Lot).order_by(Lot.code)).all()
    return [serialize_lot(l, db) for l in lots]


@app.post('/api/lots')
def api_create_lot(request: Request, payload: dict, db: Session = Depends(get_db)):
    user = require_user(request, db)
    require_role(user, EDIT_ROLES)
    code = (payload.get('code') or '').strip()
    if not code:
        raise HTTPException(status_code=400, detail='Code lot obligatoire')
    existing = db.scalar(select(Lot).where(Lot.code == code))
    if existing:
        raise HTTPException(status_code=400, detail='Code lot déjà utilisé')
    lot = Lot(code=code, vintage=payload.get('vintage'), wine_type=(payload.get('wine_type') or '').strip(), comment=(payload.get('comment') or '').strip(), active=payload.get('active', True))
    db.add(lot)
    db.flush()
    log_action(db, user, 'lot_create', f'Lot {code} créé', lot_id=lot.id)
    db.commit()
    db.refresh(lot)
    return serialize_lot(lot, db)


@app.put('/api/lots/{lot_id}')
def api_update_lot(lot_id: int, request: Request, payload: dict, db: Session = Depends(get_db)):
    user = require_user(request, db)
    require_role(user, EDIT_ROLES)
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail='Lot introuvable')
    code = (payload.get('code') or '').strip()
    if not code:
        raise HTTPException(status_code=400, detail='Code lot obligatoire')
    dup = db.scalar(select(Lot).where(Lot.code == code, Lot.id != lot.id))
    if dup:
        raise HTTPException(status_code=400, detail='Code lot déjà utilisé')
    lot.code = code
    lot.vintage = payload.get('vintage')
    lot.wine_type = (payload.get('wine_type') or '').strip()
    lot.comment = (payload.get('comment') or '').strip()
    lot.active = bool(payload.get('active', True))
    log_action(db, user, 'lot_update', f'Lot {lot.code} modifié', lot_id=lot.id)
    db.commit()
    db.refresh(lot)
    return serialize_lot(lot, db)


@app.get('/api/history')
def api_history(request: Request, db: Session = Depends(get_db)):
    require_user(request, db)
    rows = db.scalars(select(AuditLog).options(joinedload(AuditLog.user), joinedload(AuditLog.tank), joinedload(AuditLog.lot)).order_by(AuditLog.created_at.desc()).limit(300)).all()
    return [{
        'id': r.id,
        'action_type': r.action_type,
        'tank_id': r.tank_id,
        'lot_code': r.lot.code if r.lot else None,
        'user': r.user.full_name if r.user else '',
        'message': r.message,
        'created_at': r.created_at.isoformat(),
    } for r in rows]


@app.get('/api/events')
def api_events(request: Request, db: Session = Depends(get_db)):
    require_user(request, db)
    events = db.scalars(select(Event).options(joinedload(Event.tank), joinedload(Event.lot), joinedload(Event.assigned_user)).order_by(Event.starts_at)).all()
    return [{
        'id': e.id,
        'title': e.title,
        'event_type': e.event_type,
        'status': e.status,
        'starts_at': e.starts_at.isoformat(),
        'ends_at': e.ends_at.isoformat() if e.ends_at else None,
        'tank_id': e.tank_id,
        'lot_id': e.lot_id,
        'lot_code': e.lot.code if e.lot else None,
        'assigned_user_id': e.assigned_user_id,
        'assigned_user_name': e.assigned_user.full_name if e.assigned_user else None,
        'comment': e.comment or '',
    } for e in events]


@app.post('/api/events')
def api_create_event(request: Request, payload: dict, db: Session = Depends(get_db)):
    user = require_user(request, db)
    title = (payload.get('title') or '').strip()
    if not title:
        raise HTTPException(status_code=400, detail='Titre obligatoire')
    starts_at = datetime.fromisoformat(payload['starts_at'])
    ends_at = datetime.fromisoformat(payload['ends_at']) if payload.get('ends_at') else None
    event = Event(
        title=title,
        event_type=(payload.get('event_type') or 'autre').strip(),
        status=(payload.get('status') or 'prevu').strip(),
        starts_at=starts_at,
        ends_at=ends_at,
        tank_id=payload.get('tank_id') or None,
        lot_id=payload.get('lot_id') or None,
        assigned_user_id=payload.get('assigned_user_id') or None,
        comment=(payload.get('comment') or '').strip(),
    )
    db.add(event)
    db.flush()
    log_action(db, user, 'event_create', f'Événement "{event.title}" créé', tank_id=event.tank_id, lot_id=event.lot_id)
    db.commit()
    return {'ok': True, 'id': event.id}


@app.put('/api/events/{event_id}')
def api_update_event(event_id: int, request: Request, payload: dict, db: Session = Depends(get_db)):
    user = require_user(request, db)
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail='Événement introuvable')
    event.title = (payload.get('title') or '').strip()
    event.event_type = (payload.get('event_type') or 'autre').strip()
    event.status = (payload.get('status') or 'prevu').strip()
    event.starts_at = datetime.fromisoformat(payload['starts_at'])
    event.ends_at = datetime.fromisoformat(payload['ends_at']) if payload.get('ends_at') else None
    event.tank_id = payload.get('tank_id') or None
    event.lot_id = payload.get('lot_id') or None
    event.assigned_user_id = payload.get('assigned_user_id') or None
    event.comment = (payload.get('comment') or '').strip()
    log_action(db, user, 'event_update', f'Événement "{event.title}" modifié', tank_id=event.tank_id, lot_id=event.lot_id)
    db.commit()
    return {'ok': True}


@app.post('/api/movements')
def api_create_movement(request: Request, payload: dict, db: Session = Depends(get_db)):
    user = require_user(request, db)
    mtype = payload.get('movement_type')
    if mtype not in {'entree', 'transfert', 'sortie', 'assemblage', 'correction_manuelle', 'autre'}:
        raise HTTPException(status_code=400, detail='Type de mouvement invalide')

    source_id = payload.get('source_tank_id') or None
    dest_id = payload.get('destination_tank_id') or None
    source = db.get(Tank, source_id) if source_id else None
    dest = db.get(Tank, dest_id) if dest_id else None
    lot_id = payload.get('lot_id') or None
    lot = db.get(Lot, int(lot_id)) if lot_id else None
    volume = payload.get('volume_hl')
    volume = float(volume) if volume not in (None, '',) else None
    comment = (payload.get('comment') or '').strip()
    operation_name = (payload.get('operation_name') or '').strip() or None
    impact_volume = bool(payload.get('impact_volume', True))
    grape_weight_kg = payload.get('grape_weight_kg')
    grape_weight_kg = float(grape_weight_kg) if grape_weight_kg not in (None, '',) else None
    mustimeter_raw = payload.get('mustimeter_raw', payload.get('must_density'))
    mustimeter_raw = normalize_mustimeter_reading(mustimeter_raw) if mustimeter_raw not in (None, '',) else None
    must_temperature_c = payload.get('must_temperature_c')
    must_temperature_c = float(must_temperature_c) if must_temperature_c not in (None, '',) else None
    corrected_density = None
    sugar_g_l = None
    tav_potential = None
    juice_yield_l_per_100kg = None
    juice_yield_pct = None

    if mtype == 'autre' and not operation_name:
        raise HTTPException(status_code=400, detail='Nom de l’opération obligatoire')
    if mtype in {'entree', 'transfert', 'sortie', 'assemblage'} and (volume is None or volume <= 0):
        raise HTTPException(status_code=400, detail='Volume obligatoire')

    if mtype == 'entree':
        if not dest:
            raise HTTPException(status_code=400, detail='Cuve destination obligatoire')
        if grape_weight_kg is not None and grape_weight_kg <= 0:
            raise HTTPException(status_code=400, detail='Le poids de raisin doit être supérieur à 0')
        if mustimeter_raw is not None and mustimeter_raw <= 0:
            raise HTTPException(status_code=400, detail='La lecture brute du mustimètre doit être supérieure à 0')
        if (mustimeter_raw is None) ^ (must_temperature_c is None):
            raise HTTPException(status_code=400, detail='Saisir la lecture brute du mustimètre et la température ensemble')
        if dest.current_volume_hl + volume > dest.capacity_hl + 1e-6:
            raise HTTPException(status_code=400, detail='Capacité dépassée')
        ensure_tank_not_blocked_for_fill(dest)
        dest.current_volume_hl += volume
        if lot:
            dest.current_lot_id = lot.id
        clear_cleaning_status_if_filled(dest)
        metrics = compute_entry_metrics(mustimeter_raw, must_temperature_c, volume, grape_weight_kg)
        corrected_density = metrics['corrected_density_20c']
        tav_potential = round(metrics['tav_potential'], 2) if metrics['tav_potential'] is not None else None
        sugar_g_l = round(metrics['sugar_g_l'], 1) if metrics['sugar_g_l'] is not None else None
        juice_yield_l_per_100kg = round(metrics['juice_yield_l_per_100kg'], 2) if metrics['juice_yield_l_per_100kg'] is not None else None
        juice_yield_pct = round(metrics['juice_yield_pct'], 2) if metrics['juice_yield_pct'] is not None else None
        extras = []
        if grape_weight_kg is not None:
            extras.append(f'{grape_weight_kg:g} kg raisin')
        if mustimeter_raw is not None:
            extras.append(f'mustimètre brut {mustimeter_raw:g}')
        if must_temperature_c is not None:
            extras.append(f'{must_temperature_c:g} °C')
        if corrected_density is not None:
            extras.append(f'MV corrigée 20°C {corrected_density:.2f} (arrondie {int(round(corrected_density))})')
        if sugar_g_l is not None:
            extras.append(f'sucres {sugar_g_l:.1f} g/L')
        if tav_potential is not None:
            extras.append(f'TAV probable {tav_potential:.2f}%')
        if juice_yield_l_per_100kg is not None:
            extras.append(f'rendement {juice_yield_l_per_100kg:.2f} L/100 kg')
        suffix = (' — ' + ', '.join(extras)) if extras else ''
        log_msg = f'Entrée {volume} hL vers {dest.id}{suffix}'
        tank_for_log = dest.id
    elif mtype in {'transfert', 'assemblage'}:
        if not source or not dest:
            raise HTTPException(status_code=400, detail='Source et destination obligatoires')
        if source.current_volume_hl < volume - 1e-6:
            raise HTTPException(status_code=400, detail='Volume insuffisant dans la source')
        if dest.current_volume_hl + volume > dest.capacity_hl + 1e-6:
            raise HTTPException(status_code=400, detail='Capacité dépassée')
        ensure_tank_not_blocked_for_fill(dest)
        source_lot_before = source.current_lot or lot
        source.current_volume_hl -= volume
        dest.current_volume_hl += volume
        if lot:
            source.current_lot_id = lot.id if source.current_volume_hl > 0 else None
            dest.current_lot_id = lot.id
        elif source.current_lot_id and not dest.current_lot_id:
            dest.current_lot_id = source.current_lot_id
        clear_cleaning_status_if_filled(dest)
        if source.current_volume_hl <= 0.0001:
            empty_tank_with_auto_status(source, source_lot_before)
        log_msg = f'{mtype.capitalize()} {volume} hL : {source.id} → {dest.id}'
        tank_for_log = dest.id
    elif mtype == 'sortie':
        if not source:
            raise HTTPException(status_code=400, detail='Cuve source obligatoire')
        if source.current_volume_hl < volume - 1e-6:
            raise HTTPException(status_code=400, detail='Volume insuffisant dans la cuve')
        source_lot_before = source.current_lot or lot
        source.current_volume_hl -= volume
        if source.current_volume_hl <= 0.0001:
            empty_tank_with_auto_status(source, source_lot_before)
        log_msg = f'Sortie {volume} hL depuis {source.id}'
        tank_for_log = source.id
    elif mtype == 'correction_manuelle':
        tank = source or dest
        if not tank:
            raise HTTPException(status_code=400, detail='Cuve obligatoire')
        if not comment:
            raise HTTPException(status_code=400, detail='Motif obligatoire')
        new_volume = float(payload.get('new_volume_hl'))
        if new_volume < 0 or new_volume > tank.capacity_hl + 1e-6:
            raise HTTPException(status_code=400, detail='Volume invalide')
        previous_lot = tank.current_lot or lot
        if new_volume > 0 and tank.current_volume_hl <= 0.0001:
            ensure_tank_not_blocked_for_fill(tank)
        tank.current_volume_hl = new_volume
        if new_volume == 0:
            empty_tank_with_auto_status(tank, previous_lot)
        elif lot:
            tank.current_lot_id = lot.id
            clear_cleaning_status_if_filled(tank)
        log_msg = f'Correction manuelle {tank.id} à {new_volume} hL'
        tank_for_log = tank.id
        volume = new_volume
    else:  # autre
        tank = source or dest
        if not tank:
            raise HTTPException(status_code=400, detail='Cuve obligatoire')
        if impact_volume:
            if volume is None:
                raise HTTPException(status_code=400, detail='Volume obligatoire')
            delta = float(volume)
            new_volume = tank.current_volume_hl + delta
            if new_volume < 0 or new_volume > tank.capacity_hl + 1e-6:
                raise HTTPException(status_code=400, detail='Volume invalide')
            previous_lot = tank.current_lot or lot
            if delta > 0 and tank.current_volume_hl <= 0.0001:
                ensure_tank_not_blocked_for_fill(tank)
            tank.current_volume_hl = new_volume
            if tank.current_volume_hl == 0:
                empty_tank_with_auto_status(tank, previous_lot)
        if lot and tank.current_volume_hl > 0:
            tank.current_lot_id = lot.id
            clear_cleaning_status_if_filled(tank)
        log_msg = f'Opération {operation_name} sur {tank.id}'
        tank_for_log = tank.id

    movement = Movement(
        movement_type=mtype,
        operation_name=operation_name,
        source_tank_id=source_id,
        destination_tank_id=dest_id,
        volume_hl=volume,
        grape_weight_kg=grape_weight_kg,
        mustimeter_raw=mustimeter_raw,
        corrected_density_20c=round(corrected_density, 2) if corrected_density is not None else None,
        sugar_g_l=sugar_g_l,
        must_temperature_c=must_temperature_c,
        tav_potential=tav_potential,
        juice_yield_l_per_100kg=juice_yield_l_per_100kg,
        juice_yield_pct=juice_yield_pct,
        lot_id=lot.id if lot else None,
        comment=comment,
        impact_volume=impact_volume,
        user_id=user.id,
    )
    db.add(movement)
    if source:
        source.updated_at = datetime.utcnow()
    if dest:
        dest.updated_at = datetime.utcnow()
    if mtype in {'correction_manuelle', 'autre'}:
        tank = source or dest
        tank.updated_at = datetime.utcnow()
    log_action(db, user, 'movement', log_msg, tank_id=tank_for_log, lot_id=lot.id if lot else None)
    db.commit()
    return {'ok': True}


@app.post('/api/tanks/{tank_id}/status')
def api_set_tank_status(tank_id: str, request: Request, payload: dict, db: Session = Depends(get_db)):
    user = require_user(request, db)
    tank = db.get(Tank, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail='Cuve introuvable')
    status = payload.get('manual_status') or None
    if status and status not in MANUAL_STATUSES:
        raise HTTPException(status_code=400, detail='Statut invalide')
    tank.manual_status = status
    tank.updated_at = datetime.utcnow()
    log_action(db, user, 'status_change', f'Statut de {tank.id} mis à {status or "automatique"}', tank_id=tank.id, lot_id=tank.current_lot_id)
    db.commit()
    return serialize_tank(tank)


@app.post('/api/tanks/{tank_id}/reset')
def api_reset_tank(tank_id: str, request: Request, payload: dict, db: Session = Depends(get_db)):
    user = require_user(request, db)
    require_role(user, EDIT_ROLES)
    tank = db.get(Tank, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail='Cuve introuvable')
    reason = (payload.get('reason') or '').strip()
    if not reason:
        raise HTTPException(status_code=400, detail='Motif obligatoire')
    previous_lot = tank.current_lot
    empty_tank_with_auto_status(tank, previous_lot)
    tank.updated_at = datetime.utcnow()
    db.add(Movement(movement_type='remise_a_zero', source_tank_id=tank.id, destination_tank_id=None, volume_hl=0, lot_id=None, comment=reason, impact_volume=True, user_id=user.id))
    log_action(db, user, 'reset', f'Remise à zéro de {tank.id} : {reason}', tank_id=tank.id)
    db.commit()
    return {'ok': True}


@app.get('/health')
def health():
    return {'ok': True}
