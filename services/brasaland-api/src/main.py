from datetime import datetime, timedelta, timezone
import asyncio
import csv
import io
import os
from pathlib import Path
from sqlite3 import Connection, Row, connect
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi import WebSocket, WebSocketDisconnect
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


class MenuItem(BaseModel):
    id: str
    store_id: str | None
    country: Literal["CO", "US"]
    market: str
    sku: str
    name: str
    description: str
    category: Literal["main", "combo", "side", "drink", "dessert"]
    price_amount: float
    currency: Literal["COP", "USD"]
    locale: Literal["es", "en"]
    is_active: bool
    updated_at: datetime


class MenuItemCreate(BaseModel):
    id: str
    store_id: str | None = None
    country: Literal["CO", "US"]
    sku: str
    name: str
    description: str = ""
    category: Literal["main", "combo", "side", "drink", "dessert"]
    price_amount: float
    currency: Literal["COP", "USD"]
    locale: Literal["es", "en"] = "es"
    is_active: bool = True


class StoreTelemetryEventCreate(BaseModel):
    store_id: str
    source_system: Literal["pos", "kds", "network", "iot-gateway"]
    event_ts: datetime
    pos_online: bool
    sales_last_5m: int
    open_tickets: int
    avg_prep_seconds: float
    network_rtt_ms: float
    terminal_version: str | None = None


class StoreTelemetryEventCreated(BaseModel):
    id: int
    store_id: str
    source_system: str
    event_ts: datetime
    ingested_at: datetime
    latency_seconds: float


class StoreTelemetryStatusRow(BaseModel):
    store_id: str
    store_name: str
    country: Literal["CO", "US"]
    market: str
    last_event_at: datetime | None
    minutes_since_last_event: float | None
    freshness: Literal["online", "stale", "offline"]
    source_system: str | None
    pos_online: bool | None
    sales_last_5m: int | None
    open_tickets: int | None
    avg_prep_seconds: float | None
    network_rtt_ms: float | None
    terminal_version: str | None


class StoreTelemetryStatusResponse(BaseModel):
    window_minutes: int
    generated_at: datetime
    total_stores: int
    online_stores: int
    stale_stores: int
    offline_stores: int
    rows: list[StoreTelemetryStatusRow]


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


class RecipeCatalogSearchResponse(BaseModel):
    q: str
    locale: Literal["es", "en"] | None
    total_results: int
    resources: list[TrainingResourceSummary]


class OnboardingItinerarySummary(BaseModel):
    id: str
    title: str
    role_target: str
    locale: Literal["es", "en"]
    version: str
    steps_count: int
    updated_at: datetime


class OnboardingItineraryDetail(OnboardingItinerarySummary):
    steps: list[str]


class OnboardingAssignmentCreate(BaseModel):
    employee_id: str
    itinerary_id: str
    mentor_name: str
    start_date: str | None = None


class RecipeUpdatePublishCreate(BaseModel):
    resource_id: str
    change_summary: str
    locale: Literal["es", "en"] | None = None
    mandatory: bool = True


class RecipeUpdateDistributionSummary(BaseModel):
    update_id: int
    resource_id: str
    resource_title: str
    version: str
    locale: Literal["es", "en"]
    change_summary: str
    mandatory: bool
    published_at: datetime
    delivered_stores: int
    acknowledged_stores: int
    pending_stores: int


class RecipeUpdateDeliveryRow(BaseModel):
    id: int
    update_id: int
    store_id: str
    store_name: str
    country: Literal["CO", "US"]
    market: str
    delivered_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by_role: str | None
    status: Literal["delivered", "acknowledged"]


class RecipeUpdateAcknowledgeCreate(BaseModel):
    store_id: str


class RecipeUpdatePublishResult(BaseModel):
    update: RecipeUpdateDistributionSummary
    deliveries: list[RecipeUpdateDeliveryRow]


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


class SupplierPriceRow(BaseModel):
    supplier_id: str
    supplier_name: str
    sku: str
    item_name: str
    country: Literal["CO", "US"]
    currency: Literal["COP", "USD"]
    price: float
    valid_from: datetime


class SupplierPriceAlert(BaseModel):
    supplier_id: str
    supplier_name: str
    sku: str
    item_name: str
    country: Literal["CO", "US"]
    currency: Literal["COP", "USD"]
    previous_price: float
    current_price: float
    change_pct: float
    valid_from: datetime


class CustomerSummary(BaseModel):
    country: Literal["CO", "US"]
    total_customers: int
    active_customers_30d: int
    average_points: float


class CustomerProfile(BaseModel):
    id: str
    full_name: str
    country: Literal["CO", "US"]
    segment: Literal["new", "recurring", "vip"]
    points_balance: int
    last_order_at: datetime | None


class CustomerPointsAdjustmentCreate(BaseModel):
    delta_points: int
    reason: str


class CustomerPointsAdjustmentResult(BaseModel):
    customer_id: str
    previous_points: int
    current_points: int
    delta_points: int
    reason: str
    updated_at: datetime


class MarketingOrderCreate(BaseModel):
    customer_id: str
    store_id: str
    order_items: list[str]
    total_amount: float
    currency: Literal["COP", "USD"]
    channel: Literal["app", "web"] = "app"


class MarketingOrderResult(BaseModel):
    order_id: int
    customer_id: str
    store_id: str
    channel: Literal["app", "web"]
    order_items: list[str]
    total_amount: float
    currency: Literal["COP", "USD"]
    awarded_points: int
    current_points_balance: int
    ordered_at: datetime


class CrmOverview(BaseModel):
    period_days: int
    country: Literal["CO", "US"] | None
    total_customers: int
    active_customers: int
    total_orders: int
    total_revenue: float
    currency: Literal["COP", "USD"]
    generated_at: datetime


class CrmCustomerRow(BaseModel):
    customer_id: str
    full_name: str
    country: Literal["CO", "US"]
    segment: Literal["new", "recurring", "vip"]
    points_balance: int
    orders_count: int
    total_spend: float
    favorite_item: str | None
    last_order_at: datetime | None


class CustomerOrderHistoryRow(BaseModel):
    id: int
    customer_id: str
    store_id: str
    ordered_at: datetime
    total_amount: float
    currency: Literal["COP", "USD"]
    channel: Literal["app", "web"]
    order_items: list[str]


class PersonalizedProductRecommendation(BaseModel):
    product_id: str
    name: str
    reason: str
    score: float
    expected_price: float
    currency: Literal["COP", "USD"]


class PersonalizationResponse(BaseModel):
    customer_id: str
    currency: Literal["COP", "USD"]
    generated_at: datetime
    recommendations: list[PersonalizedProductRecommendation]


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


class InventoryStockRow(BaseModel):
    store_id: str
    store_name: str
    country: Literal["CO", "US"]
    market: str
    sku: str
    item_name: str
    category: str
    unit: str
    current_stock: float
    min_stock: float
    last_updated: datetime


class SmartOrderRecommendationRow(BaseModel):
    store_id: str
    store_name: str
    country: Literal["CO", "US"]
    market: str
    sku: str
    item_name: str
    category: str
    unit: str
    current_stock: float
    min_stock: float
    expected_daily_usage: float
    projected_days_of_cover: float
    target_days_of_cover: int
    recommended_order_qty: float
    estimated_unit_cost: float | None
    estimated_order_cost: float | None
    currency: Literal["COP", "USD"]
    risk_level: Literal["ok", "warning", "critical"]


class SmartOrderRecommendationResponse(BaseModel):
    country: Literal["CO", "US"] | None
    currency: Literal["COP", "USD"]
    days_history: int
    target_days_of_cover: int
    generated_at: datetime
    recommendations: list[SmartOrderRecommendationRow]


class InventoryReceiptCreate(BaseModel):
    store_id: str
    sku: str
    received_qty: float
    unit_cost: float | None = None
    currency: Literal["COP", "USD"] = "USD"
    note: str | None = None


class InventoryReceiptResult(BaseModel):
    receipt_id: int
    store_id: str
    sku: str
    previous_stock: float
    current_stock: float
    received_qty: float
    estimated_receipt_cost: float | None
    currency: Literal["COP", "USD"]
    recommendation_status: Literal["open", "closed"]
    recommendation_after: SmartOrderRecommendationRow
    updated_at: datetime


class InventoryReceiptRow(BaseModel):
    id: int
    store_id: str
    store_name: str
    country: Literal["CO", "US"]
    market: str
    sku: str
    received_qty: float
    unit_cost: float | None
    currency: Literal["COP", "USD"]
    note: str | None
    received_at: datetime
    received_by_role: str


class SupplierPurchasesCountrySummary(BaseModel):
    country: Literal["CO", "US"]
    market: str
    receipts_count: int
    suppliers_count: int
    total_spend: float
    currency: Literal["COP", "USD"]


class SupplierPurchasesSupplierSummary(BaseModel):
    supplier_id: str
    supplier_name: str
    country: Literal["CO", "US"]
    market: str
    receipts_count: int
    total_qty: float
    total_spend: float
    average_unit_cost: float
    currency: Literal["COP", "USD"]


class SupplierPurchasesConsolidatedResponse(BaseModel):
    period_days: int
    currency: Literal["COP", "USD"]
    generated_at: datetime
    total_receipts: int
    total_suppliers: int
    total_spend: float
    by_country: list[SupplierPurchasesCountrySummary]
    by_supplier: list[SupplierPurchasesSupplierSummary]


class HrEmployeeSummary(BaseModel):
    id: str
    full_name: str
    country: Literal["CO", "US"]
    store_id: str
    role_title: str
    employment_status: Literal["active", "terminated"]
    hire_date: datetime
    terminated_at: datetime | None


class HrTimeOffRequestCreate(BaseModel):
    employee_id: str
    request_type: Literal["vacation", "sick_leave", "personal_leave"]
    start_date: str
    end_date: str
    reason: str


class HrTimeOffRequestActionCreate(BaseModel):
    status: Literal["approved", "rejected"]
    note: str | None = None


class HrTimeOffRequestRow(BaseModel):
    id: int
    employee_id: str
    employee_name: str
    store_id: str
    country: Literal["CO", "US"]
    market: str
    request_type: Literal["vacation", "sick_leave", "personal_leave"]
    start_date: datetime
    end_date: datetime
    total_days: int
    reason: str
    status: Literal["pending", "approved", "rejected"]
    created_at: datetime
    decided_at: datetime | None
    decided_by_role: str | None
    decision_note: str | None


class HrOnboardingCaseCreate(BaseModel):
    employee_id: str
    position_title: str
    mentor_name: str
    start_date: str | None = None
    notes: str | None = None


class HrOnboardingAdvanceCreate(BaseModel):
    step_key: Literal["documents", "orientation", "station_training", "supervised_shift"]
    note: str | None = None


class HrOnboardingCaseRow(BaseModel):
    id: int
    employee_id: str
    employee_name: str
    store_id: str
    country: Literal["CO", "US"]
    market: str
    position_title: str
    mentor_name: str
    status: Literal["active", "completed", "on_hold"]
    completed_steps: int
    total_steps: int
    last_step_key: str | None
    started_at: datetime
    target_completion_at: datetime
    last_updated_at: datetime
    notes: str | None


class HrKpiCountrySummary(BaseModel):
    country: Literal["CO", "US"]
    market: str
    active_headcount: int
    total_headcount: int
    terminations: int
    turnover_rate_pct: float
    absent_days: float
    absenteeism_rate_pct: float
    open_vacancies: int
    avg_time_to_fill_days: float
    pending_time_off_requests: int
    active_onboarding_cases: int


class HrKpiOverviewResponse(BaseModel):
    period_days: int
    country: Literal["CO", "US"] | None
    generated_at: datetime
    total_active_headcount: int
    total_terminations: int
    overall_turnover_rate_pct: float
    overall_absenteeism_rate_pct: float
    overall_avg_time_to_fill_days: float
    by_country: list[HrKpiCountrySummary]


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
SKU_CONSUMPTION_PER_TICKET: dict[str, float] = {
    "CHICKEN": 0.22,
    "POTATO": 0.18,
}
SKU_LOCALIZED_NAMES: dict[str, dict[str, str]] = {
    "CHICKEN": {"CO": "Pollo entero", "US": "Whole chicken"},
    "POTATO": {"CO": "Papa criolla", "US": "Potato"},
}
SUPPLIER_SKU_BY_COUNTRY: dict[str, dict[str, str]] = {
    "CO": {"CHICKEN": "SKU-POLLO", "POTATO": "SKU-PAPA"},
    "US": {"CHICKEN": "SKU-CHICKEN", "POTATO": "SKU-POTATO"},
}
STORE_OPENING_HOURS: dict[str, tuple[int, int]] = {
    "med-001": (10, 22),
    "med-002": (10, 22),
    "med-003": (10, 22),
    "med-004": (10, 22),
    "med-005": (10, 22),
    "bog-001": (10, 22),
    "bog-002": (10, 22),
    "cal-001": (10, 22),
    "mia-001": (10, 22),
    "mia-002": (10, 22),
    "mia-003": (10, 22),
    "mia-004": (10, 22),
    "orl-001": (10, 22),
    "orl-002": (10, 22),
}

PERSONALIZATION_CATALOG: list[dict[str, str | float | list[str]]] = [
    {
        "product_id": "prd-family-brasa",
        "name": "Combo Familiar Brasa",
        "tags": ["familiar", "pollo", "compartir"],
        "base_price_usd": 29.9,
    },
    {
        "product_id": "prd-pollo-clasico",
        "name": "Pollo Clasico Entero",
        "tags": ["pollo", "clasico", "proteina"],
        "base_price_usd": 14.5,
    },
    {
        "product_id": "prd-alitas-picantes",
        "name": "Alitas Picantes",
        "tags": ["picante", "sharing", "snack"],
        "base_price_usd": 9.9,
    },
    {
        "product_id": "prd-bowl-fit",
        "name": "Bowl Fit de Pollo",
        "tags": ["fit", "ligero", "saludable"],
        "base_price_usd": 12.9,
    },
    {
        "product_id": "prd-kids-brasa",
        "name": "Kids Brasa Meal",
        "tags": ["kids", "familiar", "combo"],
        "base_price_usd": 8.4,
    },
]


def is_store_open_at(local_time: datetime, opening_hour: int, closing_hour: int) -> bool:
    current_minutes = local_time.hour * 60 + local_time.minute
    opening_minutes = opening_hour * 60
    closing_minutes = closing_hour * 60

    if opening_minutes < closing_minutes:
        return opening_minutes <= current_minutes < closing_minutes

    # Supports overnight schedules, e.g., 18:00 to 02:00.
    return current_minutes >= opening_minutes or current_minutes < closing_minutes


def market_label(country: str) -> str:
    return "Colombia" if country == "CO" else "Florida"


def build_smart_order_recommendation_row(
    *,
    store_id: str,
    store_name: str,
    country_code: str,
    sku: str,
    item_name: str,
    category: str,
    unit: str,
    current_stock: float,
    min_stock: float,
    tickets: int,
    days_history: int,
    target_days: int,
    currency: Literal["COP", "USD"],
    latest_price_by_country_sku: dict[tuple[str, str], tuple[str, float]],
) -> SmartOrderRecommendationRow:
    normalized_sku = sku.upper()
    expected_daily_tickets = tickets / days_history if days_history > 0 else 0.0

    base_usage = SKU_CONSUMPTION_PER_TICKET.get(normalized_sku, 0.06)
    expected_daily_usage = max(expected_daily_tickets * base_usage, 0.01)
    projected_days_of_cover = current_stock / expected_daily_usage if expected_daily_usage > 0 else 0.0

    target_stock_qty = max(target_days * expected_daily_usage, min_stock)
    recommended_order_qty = max(0.0, target_stock_qty - current_stock)

    if projected_days_of_cover < 2:
        risk_level: Literal["ok", "warning", "critical"] = "critical"
    elif projected_days_of_cover < 4:
        risk_level = "warning"
    else:
        risk_level = "ok"

    supplier_sku = SUPPLIER_SKU_BY_COUNTRY.get(country_code, {}).get(normalized_sku)
    estimated_unit_cost: float | None = None
    estimated_order_cost: float | None = None
    if supplier_sku is not None:
        price_pair = latest_price_by_country_sku.get((country_code, supplier_sku))
        if price_pair is not None:
            source_currency, source_price = price_pair
            converted_unit = convert_amount(source_price, source_currency, currency)
            estimated_unit_cost = round(converted_unit, 4)
            estimated_order_cost = round(converted_unit * recommended_order_qty, 2)

    localized_item_name = SKU_LOCALIZED_NAMES.get(normalized_sku, {}).get(country_code, item_name)

    return SmartOrderRecommendationRow(
        store_id=store_id,
        store_name=store_name,
        country=country_code,
        market=market_label(country_code),
        sku=normalized_sku,
        item_name=localized_item_name,
        category=category,
        unit=unit,
        current_stock=round(current_stock, 3),
        min_stock=round(min_stock, 3),
        expected_daily_usage=round(expected_daily_usage, 3),
        projected_days_of_cover=round(projected_days_of_cover, 2),
        target_days_of_cover=target_days,
        recommended_order_qty=round(recommended_order_qty, 3),
        estimated_unit_cost=estimated_unit_cost,
        estimated_order_cost=estimated_order_cost,
        currency=currency,
        risk_level=risk_level,
    )


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


def validate_role_token_for_ws(role: str | None, token: str | None, allowed_roles: set[str]) -> str:
    if role is None or role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Role not allowed")

    role_tokens = resolve_role_tokens()
    expected_token = role_tokens.get(role)
    if expected_token is None or token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid role token")

    return role


def build_realtime_digest() -> dict[str, int]:
    with get_db() as db:
        sales_max = db.execute("SELECT COALESCE(MAX(id), 0) AS v FROM sales_events").fetchone()["v"]
        telemetry_max = db.execute("SELECT COALESCE(MAX(id), 0) AS v FROM store_telemetry_events").fetchone()["v"]
        alerts_actions_max = db.execute("SELECT COALESCE(MAX(id), 0) AS v FROM inactivity_alert_actions").fetchone()["v"]
        receipts_max = db.execute("SELECT COALESCE(MAX(id), 0) AS v FROM inventory_receipts").fetchone()["v"]

    return {
        "sales_events_max_id": int(sales_max),
        "telemetry_events_max_id": int(telemetry_max),
        "alert_actions_max_id": int(alerts_actions_max),
        "inventory_receipts_max_id": int(receipts_max),
    }


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


def parse_iso_date(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must use YYYY-MM-DD") from exc
    return parsed.replace(tzinfo=timezone.utc)


def calculate_requested_days(start_date: datetime, end_date: datetime) -> int:
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be equal or greater than start_date")
    return int((end_date - start_date).days) + 1


def init_db() -> None:
    stores = [
        ("med-001", "Brasaland Laureles", "CO", "Medellin", "America/Bogota", "COP"),
        ("med-002", "Brasaland El Poblado", "CO", "Medellin", "America/Bogota", "COP"),
        ("med-003", "Brasaland Envigado", "CO", "Medellin", "America/Bogota", "COP"),
        ("med-004", "Brasaland Belen", "CO", "Medellin", "America/Bogota", "COP"),
        ("med-005", "Brasaland Centro", "CO", "Medellin", "America/Bogota", "COP"),
        ("bog-001", "Brasaland Zona T", "CO", "Bogota", "America/Bogota", "COP"),
        ("bog-002", "Brasaland Usaquen", "CO", "Bogota", "America/Bogota", "COP"),
        ("cal-001", "Brasaland Granada", "CO", "Cali", "America/Bogota", "COP"),
        ("mia-001", "Brasaland Doral", "US", "Miami", "America/New_York", "USD"),
        ("mia-002", "Brasaland Kendall", "US", "Miami", "America/New_York", "USD"),
        ("mia-003", "Brasaland Brickell", "US", "Miami", "America/New_York", "USD"),
        ("mia-004", "Brasaland Hialeah", "US", "Miami", "America/New_York", "USD"),
        ("orl-001", "Brasaland Lake Nona", "US", "Orlando", "America/New_York", "USD"),
        ("orl-002", "Brasaland Winter Park", "US", "Orlando", "America/New_York", "USD"),
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
            CREATE TABLE IF NOT EXISTS menu_items (
                id TEXT PRIMARY KEY,
                store_id TEXT,
                country TEXT NOT NULL,
                sku TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                price_amount REAL NOT NULL,
                currency TEXT NOT NULL,
                locale TEXT NOT NULL,
                is_active INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(country, store_id, sku, locale),
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS store_telemetry_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT NOT NULL,
                source_system TEXT NOT NULL,
                event_ts TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                latency_seconds REAL NOT NULL,
                pos_online INTEGER NOT NULL,
                sales_last_5m INTEGER NOT NULL,
                open_tickets INTEGER NOT NULL,
                avg_prep_seconds REAL NOT NULL,
                network_rtt_ms REAL NOT NULL,
                terminal_version TEXT,
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
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS training_onboarding_itineraries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                role_target TEXT NOT NULL,
                locale TEXT NOT NULL,
                version TEXT NOT NULL,
                steps TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS training_recipe_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id TEXT NOT NULL,
                resource_title TEXT NOT NULL,
                version TEXT NOT NULL,
                locale TEXT NOT NULL,
                change_summary TEXT NOT NULL,
                mandatory INTEGER NOT NULL,
                published_at TEXT NOT NULL,
                published_by_role TEXT NOT NULL,
                FOREIGN KEY(resource_id) REFERENCES training_resources(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS training_recipe_update_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                update_id INTEGER NOT NULL,
                store_id TEXT NOT NULL,
                delivered_at TEXT NOT NULL,
                acknowledged_at TEXT,
                acknowledged_by_role TEXT,
                status TEXT NOT NULL,
                UNIQUE(update_id, store_id),
                FOREIGN KEY(update_id) REFERENCES training_recipe_updates(id),
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS supplier_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                sku TEXT NOT NULL,
                item_name TEXT NOT NULL,
                country TEXT NOT NULL,
                currency TEXT NOT NULL,
                price REAL NOT NULL,
                valid_from TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                country TEXT NOT NULL,
                segment TEXT NOT NULL,
                points_balance INTEGER NOT NULL,
                last_order_at TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS loyalty_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                delta_points INTEGER NOT NULL,
                reason TEXT NOT NULL,
                happened_at TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS digital_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                store_id TEXT NOT NULL,
                ordered_at TEXT NOT NULL,
                total_amount REAL NOT NULL,
                currency TEXT NOT NULL,
                channel TEXT NOT NULL,
                order_items TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id),
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(customer_id, preference_key),
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                unit TEXT NOT NULL,
                current_stock REAL NOT NULL,
                min_stock REAL NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(store_id, sku),
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                received_qty REAL NOT NULL,
                unit_cost REAL,
                currency TEXT NOT NULL,
                note TEXT,
                received_at TEXT NOT NULL,
                received_by_role TEXT NOT NULL,
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_employees (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                country TEXT NOT NULL,
                store_id TEXT NOT NULL,
                role_title TEXT NOT NULL,
                employment_status TEXT NOT NULL,
                hire_date TEXT NOT NULL,
                terminated_at TEXT,
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_time_off_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                store_id TEXT NOT NULL,
                country TEXT NOT NULL,
                request_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                total_days INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                decided_at TEXT,
                decided_by_role TEXT,
                decision_note TEXT,
                FOREIGN KEY(employee_id) REFERENCES hr_employees(id),
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_absence_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                country TEXT NOT NULL,
                absence_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                total_days REAL NOT NULL,
                source_request_id INTEGER,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY(employee_id) REFERENCES hr_employees(id),
                FOREIGN KEY(source_request_id) REFERENCES hr_time_off_requests(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_onboarding_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                store_id TEXT NOT NULL,
                country TEXT NOT NULL,
                position_title TEXT NOT NULL,
                mentor_name TEXT NOT NULL,
                status TEXT NOT NULL,
                completed_steps INTEGER NOT NULL,
                total_steps INTEGER NOT NULL,
                last_step_key TEXT,
                started_at TEXT NOT NULL,
                target_completion_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY(employee_id) REFERENCES hr_employees(id),
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS hr_vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT NOT NULL,
                country TEXT NOT NULL,
                role_title TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                filled_at TEXT,
                status TEXT NOT NULL,
                FOREIGN KEY(store_id) REFERENCES stores(id)
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

        existing_menu = db.execute("SELECT COUNT(*) AS c FROM menu_items").fetchone()["c"]
        if existing_menu == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            menu_seed = [
                (
                    "menu-co-main-001",
                    None,
                    "CO",
                    "SKU-POLLO-CLASICO",
                    "Pollo clasico entero",
                    "Receta estandar brasaland para pollo entero.",
                    "main",
                    48900.0,
                    "COP",
                    "es",
                    1,
                    now_iso,
                ),
                (
                    "menu-co-combo-001",
                    None,
                    "CO",
                    "SKU-COMBO-FAM",
                    "Combo familiar",
                    "Pollo + acompañamientos para 4 personas.",
                    "combo",
                    89900.0,
                    "COP",
                    "es",
                    1,
                    now_iso,
                ),
                (
                    "menu-us-main-001",
                    None,
                    "US",
                    "SKU-CHICKEN-CLASSIC",
                    "Classic whole chicken",
                    "Brasaland standard whole chicken recipe.",
                    "main",
                    15.9,
                    "USD",
                    "en",
                    1,
                    now_iso,
                ),
                (
                    "menu-us-combo-001",
                    None,
                    "US",
                    "SKU-FAMILY-COMBO",
                    "Family combo",
                    "Chicken + sides for 4 guests.",
                    "combo",
                    29.9,
                    "USD",
                    "en",
                    1,
                    now_iso,
                ),
            ]
            db.executemany(
                """
                INSERT INTO menu_items (
                    id, store_id, country, sku, name, description, category,
                    price_amount, currency, locale, is_active, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                menu_seed,
            )

        existing_telemetry = db.execute("SELECT COUNT(*) AS c FROM store_telemetry_events").fetchone()["c"]
        if existing_telemetry == 0:
            now = datetime.now(timezone.utc)
            telemetry_seed = []
            for index, store in enumerate(stores):
                store_id = store[0]
                event_ts = (now - timedelta(minutes=(index % 4) * 2)).isoformat()
                ingested_at = now.isoformat()
                telemetry_seed.append(
                    (
                        store_id,
                        "pos",
                        event_ts,
                        ingested_at,
                        max((now - datetime.fromisoformat(event_ts)).total_seconds(), 0.0),
                        1,
                        2 + (index % 5),
                        1 + (index % 3),
                        420.0 + (index * 8.0),
                        25.0 + (index % 7) * 4.0,
                        "pos-v2.1",
                    )
                )
            db.executemany(
                """
                INSERT INTO store_telemetry_events (
                    store_id, source_system, event_ts, ingested_at, latency_seconds,
                    pos_online, sales_last_5m, open_tickets, avg_prep_seconds,
                    network_rtt_ms, terminal_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                telemetry_seed,
            )

        # Backfill events per store if a store has no historical sales yet.
        now = datetime.now(timezone.utc)
        missing_store_events: list[tuple[str, str, float, str]] = []
        for index, store in enumerate(stores):
            store_id, _, country_code, _, _, base_currency = store
            store_events_count = db.execute(
                "SELECT COUNT(*) AS c FROM sales_events WHERE store_id = ?",
                (store_id,),
            ).fetchone()["c"]
            if store_events_count > 0:
                continue

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

                    if country_code == "CO":
                        base_amount = 64000.0 + (index * 1200)
                        amount = base_amount + (day_delta * 210)
                    else:
                        base_amount = 17.5 + (index * 0.45)
                        amount = base_amount + (day_delta * 0.11)

                    missing_store_events.append((store_id, sold_at.isoformat(), amount, base_currency))

        if missing_store_events:
            db.executemany(
                """
                INSERT INTO sales_events (store_id, sold_at, total_amount, currency)
                VALUES (?, ?, ?, ?)
                """,
                missing_store_events,
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

        existing_itineraries = db.execute("SELECT COUNT(*) AS c FROM training_onboarding_itineraries").fetchone()["c"]
        if existing_itineraries == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            itineraries_seed = [
                (
                    "itn-kitchen-core-es-v1",
                    "Itinerario cocina base - 7 dias",
                    "Kitchen Operator",
                    "es",
                    "v1.0",
                    "Induccion de marca y cultura|Inocuidad y BPM|Estacion de mise en place|Tecnicas de coccion estandar|Presentacion y emplatado|Servicio en turno supervisado|Evaluacion final",
                    now_iso,
                    1,
                ),
                (
                    "itn-kitchen-core-en-v1",
                    "Core kitchen itinerary - 7 days",
                    "Kitchen Operator",
                    "en",
                    "v1.0",
                    "Brand and culture induction|Food safety and hygiene|Mise en place station|Standard cooking techniques|Presentation and plating standards|Supervised shift service|Final evaluation",
                    now_iso,
                    1,
                ),
            ]
            db.executemany(
                """
                INSERT INTO training_onboarding_itineraries (
                    id, title, role_target, locale, version, steps, updated_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                itineraries_seed,
            )

        existing_recipe_updates = db.execute("SELECT COUNT(*) AS c FROM training_recipe_updates").fetchone()["c"]
        if existing_recipe_updates == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            seed_resource = db.execute(
                """
                SELECT id, title, version, locale
                FROM training_resources
                WHERE category = 'recipe'
                ORDER BY updated_at DESC, id ASC
                LIMIT 1
                """
            ).fetchone()
            if seed_resource is not None:
                cursor = db.execute(
                    """
                    INSERT INTO training_recipe_updates (
                        resource_id, resource_title, version, locale, change_summary, mandatory, published_at, published_by_role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        seed_resource["id"],
                        seed_resource["title"],
                        seed_resource["version"],
                        seed_resource["locale"],
                        "Actualizacion base de tiempos de coccion y control visual de terminado",
                        1,
                        now_iso,
                        "admin",
                    ),
                )
                update_id = int(cursor.lastrowid)
                deliveries_seed = [
                    (update_id, store[0], now_iso, None, None, "delivered")
                    for store in stores
                ]
                db.executemany(
                    """
                    INSERT INTO training_recipe_update_deliveries (
                        update_id, store_id, delivered_at, acknowledged_at, acknowledged_by_role, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    deliveries_seed,
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

        existing_supplier_prices = db.execute("SELECT COUNT(*) AS c FROM supplier_prices").fetchone()["c"]
        if existing_supplier_prices == 0:
            now = datetime.now(timezone.utc)
            supplier_seed = [
                ("sup-co-001", "Avicola Andina", "SKU-POLLO", "Pollo entero", "CO", "COP", 12100.0, (now - timedelta(days=14)).isoformat()),
                ("sup-co-001", "Avicola Andina", "SKU-POLLO", "Pollo entero", "CO", "COP", 13400.0, (now - timedelta(days=2)).isoformat()),
                ("sup-co-002", "Hortalizas Antioquia", "SKU-PAPA", "Papa criolla", "CO", "COP", 3100.0, (now - timedelta(days=10)).isoformat()),
                ("sup-co-002", "Hortalizas Antioquia", "SKU-PAPA", "Papa criolla", "CO", "COP", 3190.0, (now - timedelta(days=1)).isoformat()),
                ("sup-us-001", "Florida Poultry LLC", "SKU-CHICKEN", "Whole chicken", "US", "USD", 3.15, (now - timedelta(days=12)).isoformat()),
                ("sup-us-001", "Florida Poultry LLC", "SKU-CHICKEN", "Whole chicken", "US", "USD", 3.55, (now - timedelta(days=1)).isoformat()),
                ("sup-us-002", "Sun Produce Co", "SKU-POTATO", "Potato", "US", "USD", 1.42, (now - timedelta(days=11)).isoformat()),
                ("sup-us-002", "Sun Produce Co", "SKU-POTATO", "Potato", "US", "USD", 1.44, (now - timedelta(days=1)).isoformat()),
            ]
            db.executemany(
                """
                INSERT INTO supplier_prices (
                    supplier_id, supplier_name, sku, item_name, country, currency, price, valid_from
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                supplier_seed,
            )

        existing_customers = db.execute("SELECT COUNT(*) AS c FROM customers").fetchone()["c"]
        if existing_customers == 0:
            now = datetime.now(timezone.utc)
            customer_seed = [
                ("cus-co-001", "Ana Rios", "CO", "vip", 420, (now - timedelta(days=2)).isoformat()),
                ("cus-co-002", "Carlos Mejia", "CO", "recurring", 160, (now - timedelta(days=15)).isoformat()),
                ("cus-us-001", "Emily Carter", "US", "vip", 530, (now - timedelta(days=1)).isoformat()),
                ("cus-us-002", "James Miller", "US", "new", 40, (now - timedelta(days=35)).isoformat()),
            ]
            db.executemany(
                """
                INSERT INTO customers (id, full_name, country, segment, points_balance, last_order_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                customer_seed,
            )

        existing_loyalty = db.execute("SELECT COUNT(*) AS c FROM loyalty_events").fetchone()["c"]
        if existing_loyalty == 0:
            now = datetime.now(timezone.utc)
            loyalty_seed = [
                ("cus-co-001", 120, "welcome_bonus", (now - timedelta(days=50)).isoformat()),
                ("cus-co-001", 300, "purchase_accumulation", (now - timedelta(days=2)).isoformat()),
                ("cus-us-001", 200, "welcome_bonus", (now - timedelta(days=40)).isoformat()),
                ("cus-us-001", 330, "purchase_accumulation", (now - timedelta(days=1)).isoformat()),
            ]
            db.executemany(
                """
                INSERT INTO loyalty_events (customer_id, delta_points, reason, happened_at)
                VALUES (?, ?, ?, ?)
                """,
                loyalty_seed,
            )

        existing_digital_orders = db.execute("SELECT COUNT(*) AS c FROM digital_orders").fetchone()["c"]
        if existing_digital_orders == 0:
            now = datetime.now(timezone.utc)
            digital_orders_seed = [
                (
                    "cus-co-001",
                    "med-001",
                    (now - timedelta(days=8)).isoformat(),
                    86500.0,
                    "COP",
                    "app",
                    "pollo_clasico,papa_criolla,cola_350",
                ),
                (
                    "cus-co-001",
                    "bog-001",
                    (now - timedelta(days=2)).isoformat(),
                    123000.0,
                    "COP",
                    "app",
                    "combo_familiar,arepas,salsa_aji",
                ),
                (
                    "cus-co-002",
                    "med-002",
                    (now - timedelta(days=12)).isoformat(),
                    54200.0,
                    "COP",
                    "web",
                    "pollo_medio,ensalada,bebida_limon",
                ),
                (
                    "cus-us-001",
                    "mia-001",
                    (now - timedelta(days=6)).isoformat(),
                    33.2,
                    "USD",
                    "app",
                    "family_combo,wings_spicy,fries_large",
                ),
                (
                    "cus-us-001",
                    "mia-002",
                    (now - timedelta(days=1)).isoformat(),
                    19.8,
                    "USD",
                    "app",
                    "classic_chicken,bowl_fit,sparkling_water",
                ),
                (
                    "cus-us-002",
                    "orl-001",
                    (now - timedelta(days=4)).isoformat(),
                    11.7,
                    "USD",
                    "web",
                    "kids_meal,fries_small,juice_mango",
                ),
            ]
            db.executemany(
                """
                INSERT INTO digital_orders (
                    customer_id, store_id, ordered_at, total_amount, currency, channel, order_items
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                digital_orders_seed,
            )

        existing_preferences = db.execute("SELECT COUNT(*) AS c FROM customer_preferences").fetchone()["c"]
        if existing_preferences == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            preferences_seed = [
                ("cus-co-001", "taste", "clasico_familiar", now_iso),
                ("cus-co-001", "spice", "medio", now_iso),
                ("cus-us-001", "taste", "spicy_sharing", now_iso),
                ("cus-us-002", "taste", "kids_combo", now_iso),
            ]
            db.executemany(
                """
                INSERT INTO customer_preferences (customer_id, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                preferences_seed,
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        stock_seed: list[tuple[str, str, str, str, str, float, float, str]] = []
        for index, store in enumerate(stores):
            store_id, _, country_code, _, _, _ = store
            chicken_name = SKU_LOCALIZED_NAMES["CHICKEN"][country_code]
            potato_name = SKU_LOCALIZED_NAMES["POTATO"][country_code]

            chicken_stock = 34.0 + (index % 6) * 4.0
            chicken_min_stock = 24.0 + (index % 4) * 2.0
            potato_stock = 22.0 + (index % 5) * 3.0
            potato_min_stock = 16.0 + (index % 3) * 2.0

            stock_seed.extend(
                [
                    (
                        store_id,
                        "CHICKEN",
                        chicken_name,
                        "protein",
                        "kg",
                        chicken_stock,
                        chicken_min_stock,
                        now_iso,
                    ),
                    (
                        store_id,
                        "POTATO",
                        potato_name,
                        "produce",
                        "kg",
                        potato_stock,
                        potato_min_stock,
                        now_iso,
                    ),
                ]
            )

        db.executemany(
            """
            INSERT OR IGNORE INTO stock_levels (
                store_id, sku, item_name, category, unit, current_stock, min_stock, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            stock_seed,
        )

        now = datetime.now(timezone.utc)
        co_receipts_count = db.execute(
            """
            SELECT COUNT(*) AS c
            FROM inventory_receipts ir
            JOIN stores st ON st.id = ir.store_id
            WHERE st.country = 'CO'
            """
        ).fetchone()["c"]
        us_receipts_count = db.execute(
            """
            SELECT COUNT(*) AS c
            FROM inventory_receipts ir
            JOIN stores st ON st.id = ir.store_id
            WHERE st.country = 'US'
            """
        ).fetchone()["c"]

        receipts_seed: list[tuple[str, str, float, float, str, str, str, str]] = []
        if co_receipts_count == 0:
            receipts_seed.extend(
                [
                    ("med-001", "CHICKEN", 14.0, 13200.0, "COP", "recepcion seed co proteina", (now - timedelta(days=6)).isoformat(), "operations"),
                    ("med-002", "POTATO", 20.0, 3190.0, "COP", "recepcion seed co produce", (now - timedelta(days=5)).isoformat(), "operations"),
                    ("bog-001", "CHICKEN", 11.0, 13400.0, "COP", "recepcion seed co ajuste", (now - timedelta(days=3)).isoformat(), "operations"),
                ]
            )
        if us_receipts_count == 0:
            receipts_seed.extend(
                [
                    ("mia-001", "CHICKEN", 16.0, 3.55, "USD", "receipt seed us protein", (now - timedelta(days=4)).isoformat(), "operations"),
                    ("mia-002", "POTATO", 24.0, 1.44, "USD", "receipt seed us produce", (now - timedelta(days=2)).isoformat(), "operations"),
                    ("orl-001", "CHICKEN", 10.0, 3.55, "USD", "receipt seed us baseline", (now - timedelta(days=1)).isoformat(), "operations"),
                ]
            )

        if receipts_seed:
            db.executemany(
                """
                INSERT INTO inventory_receipts (
                    store_id, sku, received_qty, unit_cost, currency, note, received_at, received_by_role
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                receipts_seed,
            )

        existing_hr_employees = db.execute("SELECT COUNT(*) AS c FROM hr_employees").fetchone()["c"]
        if existing_hr_employees == 0:
            now = datetime.now(timezone.utc)
            co_store_ids = [store[0] for store in stores if store[2] == "CO"]
            us_store_ids = [store[0] for store in stores if store[2] == "US"]
            role_titles = [
                "Kitchen Operator",
                "Shift Lead",
                "Cashier",
                "Prep Cook",
                "Store Manager",
            ]

            employees_seed: list[tuple[str, str, str, str, str, str, str, str | None]] = []

            for idx in range(1, 116):
                country_code = "CO" if idx <= 63 else "US"
                local_idx = idx if idx <= 63 else idx - 63
                store_pool = co_store_ids if country_code == "CO" else us_store_ids
                store_id = store_pool[(local_idx - 1) % len(store_pool)]
                role_title = role_titles[(idx - 1) % len(role_titles)]
                hire_date = (now - timedelta(days=45 + (idx * 9 % 880))).replace(hour=0, minute=0, second=0, microsecond=0)
                employee_id = f"emp-{country_code.lower()}-{idx:03d}"
                full_name = f"Employee {country_code} {idx:03d}"
                employees_seed.append(
                    (
                        employee_id,
                        full_name,
                        country_code,
                        store_id,
                        role_title,
                        "active",
                        hire_date.isoformat(),
                        None,
                    )
                )

            for idx in range(1, 9):
                country_code = "CO" if idx <= 4 else "US"
                store_pool = co_store_ids if country_code == "CO" else us_store_ids
                store_id = store_pool[(idx - 1) % len(store_pool)]
                hire_date = (now - timedelta(days=640 + (idx * 17))).replace(hour=0, minute=0, second=0, microsecond=0)
                terminated_at = (now - timedelta(days=11 + idx * 4)).replace(hour=0, minute=0, second=0, microsecond=0)
                employees_seed.append(
                    (
                        f"emp-{country_code.lower()}-term-{idx:03d}",
                        f"Former Employee {country_code} {idx:03d}",
                        country_code,
                        store_id,
                        "Kitchen Operator",
                        "terminated",
                        hire_date.isoformat(),
                        terminated_at.isoformat(),
                    )
                )

            db.executemany(
                """
                INSERT INTO hr_employees (
                    id, full_name, country, store_id, role_title, employment_status, hire_date, terminated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                employees_seed,
            )

        existing_hr_requests = db.execute("SELECT COUNT(*) AS c FROM hr_time_off_requests").fetchone()["c"]
        if existing_hr_requests == 0:
            now = datetime.now(timezone.utc)
            requests_seed = [
                (
                    "emp-co-001",
                    "med-001",
                    "CO",
                    "vacation",
                    (now + timedelta(days=18)).date().isoformat(),
                    (now + timedelta(days=22)).date().isoformat(),
                    5,
                    "Vacaciones familiares",
                    "pending",
                    (now - timedelta(days=1)).isoformat(),
                    None,
                    None,
                    None,
                ),
                (
                    "emp-us-070",
                    "mia-001",
                    "US",
                    "sick_leave",
                    (now - timedelta(days=3)).date().isoformat(),
                    (now - timedelta(days=2)).date().isoformat(),
                    2,
                    "Recuperacion medica",
                    "approved",
                    (now - timedelta(days=4)).isoformat(),
                    (now - timedelta(days=4)).isoformat(),
                    "operations",
                    "Aprobado con soporte medico",
                ),
                (
                    "emp-co-015",
                    "med-003",
                    "CO",
                    "personal_leave",
                    (now + timedelta(days=4)).date().isoformat(),
                    (now + timedelta(days=4)).date().isoformat(),
                    1,
                    "Diligencia personal",
                    "pending",
                    (now - timedelta(hours=18)).isoformat(),
                    None,
                    None,
                    None,
                ),
            ]
            db.executemany(
                """
                INSERT INTO hr_time_off_requests (
                    employee_id, store_id, country, request_type, start_date, end_date, total_days, reason,
                    status, created_at, decided_at, decided_by_role, decision_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                requests_seed,
            )

        existing_absences = db.execute("SELECT COUNT(*) AS c FROM hr_absence_events").fetchone()["c"]
        if existing_absences == 0:
            now = datetime.now(timezone.utc)
            absences_seed = [
                (
                    "emp-us-070",
                    "US",
                    "sick_leave",
                    (now - timedelta(days=3)).date().isoformat(),
                    (now - timedelta(days=2)).date().isoformat(),
                    2.0,
                    None,
                    (now - timedelta(days=2)).isoformat(),
                ),
                (
                    "emp-co-028",
                    "CO",
                    "vacation",
                    (now - timedelta(days=16)).date().isoformat(),
                    (now - timedelta(days=11)).date().isoformat(),
                    6.0,
                    None,
                    (now - timedelta(days=11)).isoformat(),
                ),
            ]
            db.executemany(
                """
                INSERT INTO hr_absence_events (
                    employee_id, country, absence_type, start_date, end_date, total_days, source_request_id, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                absences_seed,
            )

        existing_onboarding = db.execute("SELECT COUNT(*) AS c FROM hr_onboarding_cases").fetchone()["c"]
        if existing_onboarding == 0:
            now = datetime.now(timezone.utc)
            onboarding_seed = [
                (
                    "emp-co-010",
                    "med-002",
                    "CO",
                    "Kitchen Operator",
                    "Laura Medina",
                    "active",
                    2,
                    4,
                    "orientation",
                    (now - timedelta(days=4)).isoformat(),
                    (now + timedelta(days=10)).isoformat(),
                    now.isoformat(),
                    "Pendiente validacion de estacion caliente",
                ),
                (
                    "emp-us-082",
                    "mia-003",
                    "US",
                    "Prep Cook",
                    "Ashley Turner",
                    "active",
                    1,
                    4,
                    "documents",
                    (now - timedelta(days=2)).isoformat(),
                    (now + timedelta(days=12)).isoformat(),
                    now.isoformat(),
                    "Onboarding inicial en curso",
                ),
            ]
            db.executemany(
                """
                INSERT INTO hr_onboarding_cases (
                    employee_id, store_id, country, position_title, mentor_name, status, completed_steps, total_steps,
                    last_step_key, started_at, target_completion_at, last_updated_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                onboarding_seed,
            )

        existing_vacancies = db.execute("SELECT COUNT(*) AS c FROM hr_vacancies").fetchone()["c"]
        if existing_vacancies == 0:
            now = datetime.now(timezone.utc)
            vacancies_seed = [
                (
                    "med-001",
                    "CO",
                    "Kitchen Operator",
                    (now - timedelta(days=65)).isoformat(),
                    (now - timedelta(days=44)).isoformat(),
                    "filled",
                ),
                (
                    "bog-001",
                    "CO",
                    "Cashier",
                    (now - timedelta(days=28)).isoformat(),
                    None,
                    "open",
                ),
                (
                    "mia-001",
                    "US",
                    "Kitchen Operator",
                    (now - timedelta(days=58)).isoformat(),
                    (now - timedelta(days=32)).isoformat(),
                    "filled",
                ),
                (
                    "orl-001",
                    "US",
                    "Shift Lead",
                    (now - timedelta(days=36)).isoformat(),
                    None,
                    "open",
                ),
            ]
            db.executemany(
                """
                INSERT INTO hr_vacancies (store_id, country, role_title, opened_at, filled_at, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                vacancies_seed,
            )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/realtime")
async def realtime_updates_socket(websocket: WebSocket) -> None:
    role = websocket.query_params.get("role")
    token = websocket.query_params.get("token")

    try:
        validated_role = validate_role_token_for_ws(role, token, {"executive", "operations", "admin"})
    except HTTPException:
        await websocket.close(code=4403)
        return

    await websocket.accept()

    try:
        digest = build_realtime_digest()
        await websocket.send_json(
            {
                "type": "snapshot",
                "source": "brasaland-realtime",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "digest": digest,
                "role": validated_role,
            }
        )

        while True:
            await asyncio.sleep(2)
            latest_digest = build_realtime_digest()
            if latest_digest != digest:
                digest = latest_digest
                await websocket.send_json(
                    {
                        "type": "update",
                        "source": "brasaland-realtime",
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "digest": digest,
                    }
                )
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.close(code=1011)


@app.get("/api/v1/stores", response_model=list[Store])
def get_stores() -> list[Store]:
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, country, city, timezone, base_currency FROM stores ORDER BY id"
        ).fetchall()
    return [Store(**dict(row)) for row in rows]


@app.get("/api/v1/menus/items", response_model=list[MenuItem])
def get_menu_items(
    country: Literal["CO", "US"] | None = Query(default=None),
    store_id: str | None = Query(default=None),
    locale: Literal["es", "en"] | None = Query(default=None),
    currency: Literal["COP", "USD"] | None = Query(default=None),
    active_only: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=1000),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[MenuItem]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, store_id, country, sku, name, description, category,
                   price_amount, currency, locale, is_active, updated_at
            FROM menu_items
            WHERE (? IS NULL OR country = ?)
              AND (? IS NULL OR store_id = ?)
              AND (? IS NULL OR locale = ?)
              AND (? = 0 OR is_active = 1)
            ORDER BY country ASC, category ASC, name ASC
            LIMIT ?
            """,
            (country, country, store_id, store_id, locale, locale, 1 if active_only else 0, limit),
        ).fetchall()

    output: list[MenuItem] = []
    for row in rows:
        target_currency = currency or row["currency"]
        converted_price = convert_amount(float(row["price_amount"]), row["currency"], target_currency)
        output.append(
            MenuItem(
                id=row["id"],
                store_id=row["store_id"],
                country=row["country"],
                market=market_label(row["country"]),
                sku=row["sku"],
                name=row["name"],
                description=row["description"],
                category=row["category"],
                price_amount=round(converted_price, 2),
                currency=target_currency,
                locale=row["locale"],
                is_active=bool(row["is_active"]),
                updated_at=parse_datetime_or_none(row["updated_at"]) or datetime.now(timezone.utc),
            )
        )

    write_audit_log(
        role,
        "read_menu_items",
        "success",
        f"country={country or 'ALL'}",
        f"store_id={store_id or 'ALL'}, locale={locale or 'ALL'}, rows={len(output)}",
    )
    return output


@app.post("/api/v1/menus/items", response_model=MenuItem, status_code=201)
def upsert_menu_item(
    payload: MenuItemCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> MenuItem:
    if payload.price_amount <= 0:
        raise HTTPException(status_code=400, detail="price_amount must be greater than zero")

    now = datetime.now(timezone.utc)
    with get_db() as db:
        if payload.store_id:
            store_row = db.execute(
                "SELECT id, country FROM stores WHERE id = ?",
                (payload.store_id,),
            ).fetchone()
            if store_row is None:
                raise HTTPException(status_code=404, detail="store_id not found")
            if store_row["country"] != payload.country:
                raise HTTPException(status_code=400, detail="store country does not match payload country")

        db.execute(
            """
            INSERT INTO menu_items (
                id, store_id, country, sku, name, description, category,
                price_amount, currency, locale, is_active, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                store_id = excluded.store_id,
                country = excluded.country,
                sku = excluded.sku,
                name = excluded.name,
                description = excluded.description,
                category = excluded.category,
                price_amount = excluded.price_amount,
                currency = excluded.currency,
                locale = excluded.locale,
                is_active = excluded.is_active,
                updated_at = excluded.updated_at
            """,
            (
                payload.id,
                payload.store_id,
                payload.country,
                payload.sku,
                payload.name,
                payload.description,
                payload.category,
                payload.price_amount,
                payload.currency,
                payload.locale,
                1 if payload.is_active else 0,
                now.isoformat(),
            ),
        )

        row = db.execute(
            """
            SELECT id, store_id, country, sku, name, description, category,
                   price_amount, currency, locale, is_active, updated_at
            FROM menu_items
            WHERE id = ?
            """,
            (payload.id,),
        ).fetchone()

    write_audit_log(
        role,
        "upsert_menu_item",
        "success",
        payload.id,
        f"country={payload.country}, sku={payload.sku}",
    )

    return MenuItem(
        id=row["id"],
        store_id=row["store_id"],
        country=row["country"],
        market=market_label(row["country"]),
        sku=row["sku"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        price_amount=float(row["price_amount"]),
        currency=row["currency"],
        locale=row["locale"],
        is_active=bool(row["is_active"]),
        updated_at=parse_datetime_or_none(row["updated_at"]) or now,
    )


@app.post("/api/v1/telemetry/events", response_model=StoreTelemetryEventCreated, status_code=201)
def create_store_telemetry_event(
    payload: StoreTelemetryEventCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> StoreTelemetryEventCreated:
    if payload.sales_last_5m < 0:
        raise HTTPException(status_code=400, detail="sales_last_5m must be >= 0")
    if payload.open_tickets < 0:
        raise HTTPException(status_code=400, detail="open_tickets must be >= 0")
    if payload.avg_prep_seconds < 0:
        raise HTTPException(status_code=400, detail="avg_prep_seconds must be >= 0")
    if payload.network_rtt_ms < 0:
        raise HTTPException(status_code=400, detail="network_rtt_ms must be >= 0")

    now = datetime.now(timezone.utc)
    event_ts = payload.event_ts.astimezone(timezone.utc)
    latency_seconds = max((now - event_ts).total_seconds(), 0.0)

    with get_db() as db:
        store_exists = db.execute("SELECT 1 FROM stores WHERE id = ?", (payload.store_id,)).fetchone()
        if store_exists is None:
            raise HTTPException(status_code=404, detail="store_id not found")

        cursor = db.execute(
            """
            INSERT INTO store_telemetry_events (
                store_id, source_system, event_ts, ingested_at, latency_seconds,
                pos_online, sales_last_5m, open_tickets, avg_prep_seconds,
                network_rtt_ms, terminal_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.store_id,
                payload.source_system,
                event_ts.isoformat(),
                now.isoformat(),
                latency_seconds,
                1 if payload.pos_online else 0,
                payload.sales_last_5m,
                payload.open_tickets,
                payload.avg_prep_seconds,
                payload.network_rtt_ms,
                payload.terminal_version,
            ),
        )
        telemetry_id = int(cursor.lastrowid)

    write_audit_log(
        role,
        "create_store_telemetry_event",
        "success",
        payload.store_id,
        f"id={telemetry_id}, source={payload.source_system}, latency_s={latency_seconds:.2f}",
    )

    return StoreTelemetryEventCreated(
        id=telemetry_id,
        store_id=payload.store_id,
        source_system=payload.source_system,
        event_ts=event_ts,
        ingested_at=now,
        latency_seconds=round(latency_seconds, 3),
    )


@app.get("/api/v1/telemetry/stores/status", response_model=StoreTelemetryStatusResponse)
def get_store_telemetry_status(
    window_minutes: int = Query(default=10, ge=1, le=120),
    country: Literal["CO", "US"] | None = Query(default=None),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> StoreTelemetryStatusResponse:
    now = datetime.now(timezone.utc)
    with get_db() as db:
        rows = db.execute(
            """
            SELECT st.id AS store_id, st.name AS store_name, st.country,
                   te.event_ts, te.source_system, te.pos_online, te.sales_last_5m,
                   te.open_tickets, te.avg_prep_seconds, te.network_rtt_ms, te.terminal_version
            FROM stores st
            LEFT JOIN store_telemetry_events te
              ON te.id = (
                  SELECT t2.id
                  FROM store_telemetry_events t2
                  WHERE t2.store_id = st.id
                  ORDER BY t2.event_ts DESC, t2.id DESC
                  LIMIT 1
              )
            WHERE (? IS NULL OR st.country = ?)
            ORDER BY st.id ASC
            """,
            (country, country),
        ).fetchall()

    status_rows: list[StoreTelemetryStatusRow] = []
    online_stores = 0
    stale_stores = 0
    offline_stores = 0

    for row in rows:
        last_event = parse_datetime_or_none(row["event_ts"])
        minutes_since = None
        freshness: Literal["online", "stale", "offline"]
        if last_event is None:
            freshness = "offline"
            offline_stores += 1
        else:
            minutes_since = max((now - last_event.astimezone(timezone.utc)).total_seconds() / 60.0, 0.0)
            if minutes_since <= window_minutes and bool(row["pos_online"]):
                freshness = "online"
                online_stores += 1
            elif minutes_since <= (window_minutes * 2):
                freshness = "stale"
                stale_stores += 1
            else:
                freshness = "offline"
                offline_stores += 1

        status_rows.append(
            StoreTelemetryStatusRow(
                store_id=row["store_id"],
                store_name=row["store_name"],
                country=row["country"],
                market=market_label(row["country"]),
                last_event_at=last_event,
                minutes_since_last_event=round(minutes_since, 2) if minutes_since is not None else None,
                freshness=freshness,
                source_system=row["source_system"],
                pos_online=bool(row["pos_online"]) if row["pos_online"] is not None else None,
                sales_last_5m=int(row["sales_last_5m"]) if row["sales_last_5m"] is not None else None,
                open_tickets=int(row["open_tickets"]) if row["open_tickets"] is not None else None,
                avg_prep_seconds=float(row["avg_prep_seconds"]) if row["avg_prep_seconds"] is not None else None,
                network_rtt_ms=float(row["network_rtt_ms"]) if row["network_rtt_ms"] is not None else None,
                terminal_version=row["terminal_version"],
            )
        )

    write_audit_log(
        role,
        "read_store_telemetry_status",
        "success",
        f"country={country or 'ALL'}",
        f"window_minutes={window_minutes}, online={online_stores}, stale={stale_stores}, offline={offline_stores}",
    )

    return StoreTelemetryStatusResponse(
        window_minutes=window_minutes,
        generated_at=now,
        total_stores=len(status_rows),
        online_stores=online_stores,
        stale_stores=stale_stores,
        offline_stores=offline_stores,
        rows=status_rows,
    )


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
    opening_hours_only: bool = Query(default=True),
    reference_at: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> InactivityAlertResponse:
    now = reference_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    alerts: list[InactivityAlert] = []
    monitored_stores = 0

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
            try:
                local_now = now.astimezone(ZoneInfo(store["timezone"]))
            except Exception:
                local_now = now

            opening_hours = STORE_OPENING_HOURS.get(store["id"], (10, 22))
            store_is_open = is_store_open_at(local_now, opening_hours[0], opening_hours[1])
            if opening_hours_only and not store_is_open:
                continue

            monitored_stores += 1

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

    total_stores = monitored_stores if opening_hours_only else len(stores)
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
        (
            f"window_minutes={window_minutes}, severity={severity_filter or 'ALL'}, "
            f"opening_hours_only={opening_hours_only}, monitored_stores={total_stores}, alerts={len(alerts)}"
        ),
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


@app.get("/api/v1/reports/hr.csv")
def export_hr_report_csv(
    days: int = Query(default=90, ge=30, le=365),
    country: Literal["CO", "US"] | None = Query(default=None),
    section: Literal["all", "requests", "onboarding", "kpis"] = Query(default="all"),
    role: str = Depends(require_roles({"executive", "operations", "admin"})),
) -> Response:
    now = datetime.now(timezone.utc)
    start_at = now - timedelta(days=days)

    with get_db() as db:
        requests_rows: list[Row] = []
        onboarding_rows: list[Row] = []

        if section in {"all", "requests"}:
            requests_rows = db.execute(
                """
                SELECT r.id, r.employee_id, e.full_name AS employee_name, r.store_id, r.country,
                       r.request_type, r.start_date, r.end_date, r.total_days, r.reason,
                       r.status, r.created_at, r.decided_at, r.decision_note
                FROM hr_time_off_requests r
                JOIN hr_employees e ON e.id = r.employee_id
                WHERE r.created_at >= ? AND r.created_at < ?
                  AND (? IS NULL OR r.country = ?)
                ORDER BY r.created_at DESC, r.id DESC
                """,
                (start_at.isoformat(), now.isoformat(), country, country),
            ).fetchall()

        if section in {"all", "onboarding"}:
            onboarding_rows = db.execute(
                """
                SELECT oc.id, oc.employee_id, e.full_name AS employee_name, oc.store_id, oc.country,
                       oc.position_title, oc.mentor_name, oc.status, oc.completed_steps, oc.total_steps,
                       oc.last_step_key, oc.started_at, oc.target_completion_at, oc.last_updated_at, oc.notes
                FROM hr_onboarding_cases oc
                JOIN hr_employees e ON e.id = oc.employee_id
                WHERE oc.last_updated_at >= ? AND oc.last_updated_at < ?
                  AND (? IS NULL OR oc.country = ?)
                ORDER BY oc.last_updated_at DESC, oc.id DESC
                """,
                (start_at.isoformat(), now.isoformat(), country, country),
            ).fetchall()

    kpis_payload: HrKpiOverviewResponse | None = None
    if section in {"all", "kpis"}:
        kpis_payload = get_hr_kpis_overview(days=days, country=country, role=role)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "record_type",
            "country",
            "market",
            "id",
            "employee_id",
            "employee_name",
            "store_id",
            "status",
            "metric",
            "value",
            "start_date",
            "end_date",
            "created_at",
            "updated_at",
            "note",
        ]
    )

    for row in requests_rows:
        writer.writerow(
            [
                "time_off_request",
                row["country"],
                market_label(row["country"]),
                row["id"],
                row["employee_id"],
                row["employee_name"],
                row["store_id"],
                row["status"],
                row["request_type"],
                row["total_days"],
                row["start_date"],
                row["end_date"],
                row["created_at"],
                row["decided_at"] or "",
                row["decision_note"] or row["reason"],
            ]
        )

    for row in onboarding_rows:
        writer.writerow(
            [
                "onboarding_case",
                row["country"],
                market_label(row["country"]),
                row["id"],
                row["employee_id"],
                row["employee_name"],
                row["store_id"],
                row["status"],
                "progress_steps",
                f"{row['completed_steps']}/{row['total_steps']}",
                row["started_at"],
                row["target_completion_at"],
                row["started_at"],
                row["last_updated_at"],
                f"mentor={row['mentor_name']}; step={row['last_step_key'] or ''}; notes={row['notes'] or ''}",
            ]
        )

    if kpis_payload is not None:
        writer.writerow(
            [
                "kpi_overall",
                country or "ALL",
                "Chain",
                "-",
                "-",
                "-",
                "-",
                "snapshot",
                "overall_turnover_rate_pct",
                f"{kpis_payload.overall_turnover_rate_pct:.2f}",
                start_at.date().isoformat(),
                now.date().isoformat(),
                now.isoformat(),
                now.isoformat(),
                "",
            ]
        )
        writer.writerow(
            [
                "kpi_overall",
                country or "ALL",
                "Chain",
                "-",
                "-",
                "-",
                "-",
                "snapshot",
                "overall_absenteeism_rate_pct",
                f"{kpis_payload.overall_absenteeism_rate_pct:.3f}",
                start_at.date().isoformat(),
                now.date().isoformat(),
                now.isoformat(),
                now.isoformat(),
                "",
            ]
        )
        writer.writerow(
            [
                "kpi_overall",
                country or "ALL",
                "Chain",
                "-",
                "-",
                "-",
                "-",
                "snapshot",
                "overall_avg_time_to_fill_days",
                f"{kpis_payload.overall_avg_time_to_fill_days:.2f}",
                start_at.date().isoformat(),
                now.date().isoformat(),
                now.isoformat(),
                now.isoformat(),
                "",
            ]
        )

        for item in kpis_payload.by_country:
            writer.writerow(
                [
                    "kpi_country",
                    item.country,
                    item.market,
                    "-",
                    "-",
                    "-",
                    "-",
                    "snapshot",
                    "turnover_rate_pct",
                    f"{item.turnover_rate_pct:.2f}",
                    start_at.date().isoformat(),
                    now.date().isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                    f"active_headcount={item.active_headcount}; terminations={item.terminations}",
                ]
            )
            writer.writerow(
                [
                    "kpi_country",
                    item.country,
                    item.market,
                    "-",
                    "-",
                    "-",
                    "-",
                    "snapshot",
                    "absenteeism_rate_pct",
                    f"{item.absenteeism_rate_pct:.3f}",
                    start_at.date().isoformat(),
                    now.date().isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                    f"absent_days={item.absent_days:.2f}",
                ]
            )
            writer.writerow(
                [
                    "kpi_country",
                    item.country,
                    item.market,
                    "-",
                    "-",
                    "-",
                    "-",
                    "snapshot",
                    "avg_time_to_fill_days",
                    f"{item.avg_time_to_fill_days:.2f}",
                    start_at.date().isoformat(),
                    now.date().isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                    f"open_vacancies={item.open_vacancies}; pending_requests={item.pending_time_off_requests}; onboarding_active={item.active_onboarding_cases}",
                ]
            )

    total_rows = len(requests_rows) + len(onboarding_rows)
    if kpis_payload is not None:
        total_rows += 3 + (len(kpis_payload.by_country) * 3)

    filename = f"brasaland-hr-{section}-{datetime.now(timezone.utc).date().isoformat()}.csv"
    write_audit_log(
        role,
        "export_hr_csv",
        "success",
        f"country={country or 'ALL'}",
        f"section={section}, days={days}, rows={total_rows}",
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


@app.get("/api/v1/inventory/stock", response_model=list[InventoryStockRow])
def get_inventory_stock(
    country: Literal["CO", "US"] | None = Query(default=None),
    store_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[InventoryStockRow]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT st.id AS store_id, st.name AS store_name, st.country,
                   sl.sku, sl.item_name, sl.category, sl.unit,
                   sl.current_stock, sl.min_stock, sl.updated_at
            FROM stock_levels sl
            JOIN stores st ON st.id = sl.store_id
            WHERE (? IS NULL OR st.country = ?)
              AND (? IS NULL OR st.id = ?)
            ORDER BY st.id ASC, sl.sku ASC
            LIMIT ?
            """,
            (country, country, store_id, store_id, limit),
        ).fetchall()

    output: list[InventoryStockRow] = []
    for row in rows:
        updated_at = parse_datetime_or_none(row["updated_at"]) or datetime.now(timezone.utc)
        output.append(
            InventoryStockRow(
                store_id=row["store_id"],
                store_name=row["store_name"],
                country=row["country"],
                market=market_label(row["country"]),
                sku=row["sku"],
                item_name=row["item_name"],
                category=row["category"],
                unit=row["unit"],
                current_stock=round(float(row["current_stock"]), 3),
                min_stock=round(float(row["min_stock"]), 3),
                last_updated=updated_at,
            )
        )

    write_audit_log(
        role,
        "read_inventory_stock",
        "success",
        f"country={country or 'ALL'}",
        f"store_id={store_id or 'ALL'}, rows={len(output)}",
    )
    return output


@app.get("/api/v1/orders/recommendations", response_model=SmartOrderRecommendationResponse)
def get_smart_order_recommendations(
    country: Literal["CO", "US"] | None = Query(default=None),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    days_history: int = Query(default=14, ge=7, le=60),
    target_days: int = Query(default=7, ge=3, le=21),
    only_at_risk: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=500),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> SmartOrderRecommendationResponse:
    now = datetime.now(timezone.utc)
    start_at = now - timedelta(days=days_history)

    with get_db() as db:
        stock_rows = db.execute(
            """
            SELECT st.id AS store_id, st.name AS store_name, st.country,
                   sl.sku, sl.item_name, sl.category, sl.unit,
                   sl.current_stock, sl.min_stock
            FROM stock_levels sl
            JOIN stores st ON st.id = sl.store_id
            WHERE (? IS NULL OR st.country = ?)
            ORDER BY st.id ASC, sl.sku ASC
            """,
            (country, country),
        ).fetchall()

        sales_rows = db.execute(
            """
            SELECT se.store_id, COUNT(*) AS tickets
            FROM sales_events se
            JOIN stores st ON st.id = se.store_id
            WHERE se.sold_at >= ? AND se.sold_at < ?
              AND (? IS NULL OR st.country = ?)
            GROUP BY se.store_id
            """,
            (start_at.isoformat(), now.isoformat(), country, country),
        ).fetchall()

        supplier_rows = db.execute(
            """
            SELECT supplier_id, sku, country, currency, price
            FROM supplier_prices
            WHERE (? IS NULL OR country = ?)
            ORDER BY country ASC, sku ASC, valid_from DESC
            """,
            (country, country),
        ).fetchall()

    tickets_by_store = {row["store_id"]: int(row["tickets"]) for row in sales_rows}

    latest_price_by_country_sku: dict[tuple[str, str], tuple[str, float]] = {}
    for row in supplier_rows:
        key = (row["country"], row["sku"])
        if key not in latest_price_by_country_sku:
            latest_price_by_country_sku[key] = (row["currency"], float(row["price"]))

    recommendations: list[SmartOrderRecommendationRow] = []
    for row in stock_rows:
        recommendations.append(
            build_smart_order_recommendation_row(
                store_id=row["store_id"],
                store_name=row["store_name"],
                country_code=row["country"],
                sku=row["sku"],
                item_name=row["item_name"],
                category=row["category"],
                unit=row["unit"],
                current_stock=float(row["current_stock"]),
                min_stock=float(row["min_stock"]),
                tickets=tickets_by_store.get(row["store_id"], 0),
                days_history=days_history,
                target_days=target_days,
                currency=currency,
                latest_price_by_country_sku=latest_price_by_country_sku,
            )
        )

    recommendations.sort(
        key=lambda item: (
            0 if item.risk_level == "critical" else 1 if item.risk_level == "warning" else 2,
            item.projected_days_of_cover,
        )
    )

    if only_at_risk:
        recommendations = [item for item in recommendations if item.risk_level != "ok"]
    recommendations = recommendations[:limit]

    write_audit_log(
        role,
        "read_smart_order_recommendations",
        "success",
        f"country={country or 'ALL'}",
        (
            f"days_history={days_history}, target_days={target_days}, only_at_risk={only_at_risk}, "
            f"rows={len(recommendations)}"
        ),
    )

    return SmartOrderRecommendationResponse(
        country=country,
        currency=currency,
        days_history=days_history,
        target_days_of_cover=target_days,
        generated_at=now,
        recommendations=recommendations,
    )


@app.post("/api/v1/inventory/receipts", response_model=InventoryReceiptResult, status_code=201)
def create_inventory_receipt(
    payload: InventoryReceiptCreate,
    days_history: int = Query(default=14, ge=7, le=60),
    target_days: int = Query(default=7, ge=3, le=21),
    role: str = Depends(require_roles({"operations", "admin"})),
) -> InventoryReceiptResult:
    if payload.received_qty <= 0:
        write_audit_log(role, "create_inventory_receipt", "rejected", payload.store_id, "received_qty <= 0")
        raise HTTPException(status_code=400, detail="received_qty must be greater than zero")

    now = datetime.now(timezone.utc)
    normalized_sku = payload.sku.upper()

    with get_db() as db:
        stock_row = db.execute(
            """
            SELECT st.id AS store_id, st.name AS store_name, st.country,
                   sl.sku, sl.item_name, sl.category, sl.unit,
                   sl.current_stock, sl.min_stock
            FROM stock_levels sl
            JOIN stores st ON st.id = sl.store_id
            WHERE st.id = ? AND sl.sku = ?
            """,
            (payload.store_id, normalized_sku),
        ).fetchone()

        if stock_row is None:
            write_audit_log(
                role,
                "create_inventory_receipt",
                "rejected",
                payload.store_id,
                f"stock row not found for sku={normalized_sku}",
            )
            raise HTTPException(status_code=404, detail="stock row not found for store_id and sku")

        previous_stock = float(stock_row["current_stock"])
        current_stock = previous_stock + float(payload.received_qty)

        db.execute(
            """
            UPDATE stock_levels
            SET current_stock = ?, updated_at = ?
            WHERE store_id = ? AND sku = ?
            """,
            (current_stock, now.isoformat(), payload.store_id, normalized_sku),
        )

        receipt_cursor = db.execute(
            """
            INSERT INTO inventory_receipts (
                store_id, sku, received_qty, unit_cost, currency, note, received_at, received_by_role
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.store_id,
                normalized_sku,
                float(payload.received_qty),
                payload.unit_cost,
                payload.currency,
                (payload.note or "")[:500],
                now.isoformat(),
                role,
            ),
        )

        sales_row = db.execute(
            """
            SELECT COUNT(*) AS tickets
            FROM sales_events
            WHERE store_id = ? AND sold_at >= ? AND sold_at < ?
            """,
            (payload.store_id, (now - timedelta(days=days_history)).isoformat(), now.isoformat()),
        ).fetchone()
        tickets = int(sales_row["tickets"]) if sales_row is not None else 0

        supplier_rows = db.execute(
            """
            SELECT supplier_id, sku, country, currency, price
            FROM supplier_prices
            WHERE country = ?
            ORDER BY sku ASC, valid_from DESC
            """,
            (stock_row["country"],),
        ).fetchall()

    latest_price_by_country_sku: dict[tuple[str, str], tuple[str, float]] = {}
    for row in supplier_rows:
        key = (row["country"], row["sku"])
        if key not in latest_price_by_country_sku:
            latest_price_by_country_sku[key] = (row["currency"], float(row["price"]))

    recommendation_after = build_smart_order_recommendation_row(
        store_id=payload.store_id,
        store_name=stock_row["store_name"],
        country_code=stock_row["country"],
        sku=normalized_sku,
        item_name=stock_row["item_name"],
        category=stock_row["category"],
        unit=stock_row["unit"],
        current_stock=current_stock,
        min_stock=float(stock_row["min_stock"]),
        tickets=tickets,
        days_history=days_history,
        target_days=target_days,
        currency=payload.currency,
        latest_price_by_country_sku=latest_price_by_country_sku,
    )

    recommendation_status: Literal["open", "closed"] = (
        "closed" if recommendation_after.recommended_order_qty <= 0 and recommendation_after.risk_level == "ok" else "open"
    )

    estimated_receipt_cost = None
    if payload.unit_cost is not None:
        estimated_receipt_cost = round(payload.unit_cost * float(payload.received_qty), 2)

    write_audit_log(
        role,
        "create_inventory_receipt",
        "success",
        payload.store_id,
        (
            f"sku={normalized_sku}, received_qty={payload.received_qty}, "
            f"recommendation_status={recommendation_status}"
        ),
    )

    return InventoryReceiptResult(
        receipt_id=int(receipt_cursor.lastrowid),
        store_id=payload.store_id,
        sku=normalized_sku,
        previous_stock=round(previous_stock, 3),
        current_stock=round(current_stock, 3),
        received_qty=round(float(payload.received_qty), 3),
        estimated_receipt_cost=estimated_receipt_cost,
        currency=payload.currency,
        recommendation_status=recommendation_status,
        recommendation_after=recommendation_after,
        updated_at=now,
    )


@app.get("/api/v1/inventory/receipts", response_model=list[InventoryReceiptRow])
def get_inventory_receipts(
    country: Literal["CO", "US"] | None = Query(default=None),
    store_id: str | None = Query(default=None),
    sku: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=5000),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[InventoryReceiptRow]:
    normalized_sku = sku.upper() if sku is not None else None

    with get_db() as db:
        rows = db.execute(
            """
            SELECT ir.id, ir.store_id, st.name AS store_name, st.country,
                   ir.sku, ir.received_qty, ir.unit_cost, ir.currency,
                   ir.note, ir.received_at, ir.received_by_role
            FROM inventory_receipts ir
            JOIN stores st ON st.id = ir.store_id
            WHERE (? IS NULL OR st.country = ?)
              AND (? IS NULL OR ir.store_id = ?)
              AND (? IS NULL OR ir.sku = ?)
            ORDER BY ir.id DESC
            LIMIT ?
                        OFFSET ?
            """,
                        (country, country, store_id, store_id, normalized_sku, normalized_sku, limit, offset),
        ).fetchall()

    output: list[InventoryReceiptRow] = []
    for row in rows:
        output.append(
            InventoryReceiptRow(
                id=int(row["id"]),
                store_id=row["store_id"],
                store_name=row["store_name"],
                country=row["country"],
                market=market_label(row["country"]),
                sku=row["sku"],
                received_qty=round(float(row["received_qty"]), 3),
                unit_cost=round(float(row["unit_cost"]), 4) if row["unit_cost"] is not None else None,
                currency=row["currency"],
                note=row["note"] or None,
                received_at=parse_datetime_or_none(row["received_at"]) or datetime.now(timezone.utc),
                received_by_role=row["received_by_role"],
            )
        )

    write_audit_log(
        role,
        "read_inventory_receipts",
        "success",
        f"country={country or 'ALL'}",
        f"store_id={store_id or 'ALL'}, sku={normalized_sku or 'ALL'}, offset={offset}, rows={len(output)}",
    )
    return output


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


@app.get("/api/v1/training/recipes/search", response_model=RecipeCatalogSearchResponse)
def search_training_recipes(
    q: str = Query(default="", max_length=120),
    locale: Literal["es", "en"] | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> RecipeCatalogSearchResponse:
    search = q.strip().lower()
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, title, category, locale, tags, version, updated_at
            FROM training_resources
            WHERE category = 'recipe'
              AND (? IS NULL OR locale = ?)
            ORDER BY updated_at DESC, id ASC
            """,
            (locale, locale),
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

    output = output[:limit]

    write_audit_log(
        role,
        "search_training_recipes",
        "success",
        f"locale={locale or 'ALL'}",
        f"q={search or '-'}, results={len(output)}",
    )

    return RecipeCatalogSearchResponse(
        q=q,
        locale=locale,
        total_results=len(output),
        resources=output,
    )


@app.get("/api/v1/training/onboarding/itineraries", response_model=list[OnboardingItinerarySummary])
def get_training_onboarding_itineraries(
    role_target: str | None = Query(default=None),
    locale: Literal["es", "en"] | None = Query(default=None),
    only_active: bool = Query(default=True),
    limit: int = Query(default=30, ge=1, le=100),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[OnboardingItinerarySummary]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, title, role_target, locale, version, steps, updated_at, is_active
            FROM training_onboarding_itineraries
            WHERE (? IS NULL OR role_target = ?)
              AND (? IS NULL OR locale = ?)
              AND (? = 0 OR is_active = 1)
            ORDER BY updated_at DESC, id ASC
            LIMIT ?
            """,
            (role_target, role_target, locale, locale, 1 if only_active else 0, limit),
        ).fetchall()

    output = [
        OnboardingItinerarySummary(
            id=row["id"],
            title=row["title"],
            role_target=row["role_target"],
            locale=row["locale"],
            version=row["version"],
            steps_count=len([step for step in (row["steps"] or "").split("|") if step.strip()]),
            updated_at=parse_datetime_or_none(row["updated_at"]) or datetime.now(timezone.utc),
        )
        for row in rows
    ]

    write_audit_log(
        role,
        "read_training_onboarding_itineraries",
        "success",
        f"role_target={role_target or 'ALL'}",
        f"locale={locale or 'ALL'}, rows={len(output)}",
    )
    return output


@app.get("/api/v1/training/onboarding/itineraries/{itinerary_id}", response_model=OnboardingItineraryDetail)
def get_training_onboarding_itinerary_detail(
    itinerary_id: str,
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> OnboardingItineraryDetail:
    with get_db() as db:
        row = db.execute(
            """
            SELECT id, title, role_target, locale, version, steps, updated_at
            FROM training_onboarding_itineraries
            WHERE id = ?
            """,
            (itinerary_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="itinerary not found")

    steps = [step.strip() for step in (row["steps"] or "").split("|") if step.strip()]
    updated_at = parse_datetime_or_none(row["updated_at"]) or datetime.now(timezone.utc)

    write_audit_log(role, "read_training_onboarding_itinerary_detail", "success", itinerary_id, f"steps={len(steps)}")

    return OnboardingItineraryDetail(
        id=row["id"],
        title=row["title"],
        role_target=row["role_target"],
        locale=row["locale"],
        version=row["version"],
        steps_count=len(steps),
        updated_at=updated_at,
        steps=steps,
    )


@app.post("/api/v1/training/onboarding/assign", response_model=HrOnboardingCaseRow, status_code=201)
def assign_training_onboarding_itinerary(
    payload: OnboardingAssignmentCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> HrOnboardingCaseRow:
    now = datetime.now(timezone.utc)
    started_at = parse_iso_date(payload.start_date, "start_date") if payload.start_date else now

    with get_db() as db:
        itinerary_row = db.execute(
            """
            SELECT id, title, role_target, locale, version, steps
            FROM training_onboarding_itineraries
            WHERE id = ? AND is_active = 1
            """,
            (payload.itinerary_id,),
        ).fetchone()
        if itinerary_row is None:
            raise HTTPException(status_code=404, detail="active itinerary not found")

        steps = [step.strip() for step in (itinerary_row["steps"] or "").split("|") if step.strip()]
        if not steps:
            raise HTTPException(status_code=400, detail="itinerary has no steps")

        employee_row = db.execute(
            """
            SELECT id, full_name, country, store_id, employment_status
            FROM hr_employees
            WHERE id = ?
            """,
            (payload.employee_id,),
        ).fetchone()
        if employee_row is None:
            raise HTTPException(status_code=404, detail="employee not found")
        if employee_row["employment_status"] != "active":
            raise HTTPException(status_code=400, detail="employee is not active")

        active_case = db.execute(
            """
            SELECT 1 FROM hr_onboarding_cases
            WHERE employee_id = ? AND status = 'active'
            """,
            (payload.employee_id,),
        ).fetchone()
        if active_case is not None:
            raise HTTPException(status_code=409, detail="employee already has an active onboarding case")

        notes = (
            f"itinerary={itinerary_row['id']}|{itinerary_row['title']}|{itinerary_row['version']}|"
            f"locale={itinerary_row['locale']}|step_1={steps[0]}"
        )

        cursor = db.execute(
            """
            INSERT INTO hr_onboarding_cases (
                employee_id, store_id, country, position_title, mentor_name, status, completed_steps,
                total_steps, last_step_key, started_at, target_completion_at, last_updated_at, notes
            ) VALUES (?, ?, ?, ?, ?, 'active', 1, ?, 'documents', ?, ?, ?, ?)
            """,
            (
                payload.employee_id,
                employee_row["store_id"],
                employee_row["country"],
                itinerary_row["role_target"],
                payload.mentor_name[:120],
                len(steps),
                started_at.isoformat(),
                (started_at + timedelta(days=14)).isoformat(),
                now.isoformat(),
                notes[:400],
            ),
        )
        case_id = int(cursor.lastrowid)

        case_row = db.execute(
            """
            SELECT oc.id, oc.employee_id, e.full_name AS employee_name, oc.store_id, oc.country,
                   oc.position_title, oc.mentor_name, oc.status, oc.completed_steps, oc.total_steps,
                   oc.last_step_key, oc.started_at, oc.target_completion_at, oc.last_updated_at, oc.notes
            FROM hr_onboarding_cases oc
            JOIN hr_employees e ON e.id = oc.employee_id
            WHERE oc.id = ?
            """,
            (case_id,),
        ).fetchone()

    write_audit_log(
        role,
        "assign_training_onboarding_itinerary",
        "success",
        payload.employee_id,
        f"itinerary={payload.itinerary_id}, case_id={case_id}",
    )

    return HrOnboardingCaseRow(
        id=int(case_row["id"]),
        employee_id=case_row["employee_id"],
        employee_name=case_row["employee_name"],
        store_id=case_row["store_id"],
        country=case_row["country"],
        market=market_label(case_row["country"]),
        position_title=case_row["position_title"],
        mentor_name=case_row["mentor_name"],
        status=case_row["status"],
        completed_steps=int(case_row["completed_steps"]),
        total_steps=int(case_row["total_steps"]),
        last_step_key=case_row["last_step_key"],
        started_at=parse_datetime_or_none(case_row["started_at"]) or now,
        target_completion_at=parse_datetime_or_none(case_row["target_completion_at"]) or now,
        last_updated_at=parse_datetime_or_none(case_row["last_updated_at"]) or now,
        notes=case_row["notes"],
    )


@app.get("/api/v1/training/recipes/updates", response_model=list[RecipeUpdateDistributionSummary])
def get_recipe_updates_distribution(
    country: Literal["CO", "US"] | None = Query(default=None),
    locale: Literal["es", "en"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[RecipeUpdateDistributionSummary]:
    with get_db() as db:
        update_rows = db.execute(
            """
            SELECT id, resource_id, resource_title, version, locale, change_summary,
                   mandatory, published_at
            FROM training_recipe_updates
            WHERE (? IS NULL OR locale = ?)
            ORDER BY published_at DESC, id DESC
            LIMIT ?
            """,
            (locale, locale, limit),
        ).fetchall()

        output: list[RecipeUpdateDistributionSummary] = []
        for row in update_rows:
            counts = db.execute(
                """
                SELECT
                    COUNT(*) AS delivered_count,
                    SUM(CASE WHEN d.status = 'acknowledged' THEN 1 ELSE 0 END) AS acknowledged_count
                FROM training_recipe_update_deliveries d
                JOIN stores st ON st.id = d.store_id
                WHERE d.update_id = ?
                  AND (? IS NULL OR st.country = ?)
                """,
                (row["id"], country, country),
            ).fetchone()

            delivered_stores = int(counts["delivered_count"] or 0)
            acknowledged_stores = int(counts["acknowledged_count"] or 0)
            pending_stores = max(delivered_stores - acknowledged_stores, 0)

            output.append(
                RecipeUpdateDistributionSummary(
                    update_id=int(row["id"]),
                    resource_id=row["resource_id"],
                    resource_title=row["resource_title"],
                    version=row["version"],
                    locale=row["locale"],
                    change_summary=row["change_summary"],
                    mandatory=bool(row["mandatory"]),
                    published_at=parse_datetime_or_none(row["published_at"]) or datetime.now(timezone.utc),
                    delivered_stores=delivered_stores,
                    acknowledged_stores=acknowledged_stores,
                    pending_stores=pending_stores,
                )
            )

    write_audit_log(
        role,
        "read_recipe_updates_distribution",
        "success",
        f"country={country or 'ALL'}",
        f"locale={locale or 'ALL'}, rows={len(output)}",
    )
    return output


@app.get("/api/v1/training/recipes/updates/{update_id}/deliveries", response_model=list[RecipeUpdateDeliveryRow])
def get_recipe_update_deliveries(
    update_id: int,
    country: Literal["CO", "US"] | None = Query(default=None),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[RecipeUpdateDeliveryRow]:
    with get_db() as db:
        update_exists = db.execute("SELECT 1 FROM training_recipe_updates WHERE id = ?", (update_id,)).fetchone()
        if update_exists is None:
            raise HTTPException(status_code=404, detail="recipe update not found")

        rows = db.execute(
            """
            SELECT d.id, d.update_id, d.store_id, st.name AS store_name, st.country,
                   d.delivered_at, d.acknowledged_at, d.acknowledged_by_role, d.status
            FROM training_recipe_update_deliveries d
            JOIN stores st ON st.id = d.store_id
            WHERE d.update_id = ?
              AND (? IS NULL OR st.country = ?)
            ORDER BY st.id ASC
            """,
            (update_id, country, country),
        ).fetchall()

    output = [
        RecipeUpdateDeliveryRow(
            id=int(row["id"]),
            update_id=int(row["update_id"]),
            store_id=row["store_id"],
            store_name=row["store_name"],
            country=row["country"],
            market=market_label(row["country"]),
            delivered_at=parse_datetime_or_none(row["delivered_at"]) or datetime.now(timezone.utc),
            acknowledged_at=parse_datetime_or_none(row["acknowledged_at"]),
            acknowledged_by_role=row["acknowledged_by_role"],
            status=row["status"],
        )
        for row in rows
    ]

    write_audit_log(
        role,
        "read_recipe_update_deliveries",
        "success",
        f"update_id={update_id}",
        f"country={country or 'ALL'}, rows={len(output)}",
    )
    return output


@app.post("/api/v1/training/recipes/updates/publish", response_model=RecipeUpdatePublishResult, status_code=201)
def publish_recipe_update(
    payload: RecipeUpdatePublishCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> RecipeUpdatePublishResult:
    now = datetime.now(timezone.utc)
    summary = payload.change_summary.strip()
    if not summary:
        raise HTTPException(status_code=400, detail="change_summary must not be empty")

    with get_db() as db:
        resource_row = db.execute(
            """
            SELECT id, title, category, locale, version
            FROM training_resources
            WHERE id = ?
            """,
            (payload.resource_id,),
        ).fetchone()
        if resource_row is None:
            raise HTTPException(status_code=404, detail="training resource not found")
        if resource_row["category"] != "recipe":
            raise HTTPException(status_code=400, detail="resource_id must reference a recipe")
        if payload.locale is not None and payload.locale != resource_row["locale"]:
            raise HTTPException(status_code=400, detail="payload locale does not match resource locale")

        cursor = db.execute(
            """
            INSERT INTO training_recipe_updates (
                resource_id, resource_title, version, locale, change_summary,
                mandatory, published_at, published_by_role
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resource_row["id"],
                resource_row["title"],
                resource_row["version"],
                payload.locale or resource_row["locale"],
                summary[:500],
                1 if payload.mandatory else 0,
                now.isoformat(),
                role,
            ),
        )
        update_id = int(cursor.lastrowid)

        stores_rows = db.execute("SELECT id, name, country FROM stores ORDER BY id ASC").fetchall()
        deliveries_seed = [
            (update_id, store["id"], now.isoformat(), None, None, "delivered")
            for store in stores_rows
        ]
        db.executemany(
            """
            INSERT INTO training_recipe_update_deliveries (
                update_id, store_id, delivered_at, acknowledged_at, acknowledged_by_role, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            deliveries_seed,
        )

    deliveries = [
        RecipeUpdateDeliveryRow(
            id=index + 1,
            update_id=update_id,
            store_id=store["id"],
            store_name=store["name"],
            country=store["country"],
            market=market_label(store["country"]),
            delivered_at=now,
            acknowledged_at=None,
            acknowledged_by_role=None,
            status="delivered",
        )
        for index, store in enumerate(stores_rows)
    ]

    summary_row = RecipeUpdateDistributionSummary(
        update_id=update_id,
        resource_id=resource_row["id"],
        resource_title=resource_row["title"],
        version=resource_row["version"],
        locale=payload.locale or resource_row["locale"],
        change_summary=summary[:500],
        mandatory=payload.mandatory,
        published_at=now,
        delivered_stores=len(deliveries),
        acknowledged_stores=0,
        pending_stores=len(deliveries),
    )

    write_audit_log(
        role,
        "publish_recipe_update",
        "success",
        payload.resource_id,
        f"update_id={update_id}, deliveries={len(deliveries)}",
    )

    return RecipeUpdatePublishResult(
        update=summary_row,
        deliveries=deliveries,
    )


@app.post("/api/v1/training/recipes/updates/{update_id}/acknowledge", response_model=RecipeUpdateDeliveryRow)
def acknowledge_recipe_update(
    update_id: int,
    payload: RecipeUpdateAcknowledgeCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> RecipeUpdateDeliveryRow:
    now = datetime.now(timezone.utc)

    with get_db() as db:
        row = db.execute(
            """
            SELECT d.id, d.update_id, d.store_id, st.name AS store_name, st.country,
                   d.delivered_at, d.acknowledged_at, d.acknowledged_by_role, d.status
            FROM training_recipe_update_deliveries d
            JOIN stores st ON st.id = d.store_id
            WHERE d.update_id = ? AND d.store_id = ?
            """,
            (update_id, payload.store_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="delivery not found for this update/store")

        db.execute(
            """
            UPDATE training_recipe_update_deliveries
            SET acknowledged_at = ?, acknowledged_by_role = ?, status = 'acknowledged'
            WHERE update_id = ? AND store_id = ?
            """,
            (now.isoformat(), role, update_id, payload.store_id),
        )

        updated = db.execute(
            """
            SELECT d.id, d.update_id, d.store_id, st.name AS store_name, st.country,
                   d.delivered_at, d.acknowledged_at, d.acknowledged_by_role, d.status
            FROM training_recipe_update_deliveries d
            JOIN stores st ON st.id = d.store_id
            WHERE d.update_id = ? AND d.store_id = ?
            """,
            (update_id, payload.store_id),
        ).fetchone()

    write_audit_log(
        role,
        "acknowledge_recipe_update",
        "success",
        f"update_id={update_id}",
        f"store_id={payload.store_id}",
    )

    return RecipeUpdateDeliveryRow(
        id=int(updated["id"]),
        update_id=int(updated["update_id"]),
        store_id=updated["store_id"],
        store_name=updated["store_name"],
        country=updated["country"],
        market=market_label(updated["country"]),
        delivered_at=parse_datetime_or_none(updated["delivered_at"]) or now,
        acknowledged_at=parse_datetime_or_none(updated["acknowledged_at"]),
        acknowledged_by_role=updated["acknowledged_by_role"],
        status=updated["status"],
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


@app.get("/api/v1/hr/employees", response_model=list[HrEmployeeSummary])
def get_hr_employees(
    country: Literal["CO", "US"] | None = Query(default=None),
    store_id: str | None = Query(default=None),
    employment_status: Literal["active", "terminated"] = Query(default="active"),
    limit: int = Query(default=200, ge=1, le=500),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[HrEmployeeSummary]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, full_name, country, store_id, role_title, employment_status, hire_date, terminated_at
            FROM hr_employees
            WHERE (? IS NULL OR country = ?)
              AND (? IS NULL OR store_id = ?)
              AND employment_status = ?
            ORDER BY country ASC, store_id ASC, id ASC
            LIMIT ?
            """,
            (country, country, store_id, store_id, employment_status, limit),
        ).fetchall()

    output = [
        HrEmployeeSummary(
            id=row["id"],
            full_name=row["full_name"],
            country=row["country"],
            store_id=row["store_id"],
            role_title=row["role_title"],
            employment_status=row["employment_status"],
            hire_date=parse_datetime_or_none(row["hire_date"]) or datetime.now(timezone.utc),
            terminated_at=parse_datetime_or_none(row["terminated_at"]),
        )
        for row in rows
    ]

    write_audit_log(
        role,
        "read_hr_employees",
        "success",
        f"country={country or 'ALL'}",
        f"store_id={store_id or 'ALL'}, status={employment_status}, rows={len(output)}",
    )
    return output


@app.get("/api/v1/hr/time-off/requests", response_model=list[HrTimeOffRequestRow])
def get_hr_time_off_requests(
    country: Literal["CO", "US"] | None = Query(default=None),
    store_id: str | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    request_type: Literal["vacation", "sick_leave", "personal_leave"] | None = Query(default=None),
    status: Literal["pending", "approved", "rejected"] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[HrTimeOffRequestRow]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT r.id, r.employee_id, e.full_name AS employee_name, r.store_id, r.country,
                   r.request_type, r.start_date, r.end_date, r.total_days, r.reason,
                   r.status, r.created_at, r.decided_at, r.decided_by_role, r.decision_note
            FROM hr_time_off_requests r
            JOIN hr_employees e ON e.id = r.employee_id
            WHERE (? IS NULL OR r.country = ?)
              AND (? IS NULL OR r.store_id = ?)
              AND (? IS NULL OR r.employee_id = ?)
              AND (? IS NULL OR r.request_type = ?)
              AND (? IS NULL OR r.status = ?)
            ORDER BY r.created_at DESC, r.id DESC
            LIMIT ?
            """,
            (
                country,
                country,
                store_id,
                store_id,
                employee_id,
                employee_id,
                request_type,
                request_type,
                status,
                status,
                limit,
            ),
        ).fetchall()

    output = [
        HrTimeOffRequestRow(
            id=int(row["id"]),
            employee_id=row["employee_id"],
            employee_name=row["employee_name"],
            store_id=row["store_id"],
            country=row["country"],
            market=market_label(row["country"]),
            request_type=row["request_type"],
            start_date=parse_datetime_or_none(row["start_date"]) or datetime.now(timezone.utc),
            end_date=parse_datetime_or_none(row["end_date"]) or datetime.now(timezone.utc),
            total_days=int(row["total_days"]),
            reason=row["reason"],
            status=row["status"],
            created_at=parse_datetime_or_none(row["created_at"]) or datetime.now(timezone.utc),
            decided_at=parse_datetime_or_none(row["decided_at"]),
            decided_by_role=row["decided_by_role"],
            decision_note=row["decision_note"],
        )
        for row in rows
    ]

    write_audit_log(
        role,
        "read_hr_time_off_requests",
        "success",
        f"country={country or 'ALL'}",
        f"status={status or 'ALL'}, rows={len(output)}",
    )
    return output


@app.post("/api/v1/hr/time-off/requests", response_model=HrTimeOffRequestRow, status_code=201)
def create_hr_time_off_request(
    payload: HrTimeOffRequestCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> HrTimeOffRequestRow:
    now = datetime.now(timezone.utc)
    start_date = parse_iso_date(payload.start_date, "start_date")
    end_date = parse_iso_date(payload.end_date, "end_date")
    total_days = calculate_requested_days(start_date, end_date)
    clean_reason = payload.reason.strip()

    if total_days > 30:
        raise HTTPException(status_code=400, detail="total requested days cannot exceed 30")
    if not clean_reason:
        raise HTTPException(status_code=400, detail="reason must not be empty")

    with get_db() as db:
        employee_row = db.execute(
            """
            SELECT id, full_name, country, store_id, employment_status
            FROM hr_employees
            WHERE id = ?
            """,
            (payload.employee_id,),
        ).fetchone()

        if employee_row is None:
            raise HTTPException(status_code=404, detail="employee not found")
        if employee_row["employment_status"] != "active":
            raise HTTPException(status_code=400, detail="employee is not active")

        country_code = employee_row["country"]
        if payload.request_type == "vacation":
            min_notice_days = 15 if country_code == "CO" else 10
            notice_days = int((start_date - now).days)
            if notice_days < min_notice_days:
                raise HTTPException(
                    status_code=400,
                    detail=f"vacation requests in {country_code} require at least {min_notice_days} days notice",
                )

        cursor = db.execute(
            """
            INSERT INTO hr_time_off_requests (
                employee_id, store_id, country, request_type, start_date, end_date, total_days,
                reason, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                payload.employee_id,
                employee_row["store_id"],
                country_code,
                payload.request_type,
                payload.start_date,
                payload.end_date,
                total_days,
                clean_reason[:300],
                now.isoformat(),
            ),
        )
        request_id = int(cursor.lastrowid)

        created_row = db.execute(
            """
            SELECT r.id, r.employee_id, e.full_name AS employee_name, r.store_id, r.country,
                   r.request_type, r.start_date, r.end_date, r.total_days, r.reason,
                   r.status, r.created_at, r.decided_at, r.decided_by_role, r.decision_note
            FROM hr_time_off_requests r
            JOIN hr_employees e ON e.id = r.employee_id
            WHERE r.id = ?
            """,
            (request_id,),
        ).fetchone()

    write_audit_log(
        role,
        "create_hr_time_off_request",
        "success",
        payload.employee_id,
        f"request_id={request_id}, type={payload.request_type}, days={total_days}",
    )

    return HrTimeOffRequestRow(
        id=request_id,
        employee_id=created_row["employee_id"],
        employee_name=created_row["employee_name"],
        store_id=created_row["store_id"],
        country=created_row["country"],
        market=market_label(created_row["country"]),
        request_type=created_row["request_type"],
        start_date=parse_datetime_or_none(created_row["start_date"]) or now,
        end_date=parse_datetime_or_none(created_row["end_date"]) or now,
        total_days=int(created_row["total_days"]),
        reason=created_row["reason"],
        status=created_row["status"],
        created_at=parse_datetime_or_none(created_row["created_at"]) or now,
        decided_at=None,
        decided_by_role=None,
        decision_note=None,
    )


@app.post("/api/v1/hr/time-off/requests/{request_id}/action", response_model=HrTimeOffRequestRow)
def action_hr_time_off_request(
    request_id: int,
    payload: HrTimeOffRequestActionCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> HrTimeOffRequestRow:
    now = datetime.now(timezone.utc)
    decision_note = (payload.note or "").strip() or None

    with get_db() as db:
        row = db.execute(
            """
            SELECT r.id, r.employee_id, e.full_name AS employee_name, r.store_id, r.country,
                   r.request_type, r.start_date, r.end_date, r.total_days, r.reason,
                   r.status, r.created_at, r.decided_at, r.decided_by_role, r.decision_note
            FROM hr_time_off_requests r
            JOIN hr_employees e ON e.id = r.employee_id
            WHERE r.id = ?
            """,
            (request_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="time-off request not found")
        if row["status"] != "pending":
            raise HTTPException(status_code=400, detail="only pending requests can be updated")

        db.execute(
            """
            UPDATE hr_time_off_requests
            SET status = ?, decided_at = ?, decided_by_role = ?, decision_note = ?
            WHERE id = ?
            """,
            (payload.status, now.isoformat(), role, (decision_note or "")[:300] if decision_note else None, request_id),
        )

        if payload.status == "approved":
            db.execute(
                """
                INSERT INTO hr_absence_events (
                    employee_id, country, absence_type, start_date, end_date, total_days, source_request_id, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["employee_id"],
                    row["country"],
                    row["request_type"],
                    row["start_date"],
                    row["end_date"],
                    float(row["total_days"]),
                    request_id,
                    now.isoformat(),
                ),
            )

        updated_row = db.execute(
            """
            SELECT r.id, r.employee_id, e.full_name AS employee_name, r.store_id, r.country,
                   r.request_type, r.start_date, r.end_date, r.total_days, r.reason,
                   r.status, r.created_at, r.decided_at, r.decided_by_role, r.decision_note
            FROM hr_time_off_requests r
            JOIN hr_employees e ON e.id = r.employee_id
            WHERE r.id = ?
            """,
            (request_id,),
        ).fetchone()

    write_audit_log(
        role,
        "action_hr_time_off_request",
        "success",
        f"request_id={request_id}",
        f"status={payload.status}",
    )

    return HrTimeOffRequestRow(
        id=int(updated_row["id"]),
        employee_id=updated_row["employee_id"],
        employee_name=updated_row["employee_name"],
        store_id=updated_row["store_id"],
        country=updated_row["country"],
        market=market_label(updated_row["country"]),
        request_type=updated_row["request_type"],
        start_date=parse_datetime_or_none(updated_row["start_date"]) or now,
        end_date=parse_datetime_or_none(updated_row["end_date"]) or now,
        total_days=int(updated_row["total_days"]),
        reason=updated_row["reason"],
        status=updated_row["status"],
        created_at=parse_datetime_or_none(updated_row["created_at"]) or now,
        decided_at=parse_datetime_or_none(updated_row["decided_at"]),
        decided_by_role=updated_row["decided_by_role"],
        decision_note=updated_row["decision_note"],
    )


@app.get("/api/v1/hr/onboarding/cases", response_model=list[HrOnboardingCaseRow])
def get_hr_onboarding_cases(
    country: Literal["CO", "US"] | None = Query(default=None),
    status: Literal["active", "completed", "on_hold"] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[HrOnboardingCaseRow]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT oc.id, oc.employee_id, e.full_name AS employee_name, oc.store_id, oc.country,
                   oc.position_title, oc.mentor_name, oc.status, oc.completed_steps, oc.total_steps,
                   oc.last_step_key, oc.started_at, oc.target_completion_at, oc.last_updated_at, oc.notes
            FROM hr_onboarding_cases oc
            JOIN hr_employees e ON e.id = oc.employee_id
            WHERE (? IS NULL OR oc.country = ?)
              AND (? IS NULL OR oc.status = ?)
            ORDER BY oc.last_updated_at DESC, oc.id DESC
            LIMIT ?
            """,
            (country, country, status, status, limit),
        ).fetchall()

    output = [
        HrOnboardingCaseRow(
            id=int(row["id"]),
            employee_id=row["employee_id"],
            employee_name=row["employee_name"],
            store_id=row["store_id"],
            country=row["country"],
            market=market_label(row["country"]),
            position_title=row["position_title"],
            mentor_name=row["mentor_name"],
            status=row["status"],
            completed_steps=int(row["completed_steps"]),
            total_steps=int(row["total_steps"]),
            last_step_key=row["last_step_key"],
            started_at=parse_datetime_or_none(row["started_at"]) or datetime.now(timezone.utc),
            target_completion_at=parse_datetime_or_none(row["target_completion_at"]) or datetime.now(timezone.utc),
            last_updated_at=parse_datetime_or_none(row["last_updated_at"]) or datetime.now(timezone.utc),
            notes=row["notes"],
        )
        for row in rows
    ]

    write_audit_log(
        role,
        "read_hr_onboarding_cases",
        "success",
        f"country={country or 'ALL'}",
        f"status={status or 'ALL'}, rows={len(output)}",
    )
    return output


@app.post("/api/v1/hr/onboarding/cases/start", response_model=HrOnboardingCaseRow, status_code=201)
def start_hr_onboarding_case(
    payload: HrOnboardingCaseCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> HrOnboardingCaseRow:
    now = datetime.now(timezone.utc)
    started_at = parse_iso_date(payload.start_date, "start_date") if payload.start_date else now
    target_completion_at = started_at + timedelta(days=14)

    with get_db() as db:
        employee_row = db.execute(
            """
            SELECT id, full_name, country, store_id, employment_status
            FROM hr_employees
            WHERE id = ?
            """,
            (payload.employee_id,),
        ).fetchone()
        if employee_row is None:
            raise HTTPException(status_code=404, detail="employee not found")
        if employee_row["employment_status"] != "active":
            raise HTTPException(status_code=400, detail="employee is not active")

        active_case = db.execute(
            """
            SELECT 1 FROM hr_onboarding_cases
            WHERE employee_id = ? AND status = 'active'
            """,
            (payload.employee_id,),
        ).fetchone()
        if active_case is not None:
            raise HTTPException(status_code=409, detail="employee already has an active onboarding case")

        cursor = db.execute(
            """
            INSERT INTO hr_onboarding_cases (
                employee_id, store_id, country, position_title, mentor_name, status, completed_steps,
                total_steps, last_step_key, started_at, target_completion_at, last_updated_at, notes
            ) VALUES (?, ?, ?, ?, ?, 'active', 1, 4, 'documents', ?, ?, ?, ?)
            """,
            (
                payload.employee_id,
                employee_row["store_id"],
                employee_row["country"],
                payload.position_title[:120],
                payload.mentor_name[:120],
                started_at.isoformat(),
                target_completion_at.isoformat(),
                now.isoformat(),
                (payload.notes or "").strip()[:400] if payload.notes else None,
            ),
        )
        case_id = int(cursor.lastrowid)

        case_row = db.execute(
            """
            SELECT oc.id, oc.employee_id, e.full_name AS employee_name, oc.store_id, oc.country,
                   oc.position_title, oc.mentor_name, oc.status, oc.completed_steps, oc.total_steps,
                   oc.last_step_key, oc.started_at, oc.target_completion_at, oc.last_updated_at, oc.notes
            FROM hr_onboarding_cases oc
            JOIN hr_employees e ON e.id = oc.employee_id
            WHERE oc.id = ?
            """,
            (case_id,),
        ).fetchone()

    write_audit_log(
        role,
        "start_hr_onboarding_case",
        "success",
        payload.employee_id,
        f"case_id={case_id}",
    )

    return HrOnboardingCaseRow(
        id=case_id,
        employee_id=case_row["employee_id"],
        employee_name=case_row["employee_name"],
        store_id=case_row["store_id"],
        country=case_row["country"],
        market=market_label(case_row["country"]),
        position_title=case_row["position_title"],
        mentor_name=case_row["mentor_name"],
        status=case_row["status"],
        completed_steps=int(case_row["completed_steps"]),
        total_steps=int(case_row["total_steps"]),
        last_step_key=case_row["last_step_key"],
        started_at=parse_datetime_or_none(case_row["started_at"]) or now,
        target_completion_at=parse_datetime_or_none(case_row["target_completion_at"]) or now,
        last_updated_at=parse_datetime_or_none(case_row["last_updated_at"]) or now,
        notes=case_row["notes"],
    )


@app.post("/api/v1/hr/onboarding/cases/{case_id}/advance", response_model=HrOnboardingCaseRow)
def advance_hr_onboarding_case(
    case_id: int,
    payload: HrOnboardingAdvanceCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> HrOnboardingCaseRow:
    now = datetime.now(timezone.utc)

    with get_db() as db:
        row = db.execute(
            """
            SELECT oc.id, oc.employee_id, e.full_name AS employee_name, oc.store_id, oc.country,
                   oc.position_title, oc.mentor_name, oc.status, oc.completed_steps, oc.total_steps,
                   oc.last_step_key, oc.started_at, oc.target_completion_at, oc.last_updated_at, oc.notes
            FROM hr_onboarding_cases oc
            JOIN hr_employees e ON e.id = oc.employee_id
            WHERE oc.id = ?
            """,
            (case_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="onboarding case not found")
        if row["status"] != "active":
            raise HTTPException(status_code=400, detail="only active onboarding cases can be advanced")

        current_steps = int(row["completed_steps"])
        total_steps = int(row["total_steps"])
        next_steps = min(current_steps + 1, total_steps)
        new_status = "completed" if next_steps >= total_steps else "active"

        notes_suffix = (payload.note or "").strip()
        merged_notes = row["notes"]
        if notes_suffix:
            merged_notes = f"{row['notes']} | {notes_suffix}" if row["notes"] else notes_suffix

        db.execute(
            """
            UPDATE hr_onboarding_cases
            SET completed_steps = ?, status = ?, last_step_key = ?, last_updated_at = ?, notes = ?
            WHERE id = ?
            """,
            (
                next_steps,
                new_status,
                payload.step_key,
                now.isoformat(),
                (merged_notes or "")[:400] if merged_notes else None,
                case_id,
            ),
        )

        updated_row = db.execute(
            """
            SELECT oc.id, oc.employee_id, e.full_name AS employee_name, oc.store_id, oc.country,
                   oc.position_title, oc.mentor_name, oc.status, oc.completed_steps, oc.total_steps,
                   oc.last_step_key, oc.started_at, oc.target_completion_at, oc.last_updated_at, oc.notes
            FROM hr_onboarding_cases oc
            JOIN hr_employees e ON e.id = oc.employee_id
            WHERE oc.id = ?
            """,
            (case_id,),
        ).fetchone()

    write_audit_log(
        role,
        "advance_hr_onboarding_case",
        "success",
        f"case_id={case_id}",
        f"step={payload.step_key}, status={updated_row['status']}",
    )

    return HrOnboardingCaseRow(
        id=int(updated_row["id"]),
        employee_id=updated_row["employee_id"],
        employee_name=updated_row["employee_name"],
        store_id=updated_row["store_id"],
        country=updated_row["country"],
        market=market_label(updated_row["country"]),
        position_title=updated_row["position_title"],
        mentor_name=updated_row["mentor_name"],
        status=updated_row["status"],
        completed_steps=int(updated_row["completed_steps"]),
        total_steps=int(updated_row["total_steps"]),
        last_step_key=updated_row["last_step_key"],
        started_at=parse_datetime_or_none(updated_row["started_at"]) or now,
        target_completion_at=parse_datetime_or_none(updated_row["target_completion_at"]) or now,
        last_updated_at=parse_datetime_or_none(updated_row["last_updated_at"]) or now,
        notes=updated_row["notes"],
    )


@app.get("/api/v1/hr/kpis/overview", response_model=HrKpiOverviewResponse)
def get_hr_kpis_overview(
    days: int = Query(default=90, ge=30, le=365),
    country: Literal["CO", "US"] | None = Query(default=None),
    role: str = Depends(require_roles({"executive", "operations", "admin"})),
) -> HrKpiOverviewResponse:
    now = datetime.now(timezone.utc)
    start_at = now - timedelta(days=days)

    with get_db() as db:
        employees_rows = db.execute(
            """
            SELECT id, country, employment_status, terminated_at
            FROM hr_employees
            WHERE (? IS NULL OR country = ?)
            """,
            (country, country),
        ).fetchall()
        absences_rows = db.execute(
            """
            SELECT country, total_days, recorded_at
            FROM hr_absence_events
            WHERE recorded_at >= ? AND recorded_at < ?
              AND (? IS NULL OR country = ?)
            """,
            (start_at.isoformat(), now.isoformat(), country, country),
        ).fetchall()
        vacancies_rows = db.execute(
            """
            SELECT country, opened_at, filled_at, status
            FROM hr_vacancies
            WHERE opened_at >= ? AND opened_at < ?
              AND (? IS NULL OR country = ?)
            """,
            (start_at.isoformat(), now.isoformat(), country, country),
        ).fetchall()
        requests_rows = db.execute(
            """
            SELECT country, status
            FROM hr_time_off_requests
            WHERE created_at >= ? AND created_at < ?
              AND (? IS NULL OR country = ?)
            """,
            (start_at.isoformat(), now.isoformat(), country, country),
        ).fetchall()
        onboarding_rows = db.execute(
            """
            SELECT country, status
            FROM hr_onboarding_cases
            WHERE (? IS NULL OR country = ?)
            """,
            (country, country),
        ).fetchall()

    countries: list[str]
    if country is not None:
        countries = [country]
    else:
        countries = sorted({row["country"] for row in employees_rows} | {"CO", "US"})

    employee_stats: dict[str, dict[str, float | int]] = {
        code: {"active": 0, "total": 0, "terminations": 0} for code in countries
    }
    for row in employees_rows:
        code = row["country"]
        if code not in employee_stats:
            employee_stats[code] = {"active": 0, "total": 0, "terminations": 0}
        employee_stats[code]["total"] += 1
        if row["employment_status"] == "active":
            employee_stats[code]["active"] += 1

        terminated_at = parse_datetime_or_none(row["terminated_at"])
        if terminated_at is not None and start_at <= terminated_at < now:
            employee_stats[code]["terminations"] += 1

    absent_days_by_country: dict[str, float] = {code: 0.0 for code in countries}
    for row in absences_rows:
        code = row["country"]
        absent_days_by_country[code] = absent_days_by_country.get(code, 0.0) + float(row["total_days"])

    vacancy_duration_days: dict[str, list[float]] = {code: [] for code in countries}
    open_vacancies_by_country: dict[str, int] = {code: 0 for code in countries}
    for row in vacancies_rows:
        code = row["country"]
        if row["status"] == "open":
            open_vacancies_by_country[code] = open_vacancies_by_country.get(code, 0) + 1
        filled_at = parse_datetime_or_none(row["filled_at"])
        opened_at = parse_datetime_or_none(row["opened_at"])
        if opened_at is not None and filled_at is not None and filled_at >= opened_at:
            vacancy_duration_days.setdefault(code, []).append((filled_at - opened_at).days)

    pending_requests_by_country: dict[str, int] = {code: 0 for code in countries}
    for row in requests_rows:
        if row["status"] == "pending":
            code = row["country"]
            pending_requests_by_country[code] = pending_requests_by_country.get(code, 0) + 1

    active_onboarding_by_country: dict[str, int] = {code: 0 for code in countries}
    for row in onboarding_rows:
        if row["status"] == "active":
            code = row["country"]
            active_onboarding_by_country[code] = active_onboarding_by_country.get(code, 0) + 1

    by_country: list[HrKpiCountrySummary] = []
    for code in countries:
        active_headcount = int(employee_stats.get(code, {}).get("active", 0))
        total_headcount = int(employee_stats.get(code, {}).get("total", 0))
        terminations = int(employee_stats.get(code, {}).get("terminations", 0))
        average_headcount = max(active_headcount + (terminations / 2), 1)
        turnover_rate_pct = (terminations / average_headcount) * 100

        absent_days = float(absent_days_by_country.get(code, 0.0))
        expected_work_days = max(active_headcount * days, 1)
        absenteeism_rate_pct = (absent_days / expected_work_days) * 100

        durations = vacancy_duration_days.get(code, [])
        avg_time_to_fill_days = (sum(durations) / len(durations)) if durations else 0.0

        by_country.append(
            HrKpiCountrySummary(
                country=code,
                market=market_label(code),
                active_headcount=active_headcount,
                total_headcount=total_headcount,
                terminations=terminations,
                turnover_rate_pct=round(turnover_rate_pct, 2),
                absent_days=round(absent_days, 2),
                absenteeism_rate_pct=round(absenteeism_rate_pct, 3),
                open_vacancies=int(open_vacancies_by_country.get(code, 0)),
                avg_time_to_fill_days=round(avg_time_to_fill_days, 2),
                pending_time_off_requests=int(pending_requests_by_country.get(code, 0)),
                active_onboarding_cases=int(active_onboarding_by_country.get(code, 0)),
            )
        )

    total_active_headcount = sum(item.active_headcount for item in by_country)
    total_terminations = sum(item.terminations for item in by_country)
    total_absent_days = sum(item.absent_days for item in by_country)
    overall_expected_work_days = max(total_active_headcount * days, 1)
    overall_avg_headcount = max(total_active_headcount + (total_terminations / 2), 1)

    overall_turnover_rate_pct = (total_terminations / overall_avg_headcount) * 100
    overall_absenteeism_rate_pct = (total_absent_days / overall_expected_work_days) * 100

    avg_fill_values = [item.avg_time_to_fill_days for item in by_country if item.avg_time_to_fill_days > 0]
    overall_avg_time_to_fill_days = sum(avg_fill_values) / len(avg_fill_values) if avg_fill_values else 0.0

    write_audit_log(
        role,
        "read_hr_kpis_overview",
        "success",
        f"country={country or 'ALL'}",
        f"days={days}, active_headcount={total_active_headcount}, terminations={total_terminations}",
    )

    return HrKpiOverviewResponse(
        period_days=days,
        country=country,
        generated_at=now,
        total_active_headcount=total_active_headcount,
        total_terminations=total_terminations,
        overall_turnover_rate_pct=round(overall_turnover_rate_pct, 2),
        overall_absenteeism_rate_pct=round(overall_absenteeism_rate_pct, 3),
        overall_avg_time_to_fill_days=round(overall_avg_time_to_fill_days, 2),
        by_country=by_country,
    )


@app.get("/api/v1/executive/ask", response_model=ExecutiveAskResponse)
def ask_executive_metrics(
    question: str = Query(..., min_length=5),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    role: str = Depends(require_roles({"executive", "admin"})),
) -> ExecutiveAskResponse:
    now = datetime.now(timezone.utc)
    normalized = question.strip().lower()

    def detect_country_from_question(text: str) -> Literal["CO", "US"] | None:
        if "florida" in text or "usa" in text or "us" in text or "eeuu" in text:
            return "US"
        if "colombia" in text or "co" in text:
            return "CO"
        return None

    def sales_answer_scope_label(country_code: Literal["CO", "US"] | None) -> str:
        if country_code == "CO":
            return "Colombia"
        if country_code == "US":
            return "Florida"
        return "Cadena"

    with get_db() as db:
        asks_week_sales = (
            any(term in normalized for term in ("vendimos", "ventas", "sell", "sold"))
            and any(term in normalized for term in ("semana", "week"))
        )
        if asks_week_sales:
            requested_country = detect_country_from_question(normalized)
            asks_compare = "vs" in normalized or ("florida" in normalized and "colombia" in normalized)
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

            total_chain = totals_by_country["CO"] + totals_by_country["US"]

            if asks_compare:
                answer = (
                    f"Semana actual: Colombia={totals_by_country['CO']:.2f} {currency}, "
                    f"Florida={totals_by_country['US']:.2f} {currency}, "
                    f"Cadena={total_chain:.2f} {currency}."
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

            if requested_country is not None:
                scope_label = sales_answer_scope_label(requested_country)
                answer = f"Semana actual en {scope_label}: {totals_by_country[requested_country]:.2f} {currency}."
                write_audit_log(
                    role,
                    "executive_ask",
                    "success",
                    "sales_week_country_single",
                    f"country={requested_country}, currency={currency}",
                )
                return ExecutiveAskResponse(
                    question=question,
                    answer=answer,
                    sources=["sales_events", "stores", "rule:sales_week_country_single"],
                    requires_follow_up=False,
                    follow_up_questions=[],
                    generated_at=now,
                )

            answer = f"Semana actual de cadena: {total_chain:.2f} {currency}."
            write_audit_log(
                role,
                "executive_ask",
                "success",
                "sales_week_chain_total",
                f"currency={currency}",
            )
            return ExecutiveAskResponse(
                question=question,
                answer=answer,
                sources=["sales_events", "stores", "rule:sales_week_chain_total"],
                requires_follow_up=False,
                follow_up_questions=[],
                generated_at=now,
            )

        asks_top_ticket = (
            "ticket" in normalized
            and ("alto" in normalized or "highest" in normalized or "mayor" in normalized)
            and ("mes" in normalized or "month" in normalized)
        )
        if asks_top_ticket:
            requested_country = detect_country_from_question(normalized)
            start_at = period_start("month")
            end_at = now
            rows = db.execute(
                """
                SELECT st.id, st.name, st.country, se.total_amount, se.currency
                FROM sales_events se
                JOIN stores st ON st.id = se.store_id
                WHERE se.sold_at >= ? AND se.sold_at < ?
                  AND (? IS NULL OR st.country = ?)
                ORDER BY st.id
                """,
                (start_at.isoformat(), end_at.isoformat(), requested_country, requested_country),
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

            if best_store_name == "N/A":
                scope_label = sales_answer_scope_label(requested_country)
                return ExecutiveAskResponse(
                    question=question,
                    answer=f"informacion insuficiente: no hay ventas del mes para {scope_label}.",
                    sources=["sales_events", "stores", "rule:top_monthly_average_ticket_store"],
                    requires_follow_up=True,
                    follow_up_questions=[
                        "Cuanto vendimos esta semana en Florida?",
                        "Que local tiene el ticket promedio mas alto este mes en toda la cadena?",
                    ],
                    generated_at=now,
                )

            answer = (
                f"Local con mayor ticket promedio mensual: {best_store_name} "
                f"({best_market}) con {best_avg:.2f} {currency}."
            )
            write_audit_log(
                role,
                "executive_ask",
                "success",
                "top_monthly_average_ticket_store",
                f"country={requested_country or 'ALL'}, currency={currency}",
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
        opening_hours_only=True,
        reference_at=None,
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


@app.get("/api/v1/suppliers/prices", response_model=list[SupplierPriceRow])
def get_supplier_prices(
    country: Literal["CO", "US"] | None = Query(default=None),
    supplier_id: str | None = Query(default=None),
    sku: str | None = Query(default=None),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    limit: int = Query(default=100, ge=1, le=500),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[SupplierPriceRow]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT supplier_id, supplier_name, sku, item_name, country, currency, price, valid_from
            FROM supplier_prices
            WHERE (? IS NULL OR country = ?)
              AND (? IS NULL OR supplier_id = ?)
              AND (? IS NULL OR sku = ?)
            ORDER BY valid_from DESC
            LIMIT ?
            """,
            (country, country, supplier_id, supplier_id, sku, sku, limit),
        ).fetchall()

    output: list[SupplierPriceRow] = []
    for row in rows:
        valid_from = parse_datetime_or_none(row["valid_from"]) or datetime.now(timezone.utc)
        output.append(
            SupplierPriceRow(
                supplier_id=row["supplier_id"],
                supplier_name=row["supplier_name"],
                sku=row["sku"],
                item_name=row["item_name"],
                country=row["country"],
                currency=currency,
                price=round(convert_amount(row["price"], row["currency"], currency), 4),
                valid_from=valid_from,
            )
        )

    write_audit_log(
        role,
        "read_supplier_prices",
        "success",
        f"country={country or 'ALL'}",
        f"supplier={supplier_id or 'ALL'}, sku={sku or 'ALL'}, rows={len(output)}",
    )
    return output


@app.get("/api/v1/suppliers/price-alerts", response_model=list[SupplierPriceAlert])
def get_supplier_price_alerts(
    threshold_pct: float = Query(default=5.0, ge=0.1, le=100.0),
    country: Literal["CO", "US"] | None = Query(default=None),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> list[SupplierPriceAlert]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT supplier_id, supplier_name, sku, item_name, country, currency, price, valid_from
            FROM supplier_prices
            WHERE (? IS NULL OR country = ?)
            ORDER BY supplier_id ASC, sku ASC, country ASC, valid_from DESC
            """,
            (country, country),
        ).fetchall()

    top_two_by_key: dict[tuple[str, str, str], list[Row]] = {}
    for row in rows:
        key = (row["supplier_id"], row["sku"], row["country"])
        if key not in top_two_by_key:
            top_two_by_key[key] = []
        if len(top_two_by_key[key]) < 2:
            top_two_by_key[key].append(row)

    alerts: list[SupplierPriceAlert] = []
    for pair in top_two_by_key.values():
        if len(pair) < 2:
            continue
        current_row, previous_row = pair[0], pair[1]
        previous_price = convert_amount(previous_row["price"], previous_row["currency"], currency)
        current_price = convert_amount(current_row["price"], current_row["currency"], currency)
        if previous_price <= 0:
            continue
        change_pct = ((current_price - previous_price) / previous_price) * 100
        if change_pct < threshold_pct:
            continue

        valid_from = parse_datetime_or_none(current_row["valid_from"]) or datetime.now(timezone.utc)
        alerts.append(
            SupplierPriceAlert(
                supplier_id=current_row["supplier_id"],
                supplier_name=current_row["supplier_name"],
                sku=current_row["sku"],
                item_name=current_row["item_name"],
                country=current_row["country"],
                currency=currency,
                previous_price=round(previous_price, 4),
                current_price=round(current_price, 4),
                change_pct=round(change_pct, 2),
                valid_from=valid_from,
            )
        )

    write_audit_log(
        role,
        "read_supplier_price_alerts",
        "success",
        f"country={country or 'ALL'}",
        f"threshold_pct={threshold_pct}, alerts={len(alerts)}",
    )
    return alerts


@app.get("/api/v1/suppliers/purchases/consolidated", response_model=SupplierPurchasesConsolidatedResponse)
def get_supplier_purchases_consolidated(
    days: int = Query(default=30, ge=7, le=365),
    country: Literal["CO", "US"] | None = Query(default=None),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    role: str = Depends(require_roles({"operations", "executive", "admin"})),
) -> SupplierPurchasesConsolidatedResponse:
    now = datetime.now(timezone.utc)
    start_at = now - timedelta(days=days)

    with get_db() as db:
        supplier_rows = db.execute(
            """
            SELECT supplier_id, supplier_name, country, sku, currency, price
            FROM supplier_prices
            WHERE (? IS NULL OR country = ?)
            ORDER BY country ASC, sku ASC, valid_from DESC
            """,
            (country, country),
        ).fetchall()

        receipts_rows = db.execute(
            """
            SELECT ir.store_id, st.country, ir.sku, ir.received_qty, ir.unit_cost, ir.currency, ir.received_at
            FROM inventory_receipts ir
            JOIN stores st ON st.id = ir.store_id
            WHERE ir.received_at >= ? AND ir.received_at < ?
              AND (? IS NULL OR st.country = ?)
            ORDER BY ir.received_at DESC
            """,
            (start_at.isoformat(), now.isoformat(), country, country),
        ).fetchall()

    latest_supplier_by_country_supplier_sku: dict[tuple[str, str], tuple[str, str, str, float]] = {}
    latest_supplier_by_country_local_sku: dict[tuple[str, str], tuple[str, str, str, float]] = {}

    for row in supplier_rows:
        key_supplier_sku = (row["country"], row["sku"])
        if key_supplier_sku not in latest_supplier_by_country_supplier_sku:
            latest_supplier_by_country_supplier_sku[key_supplier_sku] = (
                row["supplier_id"],
                row["supplier_name"],
                row["currency"],
                float(row["price"]),
            )

    for country_code, sku_map in SUPPLIER_SKU_BY_COUNTRY.items():
        for local_sku, supplier_sku in sku_map.items():
            pair = latest_supplier_by_country_supplier_sku.get((country_code, supplier_sku))
            if pair is not None:
                latest_supplier_by_country_local_sku[(country_code, local_sku)] = pair

    by_supplier_acc: dict[tuple[str, str], dict[str, float | int | str]] = {}
    by_country_acc: dict[str, dict[str, float | int | set[str]]] = {}

    for row in receipts_rows:
        country_code = row["country"]
        local_sku = str(row["sku"]).upper()
        supplier_meta = latest_supplier_by_country_local_sku.get((country_code, local_sku))
        if supplier_meta is None:
            supplier_id = f"unknown-{country_code}-{local_sku}"
            supplier_name = f"Proveedor no mapeado ({local_sku})"
            fallback_currency = row["currency"]
            fallback_unit_cost = float(row["unit_cost"]) if row["unit_cost"] is not None else 0.0
        else:
            supplier_id, supplier_name, fallback_currency, fallback_unit_cost = supplier_meta

        unit_cost_source = float(row["unit_cost"]) if row["unit_cost"] is not None else float(fallback_unit_cost)
        unit_cost_currency = row["currency"] if row["unit_cost"] is not None else fallback_currency
        converted_unit_cost = convert_amount(unit_cost_source, unit_cost_currency, currency)

        received_qty = float(row["received_qty"])
        spend = converted_unit_cost * received_qty

        supplier_key = (country_code, supplier_id)
        if supplier_key not in by_supplier_acc:
            by_supplier_acc[supplier_key] = {
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "country": country_code,
                "market": market_label(country_code),
                "receipts_count": 0,
                "total_qty": 0.0,
                "total_spend": 0.0,
                "unit_cost_weighted_sum": 0.0,
            }

        by_supplier_acc[supplier_key]["receipts_count"] += 1
        by_supplier_acc[supplier_key]["total_qty"] += received_qty
        by_supplier_acc[supplier_key]["total_spend"] += spend
        by_supplier_acc[supplier_key]["unit_cost_weighted_sum"] += converted_unit_cost * received_qty

        if country_code not in by_country_acc:
            by_country_acc[country_code] = {
                "receipts_count": 0,
                "total_spend": 0.0,
                "suppliers": set(),
            }

        by_country_acc[country_code]["receipts_count"] += 1
        by_country_acc[country_code]["total_spend"] += spend
        by_country_acc[country_code]["suppliers"].add(supplier_id)

    by_country: list[SupplierPurchasesCountrySummary] = []
    for country_code in sorted(by_country_acc.keys()):
        acc = by_country_acc[country_code]
        by_country.append(
            SupplierPurchasesCountrySummary(
                country=country_code,
                market=market_label(country_code),
                receipts_count=int(acc["receipts_count"]),
                suppliers_count=len(acc["suppliers"]),
                total_spend=round(float(acc["total_spend"]), 2),
                currency=currency,
            )
        )

    by_supplier: list[SupplierPurchasesSupplierSummary] = []
    for acc in sorted(by_supplier_acc.values(), key=lambda x: float(x["total_spend"]), reverse=True):
        total_qty = float(acc["total_qty"])
        weighted_sum = float(acc["unit_cost_weighted_sum"])
        avg_unit_cost = (weighted_sum / total_qty) if total_qty > 0 else 0.0
        by_supplier.append(
            SupplierPurchasesSupplierSummary(
                supplier_id=str(acc["supplier_id"]),
                supplier_name=str(acc["supplier_name"]),
                country=str(acc["country"]),
                market=str(acc["market"]),
                receipts_count=int(acc["receipts_count"]),
                total_qty=round(total_qty, 3),
                total_spend=round(float(acc["total_spend"]), 2),
                average_unit_cost=round(avg_unit_cost, 4),
                currency=currency,
            )
        )

    total_spend = round(sum(item.total_spend for item in by_country), 2)
    total_receipts = sum(item.receipts_count for item in by_country)
    total_suppliers = len(by_supplier)

    write_audit_log(
        role,
        "read_supplier_purchases_consolidated",
        "success",
        f"country={country or 'ALL'}",
        f"days={days}, receipts={total_receipts}, suppliers={total_suppliers}, currency={currency}",
    )

    return SupplierPurchasesConsolidatedResponse(
        period_days=days,
        currency=currency,
        generated_at=now,
        total_receipts=total_receipts,
        total_suppliers=total_suppliers,
        total_spend=total_spend,
        by_country=by_country,
        by_supplier=by_supplier,
    )


@app.get("/api/v1/customers/summary", response_model=list[CustomerSummary])
def get_customers_summary(
    country: Literal["CO", "US"] | None = Query(default=None),
    role: str = Depends(require_roles({"executive", "operations", "admin"})),
) -> list[CustomerSummary]:
    threshold = datetime.now(timezone.utc) - timedelta(days=30)
    with get_db() as db:
        rows = db.execute(
            """
            SELECT country, points_balance, last_order_at
            FROM customers
            WHERE (? IS NULL OR country = ?)
            """,
            (country, country),
        ).fetchall()

    grouped: dict[str, dict[str, float | int]] = {}
    for row in rows:
        key = row["country"]
        if key not in grouped:
            grouped[key] = {"count": 0, "active_30d": 0, "points_sum": 0.0}
        grouped[key]["count"] += 1
        grouped[key]["points_sum"] += float(row["points_balance"])
        last_order_at = parse_datetime_or_none(row["last_order_at"])
        if last_order_at is not None and last_order_at >= threshold:
            grouped[key]["active_30d"] += 1

    output: list[CustomerSummary] = []
    for key in sorted(grouped.keys()):
        count = int(grouped[key]["count"])
        avg_points = float(grouped[key]["points_sum"]) / count if count > 0 else 0.0
        output.append(
            CustomerSummary(
                country=key,
                total_customers=count,
                active_customers_30d=int(grouped[key]["active_30d"]),
                average_points=round(avg_points, 2),
            )
        )

    write_audit_log(
        role,
        "read_customers_summary",
        "success",
        f"country={country or 'ALL'}",
        f"rows={len(output)}",
    )
    return output


@app.get("/api/v1/customers/{customer_id}", response_model=CustomerProfile)
def get_customer_profile(
    customer_id: str,
    role: str = Depends(require_roles({"executive", "operations", "admin"})),
) -> CustomerProfile:
    with get_db() as db:
        row = db.execute(
            """
            SELECT id, full_name, country, segment, points_balance, last_order_at
            FROM customers
            WHERE id = ?
            """,
            (customer_id,),
        ).fetchone()

    if row is None:
        write_audit_log(role, "read_customer_profile", "rejected", customer_id, "not found")
        raise HTTPException(status_code=404, detail="customer not found")

    write_audit_log(role, "read_customer_profile", "success", customer_id, "")
    return CustomerProfile(
        id=row["id"],
        full_name=row["full_name"],
        country=row["country"],
        segment=row["segment"],
        points_balance=int(row["points_balance"]),
        last_order_at=parse_datetime_or_none(row["last_order_at"]),
    )


@app.post("/api/v1/customers/{customer_id}/points/adjust", response_model=CustomerPointsAdjustmentResult)
def adjust_customer_points(
    customer_id: str,
    payload: CustomerPointsAdjustmentCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> CustomerPointsAdjustmentResult:
    happened_at = datetime.now(timezone.utc)

    with get_db() as db:
        row = db.execute(
            "SELECT points_balance FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if row is None:
            write_audit_log(role, "adjust_customer_points", "rejected", customer_id, "not found")
            raise HTTPException(status_code=404, detail="customer not found")

        previous_points = int(row["points_balance"])
        current_points = previous_points + payload.delta_points
        if current_points < 0:
            write_audit_log(role, "adjust_customer_points", "rejected", customer_id, "negative points balance")
            raise HTTPException(status_code=400, detail="points balance cannot be negative")

        db.execute(
            "UPDATE customers SET points_balance = ? WHERE id = ?",
            (current_points, customer_id),
        )
        db.execute(
            """
            INSERT INTO loyalty_events (customer_id, delta_points, reason, happened_at)
            VALUES (?, ?, ?, ?)
            """,
            (customer_id, payload.delta_points, payload.reason[:300], happened_at.isoformat()),
        )

    write_audit_log(
        role,
        "adjust_customer_points",
        "success",
        customer_id,
        f"delta={payload.delta_points}, reason={payload.reason[:120]}",
    )

    return CustomerPointsAdjustmentResult(
        customer_id=customer_id,
        previous_points=previous_points,
        current_points=current_points,
        delta_points=payload.delta_points,
        reason=payload.reason,
        updated_at=happened_at,
    )


@app.post("/api/v1/marketing/orders", response_model=MarketingOrderResult, status_code=201)
def create_marketing_order(
    payload: MarketingOrderCreate,
    role: str = Depends(require_roles({"operations", "admin"})),
) -> MarketingOrderResult:
    if payload.total_amount <= 0:
        raise HTTPException(status_code=400, detail="total_amount must be greater than zero")
    if len(payload.order_items) == 0:
        raise HTTPException(status_code=400, detail="order_items must contain at least one item")

    now = datetime.now(timezone.utc)
    clean_items = [item.strip().lower().replace(" ", "_") for item in payload.order_items if item.strip()]
    if not clean_items:
        raise HTTPException(status_code=400, detail="order_items must contain valid values")

    amount_usd = convert_amount(payload.total_amount, payload.currency, "USD")
    awarded_points = max(int(round(amount_usd * 10)), 1)

    with get_db() as db:
        customer_row = db.execute(
            "SELECT id, points_balance FROM customers WHERE id = ?",
            (payload.customer_id,),
        ).fetchone()
        if customer_row is None:
            raise HTTPException(status_code=404, detail="customer not found")

        store_row = db.execute(
            "SELECT id FROM stores WHERE id = ?",
            (payload.store_id,),
        ).fetchone()
        if store_row is None:
            raise HTTPException(status_code=404, detail="store not found")

        cursor = db.execute(
            """
            INSERT INTO digital_orders (
                customer_id, store_id, ordered_at, total_amount, currency, channel, order_items
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.customer_id,
                payload.store_id,
                now.isoformat(),
                payload.total_amount,
                payload.currency,
                payload.channel,
                ",".join(clean_items),
            ),
        )
        order_id = int(cursor.lastrowid)

        current_points = int(customer_row["points_balance"]) + awarded_points
        db.execute(
            "UPDATE customers SET points_balance = ?, last_order_at = ? WHERE id = ?",
            (current_points, now.isoformat(), payload.customer_id),
        )
        db.execute(
            """
            INSERT INTO loyalty_events (customer_id, delta_points, reason, happened_at)
            VALUES (?, ?, ?, ?)
            """,
            (payload.customer_id, awarded_points, "purchase_accumulation", now.isoformat()),
        )

    write_audit_log(
        role,
        "create_marketing_order",
        "success",
        payload.customer_id,
        f"order_id={order_id}, store_id={payload.store_id}, awarded_points={awarded_points}",
    )

    return MarketingOrderResult(
        order_id=order_id,
        customer_id=payload.customer_id,
        store_id=payload.store_id,
        channel=payload.channel,
        order_items=clean_items,
        total_amount=payload.total_amount,
        currency=payload.currency,
        awarded_points=awarded_points,
        current_points_balance=current_points,
        ordered_at=now,
    )


@app.get("/api/v1/marketing/crm/overview", response_model=CrmOverview)
def get_marketing_crm_overview(
    days: int = Query(default=30, ge=7, le=365),
    country: Literal["CO", "US"] | None = Query(default=None),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    role: str = Depends(require_roles({"executive", "operations", "admin"})),
) -> CrmOverview:
    now = datetime.now(timezone.utc)
    start_at = now - timedelta(days=days)

    with get_db() as db:
        customers_rows = db.execute(
            """
            SELECT id, last_order_at
            FROM customers
            WHERE (? IS NULL OR country = ?)
            """,
            (country, country),
        ).fetchall()

        orders_rows = db.execute(
            """
            SELECT do.total_amount, do.currency
            FROM digital_orders do
            JOIN customers c ON c.id = do.customer_id
            WHERE do.ordered_at >= ? AND do.ordered_at < ?
              AND (? IS NULL OR c.country = ?)
            """,
            (start_at.isoformat(), now.isoformat(), country, country),
        ).fetchall()

    active_customers = 0
    for row in customers_rows:
        last_order = parse_datetime_or_none(row["last_order_at"])
        if last_order is not None and last_order >= start_at:
            active_customers += 1

    total_revenue = sum(convert_amount(row["total_amount"], row["currency"], currency) for row in orders_rows)

    write_audit_log(
        role,
        "read_marketing_crm_overview",
        "success",
        f"country={country or 'ALL'}",
        f"days={days}, customers={len(customers_rows)}, orders={len(orders_rows)}",
    )

    return CrmOverview(
        period_days=days,
        country=country,
        total_customers=len(customers_rows),
        active_customers=active_customers,
        total_orders=len(orders_rows),
        total_revenue=round(total_revenue, 2),
        currency=currency,
        generated_at=now,
    )


@app.get("/api/v1/marketing/crm/customers", response_model=list[CrmCustomerRow])
def get_marketing_crm_customers(
    country: Literal["CO", "US"] | None = Query(default=None),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    limit: int = Query(default=50, ge=1, le=500),
    role: str = Depends(require_roles({"executive", "operations", "admin"})),
) -> list[CrmCustomerRow]:
    with get_db() as db:
        customers_rows = db.execute(
            """
            SELECT id, full_name, country, segment, points_balance, last_order_at
            FROM customers
            WHERE (? IS NULL OR country = ?)
            ORDER BY id ASC
            """,
            (country, country),
        ).fetchall()

        orders_rows = db.execute(
            """
            SELECT customer_id, total_amount, currency, order_items
            FROM digital_orders
            ORDER BY ordered_at DESC
            """
        ).fetchall()

    agg: dict[str, dict[str, float | int | dict[str, int]]] = {}
    for row in orders_rows:
        customer_id = row["customer_id"]
        if customer_id not in agg:
            agg[customer_id] = {"orders": 0, "spend": 0.0, "items": {}}
        agg[customer_id]["orders"] += 1
        agg[customer_id]["spend"] += convert_amount(row["total_amount"], row["currency"], currency)

        items_map = agg[customer_id]["items"]
        for token in (row["order_items"] or "").split(","):
            key = token.strip()
            if not key:
                continue
            items_map[key] = items_map.get(key, 0) + 1

    output: list[CrmCustomerRow] = []
    for row in customers_rows:
        customer_id = row["id"]
        item_agg = agg.get(customer_id, {"orders": 0, "spend": 0.0, "items": {}})
        items_map = item_agg["items"]
        favorite_item = None
        if items_map:
            favorite_item = sorted(items_map.items(), key=lambda pair: pair[1], reverse=True)[0][0]

        output.append(
            CrmCustomerRow(
                customer_id=customer_id,
                full_name=row["full_name"],
                country=row["country"],
                segment=row["segment"],
                points_balance=int(row["points_balance"]),
                orders_count=int(item_agg["orders"]),
                total_spend=round(float(item_agg["spend"]), 2),
                favorite_item=favorite_item,
                last_order_at=parse_datetime_or_none(row["last_order_at"]),
            )
        )

    output.sort(key=lambda item: item.total_spend, reverse=True)
    output = output[:limit]

    write_audit_log(
        role,
        "read_marketing_crm_customers",
        "success",
        f"country={country or 'ALL'}",
        f"rows={len(output)}, currency={currency}",
    )
    return output


@app.get("/api/v1/marketing/customers/{customer_id}/history", response_model=list[CustomerOrderHistoryRow])
def get_marketing_customer_history(
    customer_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    role: str = Depends(require_roles({"executive", "operations", "admin"})),
) -> list[CustomerOrderHistoryRow]:
    with get_db() as db:
        customer_row = db.execute("SELECT 1 FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if customer_row is None:
            raise HTTPException(status_code=404, detail="customer not found")

        rows = db.execute(
            """
            SELECT id, customer_id, store_id, ordered_at, total_amount, currency, channel, order_items
            FROM digital_orders
            WHERE customer_id = ?
            ORDER BY ordered_at DESC, id DESC
            LIMIT ?
            """,
            (customer_id, limit),
        ).fetchall()

    output = [
        CustomerOrderHistoryRow(
            id=int(row["id"]),
            customer_id=row["customer_id"],
            store_id=row["store_id"],
            ordered_at=parse_datetime_or_none(row["ordered_at"]) or datetime.now(timezone.utc),
            total_amount=round(float(row["total_amount"]), 2),
            currency=row["currency"],
            channel=row["channel"],
            order_items=[item for item in (row["order_items"] or "").split(",") if item],
        )
        for row in rows
    ]

    write_audit_log(
        role,
        "read_marketing_customer_history",
        "success",
        customer_id,
        f"rows={len(output)}",
    )
    return output


@app.get("/api/v1/marketing/personalization/recommendations", response_model=PersonalizationResponse)
def get_marketing_personalization_recommendations(
    customer_id: str = Query(..., min_length=3),
    currency: Literal["COP", "USD"] = Query(default="USD"),
    limit: int = Query(default=5, ge=1, le=10),
    role: str = Depends(require_roles({"executive", "operations", "admin"})),
) -> PersonalizationResponse:
    with get_db() as db:
        customer_row = db.execute(
            "SELECT id, segment, country FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if customer_row is None:
            raise HTTPException(status_code=404, detail="customer not found")

        orders_rows = db.execute(
            """
            SELECT order_items
            FROM digital_orders
            WHERE customer_id = ?
            ORDER BY ordered_at DESC
            LIMIT 30
            """,
            (customer_id,),
        ).fetchall()
        preferences_rows = db.execute(
            """
            SELECT preference_value
            FROM customer_preferences
            WHERE customer_id = ?
            """,
            (customer_id,),
        ).fetchall()

    behavior_tokens: dict[str, int] = {}
    for row in orders_rows:
        for token in (row["order_items"] or "").split(","):
            clean = token.strip().lower()
            if not clean:
                continue
            behavior_tokens[clean] = behavior_tokens.get(clean, 0) + 1

    for row in preferences_rows:
        for token in str(row["preference_value"]).lower().split("_"):
            clean = token.strip()
            if clean:
                behavior_tokens[clean] = behavior_tokens.get(clean, 0) + 2

    if customer_row["segment"] == "vip":
        behavior_tokens["familiar"] = behavior_tokens.get("familiar", 0) + 2
        behavior_tokens["sharing"] = behavior_tokens.get("sharing", 0) + 2
    elif customer_row["segment"] == "new":
        behavior_tokens["kids"] = behavior_tokens.get("kids", 0) + 1
        behavior_tokens["clasico"] = behavior_tokens.get("clasico", 0) + 1

    recommendations: list[PersonalizedProductRecommendation] = []
    for item in PERSONALIZATION_CATALOG:
        tags = [str(tag).lower() for tag in item["tags"]]
        score = 0.0
        matched_tags: list[str] = []
        for tag in tags:
            token_score = behavior_tokens.get(tag, 0)
            if token_score > 0:
                score += token_score
                matched_tags.append(tag)

        if score == 0:
            score = 0.5

        expected_price = convert_amount(float(item["base_price_usd"]), "USD", currency)
        reason = (
            f"Coincide con tu comportamiento: {', '.join(matched_tags)}"
            if matched_tags
            else "Recomendacion base para explorar nuevos productos"
        )
        recommendations.append(
            PersonalizedProductRecommendation(
                product_id=str(item["product_id"]),
                name=str(item["name"]),
                reason=reason,
                score=round(score, 2),
                expected_price=round(expected_price, 2),
                currency=currency,
            )
        )

    recommendations.sort(key=lambda rec: rec.score, reverse=True)
    recommendations = recommendations[:limit]

    now = datetime.now(timezone.utc)
    write_audit_log(
        role,
        "read_marketing_personalization",
        "success",
        customer_id,
        f"rows={len(recommendations)}, currency={currency}",
    )

    return PersonalizationResponse(
        customer_id=customer_id,
        currency=currency,
        generated_at=now,
        recommendations=recommendations,
    )
