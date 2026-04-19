from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class TechnicalPRDForm(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    epic_key: Optional[str] = Field(None, pattern=r"^[A-Z]+-\d+$")
    problem_statement: str = Field(..., min_length=10, max_length=2000)
    proposed_approach: str = Field(..., min_length=10, max_length=2000)
    target_users: str = Field(..., min_length=5, max_length=500)
    success_metrics: List[str] = Field(..., min_items=1, max_items=5)
    dependencies: Optional[List[str]] = Field(None)
    risk_areas: Optional[List[str]] = Field(None)
    technical_constraints: Optional[str] = Field(None, max_length=1000)
    data_model_changes: Optional[str] = Field(None, max_length=1000)
    api_changes: Optional[str] = Field(None, max_length=1000)

    @field_validator("success_metrics")
    def validate_metrics(cls, v):
        for metric in v:
            if len(metric) < 3 or len(metric) > 200:
                raise ValueError("Each metric must be 3-200 characters")
        return v


class BusinessPRDForm(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    epic_key: Optional[str] = Field(None, pattern=r"^[A-Z]+-\d+$")
    business_context: str = Field(..., min_length=20, max_length=1500)
    market_opportunity: str = Field(..., min_length=20, max_length=1500)
    target_users: str = Field(..., min_length=5, max_length=500)
    revenue_impact_description: str = Field(..., min_length=10, max_length=500)
    proposed_solution: str = Field(..., min_length=10, max_length=1500)
    success_metrics: List[str] = Field(..., min_items=1, max_items=5)
    key_stakeholders: List[str] = Field(..., min_items=1, max_items=10)
    timeline_estimate_weeks: int = Field(..., ge=1, le=52)
    risk_areas: Optional[List[str]] = Field(None)

    @field_validator("timeline_estimate_weeks")
    def validate_timeline(cls, v):
        if v <= 0:
            raise ValueError("Timeline must be positive")
        return v


class RiskAssessmentForm(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=200)
    service_type: str = Field(..., min_length=5, max_length=200)
    data_categories: List[str] = Field(..., min_items=1, max_items=10)
    regulatory_frameworks: List[str] = Field(..., min_items=1, max_items=5)
    security_requirements: str = Field(..., min_length=10, max_length=1000)
    integration_approach: str = Field(..., min_length=10, max_length=1000)
    data_retention_days: int = Field(..., ge=1, le=3650)
    exit_strategy_description: str = Field(..., min_length=10, max_length=1000)
    monitoring_approach: Optional[str] = Field(None, max_length=500)
    compliance_checklist: Optional[List[str]] = Field(None)

    @field_validator("data_retention_days")
    def validate_retention(cls, v):
        if v > 3650:
            raise ValueError("Retention cannot exceed 10 years")
        return v


class SponsorBankForm(BaseModel):
    bank_name: str = Field(..., min_length=1, max_length=200)
    bank_routing_number: str = Field(..., min_length=5, max_length=20)
    integration_scope: str = Field(..., min_length=10, max_length=1500)
    regulatory_requirements: List[str] = Field(..., min_items=1, max_items=5)
    transaction_types: List[str] = Field(..., min_items=1, max_items=10)
    settlement_window_hours: int = Field(..., ge=1, le=48)
    daily_volume_limit_cents: int = Field(..., ge=1000)
    sla_uptime_percentage: float = Field(..., ge=99.0, le=100.0)
    incident_response_sla_minutes: int = Field(..., ge=15, le=1440)
    compliance_contacts: List[str] = Field(..., min_items=1, max_items=5)

    @field_validator("sla_uptime_percentage")
    def validate_sla(cls, v):
        if v < 99.0:
            raise ValueError("SLA must be at least 99%")
        return v


class DiscoveryForm(BaseModel):
    problem_area: str = Field(..., min_length=10, max_length=1000)
    research_questions: List[str] = Field(..., min_items=1, max_items=5)
    user_segments: List[str] = Field(..., min_items=1, max_items=10)
    data_sources: List[str] = Field(..., min_items=1, max_items=5)
    hypotheses: List[str] = Field(..., min_items=1, max_items=5)
    evidence_summary: str = Field(..., min_length=10, max_length=1500)
    opportunity_size_description: str = Field(..., min_length=10, max_length=500)
    recommendation: str = Field(..., min_length=10, max_length=1000)
    next_steps: Optional[List[str]] = Field(None, max_items=3)


class EpicBuilderForm(BaseModel):
    epic_key: str = Field(..., pattern=r"^[A-Z]+-\d+$")
    epic_summary: str = Field(..., min_length=10, max_length=200)
    epic_description: str = Field(..., min_length=20, max_length=1500)
    acceptance_criteria: List[str] = Field(..., min_items=1, max_items=10)
    story_count_estimate: int = Field(..., ge=1, le=50)
    story_point_estimate: int = Field(..., ge=1, le=200)
    priority: str = Field(..., pattern=r"^(highest|high|medium|low|lowest)$")
    team: str = Field(..., min_length=1, max_length=100)
    dependencies: Optional[List[str]] = Field(None, max_items=5)
    success_metrics: Optional[List[str]] = Field(None, max_items=3)

    @field_validator("priority")
    def validate_priority(cls, v):
        valid = ["highest", "high", "medium", "low", "lowest"]
        if v.lower() not in valid:
            raise ValueError(f"Priority must be one of {valid}")
        return v.lower()
