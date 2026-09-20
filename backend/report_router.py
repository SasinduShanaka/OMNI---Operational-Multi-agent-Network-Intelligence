from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from backend import report_service as service

router = APIRouter(prefix="/reports", tags=["Report Agent"])
Domain = Literal["inventory", "forecast", "production", "supply_chain"]


class ReportScope(BaseModel):
    title: str = Field(default="Factory management report", min_length=1, max_length=100)
    domains: list[Domain] = Field(default_factory=lambda: ["inventory", "forecast", "production", "supply_chain"], min_length=1, max_length=4)
    skus: list[str] = Field(default_factory=list, max_length=100)
    periods: int = Field(default=3, ge=1, le=12)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip():
            raise ValueError("Title must not be blank")
        return value.strip()

    @field_validator("domains")
    @classmethod
    def unique_domains(cls, value):
        return list(dict.fromkeys(value))

    @field_validator("skus")
    @classmethod
    def valid_skus(cls, value):
        import re
        cleaned = list(dict.fromkeys(sku.strip().upper() for sku in value))
        if any(not re.fullmatch(r"GAR-\d{3}", sku) for sku in cleaned):
            raise ValueError("Use product codes such as GAR-003")
        return cleaned


class ScheduleRequest(BaseModel):
    scope: ReportScope = Field(default_factory=ReportScope)
    frequency: Literal["daily", "monthly"] = "daily"
    time: str = Field(default="08:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    day_of_month: int = Field(default=1, ge=1, le=28)


class ScheduleToggle(BaseModel):
    enabled: bool


def storage_call(function, *args):
    try:
        return function(*args)
    except Exception as error:
        raise HTTPException(503, "Report storage is unavailable. Check MongoDB connectivity and MONGO_URI.") from error


@router.post("/generate")
def generate(scope: ReportScope):
    report = storage_call(service.generate_report, scope.model_dump())
    # Raw evidence remains in storage; the API returns readable report sections.
    report.pop("evidence", None)
    return report


@router.get("")
def history(limit: int = Query(20, ge=1, le=100), skip: int = Query(0, ge=0)):
    return storage_call(service.list_reports, limit, skip)


@router.get("/schedules")
def schedules():
    return {"schedules": storage_call(service.list_schedules)}


@router.post("/schedules")
def schedule(request: ScheduleRequest):
    return storage_call(service.create_schedule, request.model_dump())


@router.patch("/schedules/{schedule_id}")
def toggle(schedule_id: str, request: ScheduleToggle):
    result = storage_call(service.set_schedule_enabled, schedule_id, request.enabled)
    if result is None:
        raise HTTPException(404, "Schedule not found")
    return result


@router.get("/{report_id}")
def report(report_id: str):
    result = storage_call(service.get_report, report_id)
    if result is None:
        raise HTTPException(404, "Report not found")
    return result
