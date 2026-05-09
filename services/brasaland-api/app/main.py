from datetime import datetime, timedelta, timezone
import csv
import io
import os
from pathlib import Path
from sqlite3 import Connection, Row, connect
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(
    title="Brasaland API",
    version="0.1.0",
    description="API central MVP para locales y resumen de ventas.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Store(BaseModel):
    id: str
    name: str
    country: Literal["CO", "US"]
    city: str
    timezone: str
    base_currency: Literal["COP", "USD"]


class SalesSummary(BaseModel):
    period: str
    currency: Literal["COP", "USD"]
    total_sales: float
    average_ticket: float
    generated_at: datetime


class SaleEventCreate(BaseModel):
    store_id: str
    sold_at: datetime
    total_amount: float
    currency: Literal["COP", "USD"]


class SaleEventCreated(BaseModel):
    id: int
    store_id: str
    sold_at: datetime
    total_amount: float
    currency: Literal["COP", "USD"]


class MarketSummary(BaseModel):
    market: str
    sales: float
    average_ticket: float
    wow_variation_pct: float


class FinanceKpiSummary(BaseModel):
    currency: Literal["COP", "USD"]
    total_revenue: float
    estimated_cogs: float
    estimated_gross_profit: float
    gross_margin_pct: float
    generated_at: datetime


class AuditLogEntry(BaseModel):
    id: int
    happened_at: datetime
    role: str
    action: str
    outcome: str
    target: str
    details: str


class DailySalesPoint(BaseModel):
    day: str
    total_sales: float
    tickets: int


class StoreSalesRow(BaseModel):
    store_id: str
    store_name: str
    market: str
    tickets: int
    total_sales: float
    average_ticket: float
    currency: Literal["COP", "USD"]


class InactivityAlert(BaseModel):
    store_id: str
    store_name: str
    market: str
    store_timezone: str
    minutes_without_sales: int
    severity: Literal["warning", "critical"]
    last_sale_at: datetime | None
    last_sale_local: datetime | None
    alert_status: Literal["new", "acknowledged", "resolved"]
    alert_owner: str | None
    alert_note: str | None
    alert_updated_at: datetime | None
    recommended_action: str


class InactivityAlertResponse(BaseModel):
    window_minutes: int
    active_stores: int
    total_stores: int
    total_alerts: int
    critical_alerts: int
    warning_alerts: int
    critical_ratio_pct: float
    risk_level: Literal["low", "medium", "high"]
    generated_at: datetime
    alerts: list[InactivityAlert]


class InactivityAlertSlaSummary(BaseModel):
    period_days: int
    sla_target_minutes: int
    total_actions: int
    acknowledged_actions: int
    resolved_actions: int
    resolved_after_ack_count: int
    avg_minutes_ack_to_resolve: float
    resolved_within_sla_pct: float
    generated_at: datetime


class TrainingResourceSummary(BaseModel):
    id: str
    title: str
    category: Literal["recipe", "sop", "onboarding"]
    locale: Literal["es", "en"]
    tags: list[str]
    version: str
    updated_at: datetime


class TrainingResourceDetail(TrainingResourceSummary):
    content: str


class HrResourceSummary(BaseModel):
    id: str
    title: str
    resource_type: Literal["onboarding", "policy", "faq"]
    locale: Literal["es", "en"]
    tags: list[str]
    version: str
    updated_at: datetime


class HrResourceDetail(HrResourceSummary):
    content: str


class ExecutiveAskResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    requires_follow_up: bool
    follow_up_questions: list[str]
    generated_at: datetime


class WeeklyExecutiveReportResponse(BaseModel):
    currency: Literal["COP", "USD"]
    generated_at: datetime
    summary: SalesSummary
    markets: list[MarketSummary]
    inactivity: InactivityAlertResponse
    alerts_sla: InactivityAlertSlaSummary


class AlertActionCreate(BaseModel):
    store_id: str
    status: Literal["acknowledged", "resolved"]
    owner: str | None = None
    note: str | None = None


class AlertActionCreated(BaseModel):
    id: int
    store_id: str
    status: Literal["acknowledged", "resolved"]
    owner: str | None
    note: str | None
    updated_at: datetime
    updated_by_role: str


DB_PATH = Path(__file__).resolve().parent.parent / "brasaland.db"
FX_COP_PER_USD = 3950.0
DEFAULT_API_TOKEN = "brasaland-dev-token"
DEFAULT_ROLE_TOKENS: dict[str, str] = {
    "admin": "brasaland-admin-token",
    "executive": "brasaland-executive-token",
    "operations": "brasaland-operations-token",
    "finance": "brasaland-finance-token",
}
ESTIMATED_COGS_RATIO_BY_COUNTRY: dict[str, float] = {
    "CO": 0.56,
    "US": 0.49,
}


def get_db() -> Connection:
    connection = connect(DB_PATH)
    connection.row_factory = Row
    return connection


def parse_date_or_none(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="start_date/end_date must use YYYY-MM-DD") from exc
    return parsed


def convert_amount(amount: float, source_currency: str, target_currency: str) -> float:
    if source_currency == target_currency:
        return amount
    if source_currency == "COP" and target_currency == "USD":
        return amount / FX_COP_PER_USD
    if source_currency == "USD" and target_currency == "COP":
        return amount * FX_COP_PER_USD
    return amount


def period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "day":
        return now - timedelta(days=1)
    if period == "month":
        return now - timedelta(days=30)
    return now - timedelta(days=7)


def require_api_token(x_api_token: str | None = Header(default=None)) -> None:
    configured_token = os.getenv("BRASALAND_API_TOKEN", DEFAULT_API_TOKEN)
    if x_api_token != configured_token:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Token")


def resolve_role_tokens() -> dict[str, str]:
    return {
        "admin": os.getenv("BRASALAND_ADMIN_TOKEN", DEFAULT_ROLE_TOKENS["admin"]),
        "executive": os.getenv("BRASALAND_EXECUTIVE_TOKEN", DEFAULT_ROLE_TOKENS["executive"]),
        "operations": os.getenv("BRASALAND_OPERATIONS_TOKEN", DEFAULT_ROLE_TOKENS["operations"]),
        "finance": os.getenv("BRASALAND_FINANCE_TOKEN", DEFAULT_ROLE_TOKENS["finance"]),
    }


def require_roles(allowed_roles: set[str]):
    def validator(x_api_token: str | None = Header(default=None), x_api_role: str | None = Header(default=None)) -> str:
        if x_api_role is None or x_api_role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Role not allowed")

        role_tokens = resolve_role_tokens()
        expected_token = role_tokens.get(x_api_role)
        if expected_token is None or x_api_token != expected_token:
            raise HTTPException(status_code=401, detail="Invalid role token")

        return x_api_role

    return validator


def write_audit_log(role: str, action: str, outcome: str, target: str, details: str = "") -> None:
    happened_at = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        db.execute(
            """
            INSERT INTO audit_logs (happened_at, role, action, outcome, target, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (happened_at, role, action, outcome, target, details[:1000]),
        )


def resolve_period_bounds(
    period: str,
    start_date: str | None,
    end_date: str | None,
) -> tuple[datetime, datetime]:
    start_at = parse_date_or_none(start_date) or period_start(period)
    end_at = (parse_date_or_none(end_date) or datetime.now(timezone.utc)) + timedelta(days=1)
    if end_at <= start_at:
        raise HTTPException(status_code=400, detail="end_date must be greater than start_date")
    return start_at, end_at


def parse_datetime_or_none(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="sold_at must be ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def init_db() -> None:
    stores = [
        ("med-001", "Brasaland Laureles", "CO", "Medellin", "America/Bogota", "COP"),
        ("med-002", "Brasaland El Poblado", "CO", "Medellin", "America/Bogota", "COP"),
        ("mia-001", "Brasaland Doral", "US", "Miami", "America/New_York", "USD"),
        ("mia-002", "Brasaland Kendall", "US", "Miami", "America/New_York", "USD"),
    ]

    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS stores (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT NOT NULL,
                timezone TEXT NOT NULL,
                base_currency TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT NOT NULL,
                sold_at TEXT NOT NULL,
                total_amount REAL NOT NULL,
                currency TEXT NOT NULL,
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                happened_at TEXT NOT NULL,
                role TEXT NOT NULL,
                action TEXT NOT NULL,
                outcome TEXT NOT NULL,
                target TEXT NOT NULL,
                details TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT NOT NULL,
                status TEXT NOT NULL,
                owner TEXT,
                note TEXT,
                updated_at TEXT NOT NULL,
                updated_by_role TEXT NOT NULL,
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS training_resources (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                locale TEXT NOT NULL,
                tags TEXT NOT NULL,
                version TEXT NOT NULL,
                content TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_resources (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                locale TEXT NOT NULL,
                tags TEXT NOT NULL,
                version TEXT NOT NULL,
                content TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        db.executemany(
            """
            INSERT OR IGNORE INTO stores (id, name, country, city, timezone, base_currency)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            stores,
        )

        existing_events = db.execute("SELECT COUNT(*) AS c FROM sales_events").fetchone()["c"]
        if existing_events == 0:
            now = datetime.now(timezone.utc)
            seed_events: list[tuple[str, str, float, str]] = []
            for day_delta in range(0, 14):
                for hour in (12, 14, 18, 20):
                    sold_at = (now - timedelta(days=day_delta)).replace(
                        hour=hour,
                        minute=0,
                        second=0,
                        microsecond=0,
                    )
                    if sold_at > now:
                        sold_at -= timedelta(days=1)
                    seed_events.extend(
                        [
                            ("med-001", sold_at.isoformat(), 65200.0 + (day_delta * 250), "COP"),
                            ("med-002", sold_at.isoformat(), 71300.0 + (day_delta * 220), "COP"),
                            ("mia-001", sold_at.isoformat(), 18.7 + (day_delta * 0.12), "USD"),
                            ("mia-002", sold_at.isoformat(), 20.1 + (day_delta * 0.11), "USD"),
                        ]
                    )

            db.executemany(
                """
                INSERT INTO sales_events (store_id, sold_at, total_amount, currency)
                VALUES (?, ?, ?, ?)
                """,
                seed_events,
            )

        existing_training = db.execute("SELECT COUNT(*) AS c FROM training_resources").fetchone()["c"]
        if existing_training == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            training_seed = [
                (
                    "rec-brasa-pollo-v1",
                    "Receta base: Pollo a la brasa",
                    "recipe",
                    "es",
                    "pollo,brasa,coccion,calidad",
                    "v1.0",
                    "1) Marinar 12h. 2) Precalentar horno/parrilla. 3) Coccion objetivo: 74C interna. 4) Reposo 5 min.",
                    now_iso,
                ),
                (
                    "sop-apertura-cocina-v1",
                    "SOP: Apertura de cocina",
                    "sop",
                    "es",
                    "apertura,checklist,inocuidad",
                    "v1.0",
                    "Checklist apertura: higiene, mise en place, temperaturas, equipos, stock critico.",
                    now_iso,
                ),
                (
                    "onb-caja-dia1-v1",
                    "Onboarding caja - Dia 1",
                    "onboarding",
                    "es",
                    "onboarding,caja,pos,servicio",
                    "v1.0",
                    "Objetivo dia 1: login POS, flujo de cobro, manejo de anulaciones y cierre de turno asistido.",
                    now_iso,
                ),
                (
                    "sop-kitchen-opening-v1",
                    "SOP: Kitchen opening",
                    "sop",
                    "en",
                    "opening,checklist,food-safety",
                    "v1.0",
                    "Opening checklist: sanitation, mise en place, temperature checks, equipment and critical stock.",
                    now_iso,
                ),
            ]
            db.executemany(
                """
                INSERT INTO training_resources (id, title, category, locale, tags, version, content, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                training_seed,
            )

        existing_hr = db.execute("SELECT COUNT(*) AS c FROM hr_resources").fetchone()["c"]
        if existing_hr == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            hr_seed = [
                (
                    "hr-onb-cocina-001",
                    "Onboarding cocina - Semana 1",
                    "onboarding",
                    "es",
                    "onboarding,cocina,checklist,turno",
                    "v1.0",
                    "Dia 1: induccion y seguridad. Dia 2-3: estaciones. Dia 4-5: evaluacion asistida en turno.",
                    now_iso,
                ),
                (
                    "hr-pol-vacaciones-001",
                    "Politica de vacaciones y ausencias",
                    "policy",
                    "es",
                    "rrhh,vacaciones,ausencias,politica",
                    "v1.0",
                    "Solicitud con 15 dias de anticipacion. Aprobacion por manager y validacion RRHH.",
                    now_iso,
                ),
                (
                    "hr-faq-miami-001",
                    "FAQ RRHH Florida",
                    "faq",
                    "en",
                    "hr,faq,florida,payroll",
                    "v1.0",
                    "Common questions: payroll dates, schedule changes, time-off requests and mandatory documents.",
                    now_iso,
                ),
            ]
            db.executemany(
                """
                INSERT INTO hr_resources (id, title, resource_type, locale, tags, version, content, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                hr_seed,
            )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/stores", response_model=list[Store])
def get_stores() -> list[Store]:
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, country, city, timezone, base_currency FROM stores ORDER BY id"
        ).fetchall()
    return [Store(**dict(row)) for row in rows]


@app.post("/api/v1/sales/events", response_model=SaleEventCreated, status_code=201)
def create_sales_event(
    payload: SaleEventCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> SaleEventCreated:
    if payload.total_amount <= 0:
        write_audit_log(role, "create_sale_event", "rejected", payload.store_id, "total_amount <= 0")
        raise HTTPException(status_code=400, detail="total_amount must be greater than zero")

    with get_db() as db:
        exists = db.execute(
            "SELECT 1 FROM stores WHERE id = ?",
            (payload.store_id,),
        ).fetchone()
        if exists is None:
            write_audit_log(role, "create_sale_event", "rejected", payload.store_id, "store_id not found")
            raise HTTPException(status_code=404, detail="store_id not found")

        cursor = db.execute(
            """
            INSERT INTO sales_events (store_id, sold_at, total_amount, currency)
            VALUES (?, ?, ?, ?)
            """,
            (
                payload.store_id,
                payload.sold_at.astimezone(timezone.utc).isoformat(),
                payload.total_amount,
                payload.currency,
            ),
        )
        created_id = int(cursor.lastrowid)

    write_audit_log(
        role,
        "create_sale_event",
        "success",
        payload.store_id,
        f"id={created_id}, amount={payload.total_amount}, currency={payload.currency}",
    )

    return SaleEventCreated(
        id=created_id,
        store_id=payload.store_id,
        sold_at=payload.sold_at,
        total_amount=payload.total_amount,
        currency=payload.currency,
    )


@app.get("/api/v1/sales/summary", response_model=SalesSummary)
def get_sales_summary(
    period: str = Query(default="week"),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    country: Literal["CO", "US"] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> SalesSummary:
    start_at, end_at = resolve_period_bounds(period, start_date, end_date)

    with get_db() as db:
        rows = db.execute(
            """
            SELECT se.total_amount, se.currency
            FROM sales_events se
            JOIN stores st ON st.id = se.store_id
            WHERE se.sold_at >= ? AND se.sold_at < ?
              AND (? IS NULL OR st.country = ?)
            """,
            (start_at.isoformat(), end_at.isoformat(), country, country),
        ).fetchall()

    totals = [convert_amount(row["total_amount"], row["currency"], currency) for row in rows]
    total_sales = sum(totals)
    average_ticket = total_sales / len(totals) if totals else 0.0

    return SalesSummary(
        period=period,
        currency=currency,
        total_sales=total_sales,
        average_ticket=average_ticket,
        generated_at=datetime.now(timezone.utc),
    )


@app.get("/api/v1/markets/summary", response_model=list[MarketSummary])
def get_market_summary(
    currency: Literal["COP", "USD"] = Query(default="USD"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    country: Literal["CO", "US"] | None = Query(default=None),
) -> list[MarketSummary]:
    start_at, end_at = resolve_period_bounds("week", start_date, end_date)
    previous_start = start_at - (end_at - start_at)
    previous_end = start_at

    with get_db() as db:
        rows = db.execute(
            """
            SELECT st.country, se.total_amount, se.currency
            FROM sales_events se
            JOIN stores st ON st.id = se.store_id
            WHERE se.sold_at >= ? AND se.sold_at < ?
              AND (? IS NULL OR st.country = ?)
            """,
            (start_at.isoformat(), end_at.isoformat(), country, country),
        ).fetchall()

        previous_rows = db.execute(
            """
            SELECT st.country, se.total_amount, se.currency
            FROM sales_events se
            JOIN stores st ON st.id = se.store_id
            WHERE se.sold_at >= ? AND se.sold_at < ?
              AND (? IS NULL OR st.country = ?)
            """,
            (previous_start.isoformat(), previous_end.isoformat(), country, country),
        ).fetchall()

    grouped: dict[str, list[float]] = {"CO": [], "US": []}
    for row in rows:
        grouped[row["country"]].append(convert_amount(row["total_amount"], row["currency"], currency))

    previous_grouped: dict[str, list[float]] = {"CO": [], "US": []}
    for row in previous_rows:
        previous_grouped[row["country"]].append(
            convert_amount(row["total_amount"], row["currency"], currency)
        )

    output: list[MarketSummary] = []
    for key, label in (("CO", "Colombia"), ("US", "Florida")):
        values = grouped[key]
        if country is not None and key != country:
            continue
        sales = sum(values)
        average_ticket = sales / len(values) if values else 0.0
        previous_sales = sum(previous_grouped[key])
        wow = 0.0
        if previous_sales > 0:
            wow = ((sales - previous_sales) / previous_sales) * 100
        output.append(
            MarketSummary(
                market=label,
                sales=sales,
                average_ticket=average_ticket,
                wow_variation_pct=round(wow, 2),
            )
        )

    return output


@app.get("/api/v1/sales/by-store", response_model=list[StoreSalesRow])
def get_sales_by_store(
    currency: Literal["COP", "USD"] = Query(default="USD"),
    country: Literal["CO", "US"] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> list[StoreSalesRow]:
    start_at, end_at = resolve_period_bounds("week", start_date, end_date)

    with get_db() as db:
        rows = db.execute(
            """
            SELECT st.id, st.name, st.country, se.total_amount, se.currency
            FROM sales_events se
            JOIN stores st ON st.id = se.store_id
            WHERE se.sold_at >= ? AND se.sold_at < ?
              AND (? IS NULL OR st.country = ?)
            ORDER BY st.id
            """,
            (start_at.isoformat(), end_at.isoformat(), country, country),
        ).fetchall()

    grouped: dict[str, dict[str, float | int | str]] = {}
    for row in rows:
        store_id = row["id"]
        if store_id not in grouped:
            grouped[store_id] = {
                "store_id": store_id,
                "store_name": row["name"],
                "market": "Colombia" if row["country"] == "CO" else "Florida",
                "tickets": 0,
                "total_sales": 0.0,
            }
        grouped[store_id]["tickets"] += 1
        grouped[store_id]["total_sales"] += convert_amount(row["total_amount"], row["currency"], currency)

    output: list[StoreSalesRow] = []
    for item in grouped.values():
        tickets = int(item["tickets"])
        total_sales = float(item["total_sales"])
        output.append(
            StoreSalesRow(
                store_id=str(item["store_id"]),
                store_name=str(item["store_name"]),
                market=str(item["market"]),
                tickets=tickets,
                total_sales=total_sales,
                average_ticket=(total_sales / tickets if tickets else 0.0),
                currency=currency,
            )
        )
    return output


@app.get("/api/v1/sales/daily-trend", response_model=list[DailySalesPoint])
def get_sales_daily_trend(
    currency: Literal["COP", "USD"] = Query(default="USD"),
    country: Literal["CO", "US"] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> list[DailySalesPoint]:
    start_at, end_at = resolve_period_bounds("week", start_date, end_date)

    with get_db() as db:
        rows = db.execute(
            """
            SELECT se.sold_at, se.total_amount, se.currency
            FROM sales_events se
            JOIN stores st ON st.id = se.store_id
            WHERE se.sold_at >= ? AND se.sold_at < ?
              AND (? IS NULL OR st.country = ?)
            ORDER BY se.sold_at ASC
            """,
            (start_at.isoformat(), end_at.isoformat(), country, country),
        ).fetchall()

    grouped: dict[str, dict[str, float | int]] = {}
    for row in rows:
        sold_at = parse_datetime_or_none(row["sold_at"])
        if sold_at is None:
            continue
        key = sold_at.date().isoformat()
        if key not in grouped:
            grouped[key] = {"total_sales": 0.0, "tickets": 0}
        grouped[key]["total_sales"] += convert_amount(row["total_amount"], row["currency"], currency)
        grouped[key]["tickets"] += 1

    output: list[DailySalesPoint] = []
    for day in sorted(grouped.keys()):
        output.append(
            DailySalesPoint(
                day=day,
                total_sales=float(grouped[day]["total_sales"]),
                tickets=int(grouped[day]["tickets"]),
            )
        )
    return output


@app.get("/api/v1/alerts/inactivity", response_model=InactivityAlertResponse)
def get_inactivity_alerts(
    window_minutes: int = Query(default=60, ge=15, le=240),
    country: Literal["CO", "US"] | None = Query(default=None),
    severity_filter: Literal["warning", "critical"] | None = Query(default=None, alias="severity"),
    limit: int = Query(default=20, ge=1, le=100),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> InactivityAlertResponse:
    now = datetime.now(timezone.utc)
    alerts: list[InactivityAlert] = []

    with get_db() as db:
        stores = db.execute(
            """
            SELECT id, name, country, timezone
            FROM stores
            WHERE (? IS NULL OR country = ?)
            ORDER BY id
            """,
            (country, country),
        ).fetchall()

        alert_action_rows = db.execute(
            """
            SELECT aa.store_id, aa.status, aa.owner, aa.note, aa.updated_at
            FROM alert_actions aa
            JOIN (
                SELECT store_id, MAX(id) AS max_id
                FROM alert_actions
                GROUP BY store_id
            ) latest ON latest.max_id = aa.id
            """
        ).fetchall()
        latest_actions_by_store = {row["store_id"]: row for row in alert_action_rows}

        for store in stores:
            row = db.execute(
                "SELECT MAX(sold_at) AS last_sale_at FROM sales_events WHERE store_id = ?",
                (store["id"],),
            ).fetchone()

            parsed_last_sale_at: datetime | None = None
            if row is None or row["last_sale_at"] is None:
                minutes_without_sales = 10_000
            else:
                parsed_last_sale_at = datetime.fromisoformat(row["last_sale_at"])
                if parsed_last_sale_at.tzinfo is None:
                    parsed_last_sale_at = parsed_last_sale_at.replace(tzinfo=timezone.utc)
                minutes_without_sales = int((now - parsed_last_sale_at).total_seconds() // 60)

            parsed_last_sale_local: datetime | None = None
            if parsed_last_sale_at is not None:
                try:
                    parsed_last_sale_local = parsed_last_sale_at.astimezone(ZoneInfo(store["timezone"]))
                except Exception:
                    parsed_last_sale_local = parsed_last_sale_at

            if minutes_without_sales > window_minutes:
                alert_severity: Literal["warning", "critical"] = (
                    "critical" if minutes_without_sales > (window_minutes * 2) else "warning"
                )
                action_row = latest_actions_by_store.get(store["id"])
                alert_status: Literal["new", "acknowledged", "resolved"] = "new"
                alert_owner: str | None = None
                alert_note: str | None = None
                alert_updated_at: datetime | None = None

                if action_row is not None:
                    candidate_updated_at = datetime.fromisoformat(action_row["updated_at"])
                    if candidate_updated_at.tzinfo is None:
                        candidate_updated_at = candidate_updated_at.replace(tzinfo=timezone.utc)
                    # If there were newer sales after action, action is stale and alert returns to "new".
                    is_stale_action = parsed_last_sale_at is not None and parsed_last_sale_at > candidate_updated_at
                    if not is_stale_action:
                        alert_status = action_row["status"]
                        alert_owner = action_row["owner"]
                        alert_note = action_row["note"]
                        alert_updated_at = candidate_updated_at

                alerts.append(
                    InactivityAlert(
                        store_id=store["id"],
                        store_name=store["name"],
                        market="Colombia" if store["country"] == "CO" else "Florida",
                        store_timezone=store["timezone"],
                        minutes_without_sales=minutes_without_sales,
                        severity=alert_severity,
                        last_sale_at=parsed_last_sale_at,
                        last_sale_local=parsed_last_sale_local,
                        alert_status=alert_status,
                        alert_owner=alert_owner,
                        alert_note=alert_note,
                        alert_updated_at=alert_updated_at,
                        recommended_action=(
                            "Contact store manager and validate POS/connectivity immediately"
                            if alert_severity == "critical"
                            else "Monitor next 30 minutes and verify staffing and ticket flow"
                        ),
                    )
                )

    alerts.sort(key=lambda item: item.minutes_without_sales, reverse=True)

    total_stores = len(stores)
    raw_alerts_count = len(alerts)

    if severity_filter is not None:
        alerts = [item for item in alerts if item.severity == severity_filter]

    alerts = alerts[:limit]
    critical_alerts = len([item for item in alerts if item.severity == "critical"])
    warning_alerts = len([item for item in alerts if item.severity == "warning"])
    critical_ratio_pct = round((critical_alerts / total_stores) * 100, 2) if total_stores > 0 else 0.0
    if critical_ratio_pct >= 50:
        risk_level: Literal["low", "medium", "high"] = "high"
    elif critical_ratio_pct >= 20:
        risk_level = "medium"
    else:
        risk_level = "low"

    write_audit_log(
        role,
        "read_inactivity_alerts",
        "success",
        f"country={country or 'ALL'}",
        f"window_minutes={window_minutes}, severity={severity_filter or 'ALL'}, alerts={len(alerts)}",
    )

    return InactivityAlertResponse(
        window_minutes=window_minutes,
        active_stores=total_stores - raw_alerts_count,
        total_stores=total_stores,
        total_alerts=len(alerts),
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts,
        critical_ratio_pct=critical_ratio_pct,
        risk_level=risk_level,
        generated_at=now,
        alerts=alerts,
    )


@app.get("/api/v1/alerts/inactivity/sla", response_model=InactivityAlertSlaSummary)
def get_inactivity_alerts_sla(
    days: int = Query(default=7, ge=1, le=30),
    sla_target_minutes: int = Query(default=30, ge=5, le=240),
    country: Literal["CO", "US"] | None = Query(default=None),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> InactivityAlertSlaSummary:
    now = datetime.now(timezone.utc)
    start_at = now - timedelta(days=days)

    with get_db() as db:
        rows = db.execute(
            """
            SELECT aa.store_id, aa.status, aa.updated_at
            FROM alert_actions aa
            JOIN stores st ON st.id = aa.store_id
            WHERE aa.updated_at >= ?
              AND (? IS NULL OR st.country = ?)
            ORDER BY aa.store_id ASC, aa.updated_at ASC, aa.id ASC
            """,
            (start_at.isoformat(), country, country),
        ).fetchall()

    total_actions = len(rows)
    acknowledged_actions = len([row for row in rows if row["status"] == "acknowledged"])
    resolved_actions = len([row for row in rows if row["status"] == "resolved"])

    durations_minutes: list[float] = []
    last_ack_by_store: dict[str, datetime] = {}
    for row in rows:
        updated_at = datetime.fromisoformat(row["updated_at"])
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        if row["status"] == "acknowledged":
            last_ack_by_store[row["store_id"]] = updated_at
            continue

        if row["status"] == "resolved":
            ack_at = last_ack_by_store.get(row["store_id"])
            if ack_at is not None and updated_at >= ack_at:
                durations_minutes.append((updated_at - ack_at).total_seconds() / 60)

    resolved_after_ack_count = len(durations_minutes)
    avg_minutes_ack_to_resolve = round(sum(durations_minutes) / resolved_after_ack_count, 2) if resolved_after_ack_count > 0 else 0.0
    resolved_within_sla = len([value for value in durations_minutes if value <= sla_target_minutes])
    resolved_within_sla_pct = (
        round((resolved_within_sla / resolved_after_ack_count) * 100, 2) if resolved_after_ack_count > 0 else 0.0
    )

    write_audit_log(
        role,
        "read_inactivity_alerts_sla",
        "success",
        f"country={country or 'ALL'}",
        f"days={days}, actions={total_actions}, within_sla_pct={resolved_within_sla_pct}",
    )

    return InactivityAlertSlaSummary(
        period_days=days,
        sla_target_minutes=sla_target_minutes,
        total_actions=total_actions,
        acknowledged_actions=acknowledged_actions,
        resolved_actions=resolved_actions,
        resolved_after_ack_count=resolved_after_ack_count,
        avg_minutes_ack_to_resolve=avg_minutes_ack_to_resolve,
        resolved_within_sla_pct=resolved_within_sla_pct,
        generated_at=now,
    )


@app.post("/api/v1/alerts/inactivity/actions", response_model=AlertActionCreated, status_code=201)
def create_inactivity_alert_action(
    payload: AlertActionCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> AlertActionCreated:
    updated_at = datetime.now(timezone.utc)

    with get_db() as db:
        exists = db.execute("SELECT 1 FROM stores WHERE id = ?", (payload.store_id,)).fetchone()
        if exists is None:
            write_audit_log(role, "create_alert_action", "rejected", payload.store_id, "store_id not found")
            raise HTTPException(status_code=404, detail="store_id not found")

        cursor = db.execute(
            """
            INSERT INTO alert_actions (store_id, status, owner, note, updated_at, updated_by_role)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.store_id,
                payload.status,
                payload.owner,
                (payload.note or "")[:1000],
                updated_at.isoformat(),
                role,
            ),
        )
        created_id = int(cursor.lastrowid)

    write_audit_log(
        role,
        "create_alert_action",
        "success",
        payload.store_id,
        f"status={payload.status}, owner={payload.owner or ''}",
    )

    return AlertActionCreated(
        id=created_id,
        store_id=payload.store_id,
        status=payload.status,
        owner=payload.owner,
        note=(payload.note or "")[:1000],
        updated_at=updated_at,
        updated_by_role=role,
    )


@app.get("/api/v1/reports/sales.csv")
def export_sales_report_csv(
    currency: Literal["COP", "USD"] = Query(default="USD"),
    country: Literal["CO", "US"] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    role: str = Depends(require_roles({"executive", "finance", "admin"})),
) -> Response:
    start_at, end_at = resolve_period_bounds("week", start_date, end_date)

    with get_db() as db:
        rows = db.execute(
            """
            SELECT st.id, st.name, st.country, se.sold_at, se.total_amount, se.currency
            FROM sales_events se
            JOIN stores st ON st.id = se.store_id
            WHERE se.sold_at >= ? AND se.sold_at < ?
              AND (? IS NULL OR st.country = ?)
            ORDER BY se.sold_at ASC
            """,
            (start_at.isoformat(), end_at.isoformat(), country, country),
        ).fetchall()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["store_id", "store_name", "country", "sold_at", "amount", "currency"])
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["name"],
                row["country"],
                row["sold_at"],
                f"{convert_amount(row['total_amount'], row['currency'], currency):.2f}",
                currency,
            ]
        )

    filename = f"brasaland-sales-{datetime.now(timezone.utc).date().isoformat()}.csv"
    write_audit_log(
        role,
        "export_sales_csv",
        "success",
        f"country={country or 'ALL'}",
        f"rows={len(rows)}, currency={currency}",
    )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/v1/finance/kpis", response_model=FinanceKpiSummary)
def get_finance_kpis(
    currency: Literal["COP", "USD"] = Query(default="USD"),
    country: Literal["CO", "US"] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    role: str = Depends(require_roles({"finance", "executive", "admin"})),
) -> FinanceKpiSummary:
    start_at, end_at = resolve_period_bounds("week", start_date, end_date)

    with get_db() as db:
        rows = db.execute(
            """
            SELECT st.country, se.total_amount, se.currency
            FROM sales_events se
            JOIN stores st ON st.id = se.store_id
            WHERE se.sold_at >= ? AND se.sold_at < ?
              AND (? IS NULL OR st.country = ?)
            """,
            (start_at.isoformat(), end_at.isoformat(), country, country),
        ).fetchall()

    total_revenue = 0.0
    estimated_cogs = 0.0
    for row in rows:
        amount = convert_amount(row["total_amount"], row["currency"], currency)
        ratio = ESTIMATED_COGS_RATIO_BY_COUNTRY.get(row["country"], 0.55)
        total_revenue += amount
        estimated_cogs += amount * ratio

    gross_profit = total_revenue - estimated_cogs
    margin_pct = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    write_audit_log(
        role,
        "read_finance_kpis",
        "success",
        f"country={country or 'ALL'}",
        f"currency={currency}, revenue={round(total_revenue, 2)}",
    )

    return FinanceKpiSummary(
        currency=currency,
        total_revenue=round(total_revenue, 2),
        estimated_cogs=round(estimated_cogs, 2),
        estimated_gross_profit=round(gross_profit, 2),
        gross_margin_pct=round(margin_pct, 2),
        generated_at=datetime.now(timezone.utc),
    )


@app.get("/api/v1/audit/logs", response_model=list[AuditLogEntry])
def get_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    role: str = Depends(require_roles({"admin"})),
) -> list[AuditLogEntry]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, happened_at, role, action, outcome, target, details
            FROM audit_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    write_audit_log(role, "read_audit_logs", "success", "audit_logs", f"limit={limit}")

    output: list[AuditLogEntry] = []
    for row in rows:
        happened_at = parse_datetime_or_none(row["happened_at"]) or datetime.now(timezone.utc)
        output.append(
            AuditLogEntry(
                id=row["id"],
                happened_at=happened_at,
                role=row["role"],
                action=row["action"],
                outcome=row["outcome"],
                target=row["target"],
                details=row["details"],
            )
        )
    return output


@app.get("/api/v1/training/resources", response_model=list[TrainingResourceSummary])
def get_training_resources(
    q: str | None = Query(default=None),
    category: Literal["recipe", "sop", "onboarding"] | None = Query(default=None),
    locale: Literal["es", "en"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    role: str = Depends(require_roles({"operations", "admin", "executive"})),
) -> list[TrainingResourceSummary]:
    search = (q or "").strip().lower()
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, title, category, locale, tags, version, updated_at
            FROM training_resources
            WHERE (? IS NULL OR category = ?)
              AND (? IS NULL OR locale = ?)
            ORDER BY updated_at DESC, id ASC
            """,
            (category, category, locale, locale),
        ).fetchall()

    output: list[TrainingResourceSummary] = []
    for row in rows:
        tags = [tag.strip() for tag in row["tags"].split(",") if tag.strip()]
        haystack = f"{row['title']} {' '.join(tags)}".lower()
        if search and search not in haystack:
            continue
        updated_at = parse_datetime_or_none(row["updated_at"]) or datetime.now(timezone.utc)
        output.append(
            TrainingResourceSummary(
                id=row["id"],
                title=row["title"],
                category=row["category"],
                locale=row["locale"],
                tags=tags,
                version=row["version"],
                updated_at=updated_at,
            )
        )

    write_audit_log(
        role,
        "read_training_resources",
        "success",
        f"category={category or 'ALL'}",
        f"locale={locale or 'ALL'}, q={search or '-'}, results={min(len(output), limit)}",
    )
    return output[:limit]


@app.get("/api/v1/training/resources/{resource_id}", response_model=TrainingResourceDetail)
def get_training_resource_detail(
    resource_id: str,
    role: str = Depends(require_roles({"operations", "admin", "executive"})),
) -> TrainingResourceDetail:
    with get_db() as db:
        row = db.execute(
            """
            SELECT id, title, category, locale, tags, version, content, updated_at
            FROM training_resources
            WHERE id = ?
            """,
            (resource_id,),
        ).fetchone()

    if row is None:
        write_audit_log(role, "read_training_resource_detail", "rejected", resource_id, "not found")
        raise HTTPException(status_code=404, detail="training resource not found")

    updated_at = parse_datetime_or_none(row["updated_at"]) or datetime.now(timezone.utc)
    tags = [tag.strip() for tag in row["tags"].split(",") if tag.strip()]

    write_audit_log(role, "read_training_resource_detail", "success", resource_id, f"version={row['version']}")

    return TrainingResourceDetail(
        id=row["id"],
        title=row["title"],
        category=row["category"],
        locale=row["locale"],
        tags=tags,
        version=row["version"],
        updated_at=updated_at,
        content=row["content"],
    )


@app.get("/api/v1/hr/resources", response_model=list[HrResourceSummary])
def get_hr_resources(
    q: str | None = Query(default=None),
    resource_type: Literal["onboarding", "policy", "faq"] | None = Query(default=None),
    locale: Literal["es", "en"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    role: str = Depends(require_roles({"operations", "admin", "executive"})),
) -> list[HrResourceSummary]:
    search = (q or "").strip().lower()
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, title, resource_type, locale, tags, version, updated_at
            FROM hr_resources
            WHERE (? IS NULL OR resource_type = ?)
              AND (? IS NULL OR locale = ?)
            ORDER BY updated_at DESC, id ASC
            """,
            (resource_type, resource_type, locale, locale),
        ).fetchall()

    output: list[HrResourceSummary] = []
    for row in rows:
        tags = [tag.strip() for tag in row["tags"].split(",") if tag.strip()]
        haystack = f"{row['title']} {' '.join(tags)}".lower()
        if search and search not in haystack:
            continue
        updated_at = parse_datetime_or_none(row["updated_at"]) or datetime.now(timezone.utc)
        output.append(
            HrResourceSummary(
                id=row["id"],
                title=row["title"],
                resource_type=row["resource_type"],
                locale=row["locale"],
                tags=tags,
                version=row["version"],
                updated_at=updated_at,
            )
        )

    write_audit_log(
        role,
        "read_hr_resources",
        "success",
        f"type={resource_type or 'ALL'}",
        f"locale={locale or 'ALL'}, q={search or '-'}, results={min(len(output), limit)}",
    )
    return output[:limit]


@app.get("/api/v1/hr/resources/{resource_id}", response_model=HrResourceDetail)
def get_hr_resource_detail(
    resource_id: str,
    role: str = Depends(require_roles({"operations", "admin", "executive"})),
) -> HrResourceDetail:
    with get_db() as db:
        row = db.execute(
            """
            SELECT id, title, resource_type, locale, tags, version, content, updated_at
            FROM hr_resources
            WHERE id = ?
            """,
            (resource_id,),
        ).fetchone()

    if row is None:
        write_audit_log(role, "read_hr_resource_detail", "rejected", resource_id, "not found")
        raise HTTPException(status_code=404, detail="hr resource not found")

    updated_at = parse_datetime_or_none(row["updated_at"]) or datetime.now(timezone.utc)
    tags = [tag.strip() for tag in row["tags"].split(",") if tag.strip()]

    write_audit_log(role, "read_hr_resource_detail", "success", resource_id, f"version={row['version']}")

    return HrResourceDetail(
        id=row["id"],
        title=row["title"],
        resource_type=row["resource_type"],
        locale=row["locale"],
        tags=tags,
        version=row["version"],
        updated_at=updated_at,
        content=row["content"],
    )


@app.get("/api/v1/executive/ask", response_model=ExecutiveAskResponse)
def ask_executive_metrics(
    question: str = Query(..., min_length=5),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    role: str = Depends(require_roles({"executive", "admin"})),
) -> ExecutiveAskResponse:
    now = datetime.now(timezone.utc)
    normalized = question.strip().lower()

    with get_db() as db:
        if "vendimos" in normalized and ("florida" in normalized or "colombia" in normalized or "vs" in normalized):
            start_at = period_start("week")
            end_at = now
            rows = db.execute(
                """
                SELECT st.country, se.total_amount, se.currency
                FROM sales_events se
                JOIN stores st ON st.id = se.store_id
                WHERE se.sold_at >= ? AND se.sold_at < ?
                """,
                (start_at.isoformat(), end_at.isoformat()),
            ).fetchall()
            totals_by_country: dict[str, float] = {"CO": 0.0, "US": 0.0}
            for row in rows:
                totals_by_country[row["country"]] += convert_amount(row["total_amount"], row["currency"], currency)

            answer = (
                f"Semana actual: Colombia={totals_by_country['CO']:.2f} {currency}, "
                f"Florida={totals_by_country['US']:.2f} {currency}."
            )
            write_audit_log(
                role,
                "executive_ask",
                "success",
                "sales_week_country_compare",
                f"currency={currency}",
            )
            return ExecutiveAskResponse(
                question=question,
                answer=answer,
                sources=["sales_events", "stores", "rule:sales_week_country_compare"],
                requires_follow_up=False,
                follow_up_questions=[],
                generated_at=now,
            )

        if "ticket" in normalized and "alto" in normalized and ("mes" in normalized or "month" in normalized):
            start_at = period_start("month")
            end_at = now
            rows = db.execute(
                """
                SELECT st.id, st.name, st.country, se.total_amount, se.currency
                FROM sales_events se
                JOIN stores st ON st.id = se.store_id
                WHERE se.sold_at >= ? AND se.sold_at < ?
                ORDER BY st.id
                """,
                (start_at.isoformat(), end_at.isoformat()),
            ).fetchall()
            grouped: dict[str, dict[str, float | int | str]] = {}
            for row in rows:
                store_id = row["id"]
                if store_id not in grouped:
                    grouped[store_id] = {
                        "store_name": row["name"],
                        "market": "Colombia" if row["country"] == "CO" else "Florida",
                        "tickets": 0,
                        "total": 0.0,
                    }
                grouped[store_id]["tickets"] += 1
                grouped[store_id]["total"] += convert_amount(row["total_amount"], row["currency"], currency)

            best_store_name = "N/A"
            best_market = "N/A"
            best_avg = 0.0
            for item in grouped.values():
                tickets = int(item["tickets"])
                if tickets <= 0:
                    continue
                avg = float(item["total"]) / tickets
                if avg > best_avg:
                    best_avg = avg
                    best_store_name = str(item["store_name"])
                    best_market = str(item["market"])

            answer = (
                f"Local con mayor ticket promedio mensual: {best_store_name} "
                f"({best_market}) con {best_avg:.2f} {currency}."
            )
            write_audit_log(
                role,
                "executive_ask",
                "success",
                "top_monthly_average_ticket_store",
                f"currency={currency}",
            )
            return ExecutiveAskResponse(
                question=question,
                answer=answer,
                sources=["sales_events", "stores", "rule:top_monthly_average_ticket_store"],
                requires_follow_up=False,
                follow_up_questions=[],
                generated_at=now,
            )

        if "riesgo" in normalized and "inactividad" in normalized:
            stores_rows = db.execute("SELECT id FROM stores").fetchall()
            total_stores = len(stores_rows)
            rows = db.execute(
                """
                SELECT st.id, MAX(se.sold_at) AS last_sale_at
                FROM stores st
                LEFT JOIN sales_events se ON se.store_id = st.id
                GROUP BY st.id
                """
            ).fetchall()
            critical_count = 0
            for row in rows:
                if row["last_sale_at"] is None:
                    critical_count += 1
                    continue
                last_sale = datetime.fromisoformat(row["last_sale_at"])
                if last_sale.tzinfo is None:
                    last_sale = last_sale.replace(tzinfo=timezone.utc)
                minutes_without_sales = int((now - last_sale).total_seconds() // 60)
                if minutes_without_sales > 120:
                    critical_count += 1

            critical_ratio_pct = round((critical_count / total_stores) * 100, 2) if total_stores > 0 else 0.0
            if critical_ratio_pct >= 50:
                risk_level = "high"
            elif critical_ratio_pct >= 20:
                risk_level = "medium"
            else:
                risk_level = "low"

            answer = (
                f"Riesgo actual de inactividad: {risk_level.upper()} "
                f"({critical_count}/{total_stores} locales en estado critico, {critical_ratio_pct:.2f}%)."
            )
            write_audit_log(
                role,
                "executive_ask",
                "success",
                "inactivity_risk_snapshot",
                "window_minutes=120",
            )
            return ExecutiveAskResponse(
                question=question,
                answer=answer,
                sources=["stores", "sales_events", "rule:inactivity_risk_snapshot"],
                requires_follow_up=False,
                follow_up_questions=[],
                generated_at=now,
            )

    write_audit_log(
        role,
        "executive_ask",
        "insufficient_data",
        "unsupported_question",
        normalized[:200],
    )
    return ExecutiveAskResponse(
        question=question,
        answer="informacion insuficiente para responder con trazabilidad. Formula una pregunta de ventas por pais, ticket promedio mensual o riesgo de inactividad.",
        sources=["rule:unsupported_question"],
        requires_follow_up=True,
        follow_up_questions=[
            "Cuanto vendimos esta semana en Florida vs Colombia?",
            "Que local tiene el ticket promedio mas alto del mes?",
            "Cual es el riesgo actual de inactividad?",
        ],
        generated_at=now,
    )


@app.get("/api/v1/executive/weekly-report", response_model=WeeklyExecutiveReportResponse)
def get_executive_weekly_report(
    currency: Literal["COP", "USD"] = Query(default="USD"),
    role: str = Depends(require_roles({"executive", "admin"})),
) -> WeeklyExecutiveReportResponse:
    summary = get_sales_summary(period="week", currency=currency, country=None, start_date=None, end_date=None)
    markets = get_market_summary(currency=currency, start_date=None, end_date=None, country=None)
    inactivity = get_inactivity_alerts(
        window_minutes=60,
        country=None,
        severity_filter=None,
        limit=20,
        role=role,
    )
    alerts_sla = get_inactivity_alerts_sla(days=7, sla_target_minutes=30, country=None, role=role)

    write_audit_log(
        role,
        "read_executive_weekly_report",
        "success",
        "weekly_report",
        f"currency={currency}, alerts={inactivity.total_alerts}",
    )

    return WeeklyExecutiveReportResponse(
        currency=currency,
        generated_at=datetime.now(timezone.utc),
        summary=summary,
        markets=markets,
        inactivity=inactivity,
        alerts_sla=alerts_sla,
    )
