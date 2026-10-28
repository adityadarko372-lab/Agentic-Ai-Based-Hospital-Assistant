"""Health check endpoint.

The frontend calls this on start-up to show "Backend connected". It also
reports which optional features are switched on, so the UI and the examiner
can see exactly what is running (nothing is implied that is not active).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.intent import get_intent_classifier
from app.core.config import Settings, get_settings
from app.health_info.retriever import index_present

router = APIRouter(prefix="/api", tags=["health"])


class FeatureFlags(BaseModel):
    intent_classifier: str  # requested in settings
    # What is actually routing messages ("rules" if the trained model is missing).
    intent_classifier_active: str
    health_info_enabled: bool
    # The MedQuAD index files exist (cheap check; the model loads on first use).
    health_info_index_present: bool
    llm_phrasing_enabled: bool
    front_desk_enabled: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    demo_data: bool
    server_time: datetime
    features: FeatureFlags


@router.get("/health", response_model=HealthResponse)
def read_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        # Every record in this prototype is synthetic demonstration data.
        demo_data=True,
        server_time=datetime.now(timezone.utc),
        features=FeatureFlags(
            intent_classifier=settings.intent_classifier,
            intent_classifier_active=get_intent_classifier()[0].name,
            health_info_enabled=settings.health_info_enabled,
            health_info_index_present=index_present(),
            llm_phrasing_enabled=settings.llm_phrasing_enabled,
            front_desk_enabled=settings.front_desk_enabled,
        ),
    )
