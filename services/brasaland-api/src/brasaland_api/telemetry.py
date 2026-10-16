import json
import logging
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictStr, model_validator


logger = logging.getLogger(__name__)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class SafeTelemetryRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def handler(request: Request):
            try:
                return await original_handler(request)
            except RequestValidationError as error:
                raise HTTPException(status_code=422, detail="Invalid telemetry payload") from error

        return handler


telemetry_router = APIRouter(
    prefix="/telemetry", tags=["telemetry"], route_class=SafeTelemetryRoute
)
TELEMETRY_ENDPOINT = os.getenv(
    "TELEMETRY_ENDPOINT", "http://localhost:8000/telemetry/events"
)
EVENT_SCHEMA_PATH = Path(__file__).resolve().parents[4] / "docs/telemetry/event-schemas.json"
with EVENT_SCHEMA_PATH.open(encoding="utf-8") as schema_file:
    EVENT_CATALOG = {
        event["event_type"]: event
        for event in json.load(schema_file)["catalog"]
    }


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: UUID
    timestamp: AwareDatetime
    sessionId: StrictStr | None
    userId: StrictStr | None
    event_type: StrictStr
    schemaVersion: Literal["1.0.0"]
    requestId: StrictStr = Field(min_length=1)
    properties: dict[StrictStr, Any]

    @model_validator(mode="after")
    def validate_catalog_properties(self) -> "TelemetryEvent":
        schema = EVENT_CATALOG.get(self.event_type)
        if schema is None:
            raise ValueError("event_type is not declared in the telemetry catalog")

        allowed = set(schema["allowlist"])
        property_names = set(self.properties)
        extra = property_names - allowed
        missing = set(schema["required"]) - property_names
        if extra:
            raise ValueError(f"properties are not allowed for {self.event_type}: {sorted(extra)}")
        if missing:
            raise ValueError(f"required properties missing for {self.event_type}: {sorted(missing)}")

        for name, value in self.properties.items():
            definition = schema["properties"][name]
            property_type = definition["type"]
            valid_types = {
                "string": lambda item: isinstance(item, str),
                "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
                "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
                "boolean": lambda item: isinstance(item, bool),
            }
            if property_type not in valid_types or not valid_types[property_type](value):
                raise ValueError(f"property {name} must be {property_type}")
            if property_type == "number" and not math.isfinite(value):
                raise ValueError(f"property {name} must be finite")
            if "enum" in definition and value not in definition["enum"]:
                raise ValueError(f"property {name} must be one of {definition['enum']}")
            if definition.get("format") == "date-time":
                try:
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError as error:
                    raise ValueError(f"property {name} must be an ISO 8601 date-time") from error
                if parsed.tzinfo is None:
                    raise ValueError(f"property {name} must include a timezone")

        return self


class TelemetryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    events: list[TelemetryEvent]


@telemetry_router.post("/events", status_code=200)
def receive_telemetry(batch: TelemetryBatch) -> dict[str, int]:
    logger.info("Received telemetry batch with %d events", len(batch.events))
    for event in batch.events:
        logger.info("Received telemetry event_type=%s", event.event_type)
    return {"received": len(batch.events)}