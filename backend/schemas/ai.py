"""
Daladan Platform — AI Endpoint Pydantic Schemas
Comprehensive validation for the optimize-listing and summarize-chat endpoints.
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════
#  Endpoint 1: /api/ai/optimize-listing
# ═══════════════════════════════════════════════════════


class OptimizeListingRequest(BaseModel):
    """Input payload for AI-powered product description generation."""

    model_config = {"extra": "forbid"}

    product_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Name of the crop, e.g. 'Red Apples'",
        examples=["Red Apples", "Cherry Tomatoes"],
    )
    variety: Optional[str] = Field(
        None,
        max_length=100,
        description="Variety or grade, e.g. 'Grade A Organic'",
        examples=["Grade A Organic", "Vine-Ripened"],
    )
    quantity_kg: float = Field(
        ...,
        gt=0,
        le=100_000,
        description="Available quantity in kilograms",
        examples=[1800, 2400],
    )
    price_per_kg: float = Field(
        ...,
        gt=0,
        le=10_000,
        description="Price per kilogram in USD",
        examples=[4.50, 3.10],
    )
    region: Optional[str] = Field(
        None,
        max_length=100,
        description="Growing region, e.g. 'Fergana'",
        examples=["Fergana", "Namangan", "Tashkent"],
    )
    is_organic: bool = Field(
        False,
        description="Whether the produce is organically grown",
    )

    @field_validator("product_name")
    @classmethod
    def product_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("product_name must not be blank")
        return v.strip()


# ═══════════════════════════════════════════════════════
#  Endpoint 2: /api/ai/summarize-chat
# ═══════════════════════════════════════════════════════


class SummarizeChatRequest(BaseModel):
    """Input payload for AI-powered deal chat summarization."""

    model_config = {"extra": "forbid"}

    deal_id: Optional[UUID] = Field(
        None,
        description="UUID of the deal group to summarize",
    )
    deal_number: Optional[int] = Field(
        None,
        description="Integer deal number (e.g. 901) — alternative to UUID",
        examples=[901],
    )

    @field_validator("deal_number")
    @classmethod
    def deal_number_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("deal_number must be a positive integer")
        return v

    def model_post_init(self, __context) -> None:
        if self.deal_id is None and self.deal_number is None:
            raise ValueError("Either deal_id or deal_number must be provided")


class DealSummaryResponse(BaseModel):
    """Structured JSON summary extracted by the LLM from chat history."""

    deal_number: int = Field(..., description="The deal identifier number")
    title: str = Field(..., description="Product being negotiated")
    agreed_price: Optional[str] = Field(
        None,
        description="Agreed unit price, e.g. '$3.65/kg'",
    )
    quantity: Optional[str] = Field(
        None,
        description="Agreed quantity, e.g. '1,200 kg weekly'",
    )
    total_value: Optional[str] = Field(
        None,
        description="Calculated total value, e.g. '$4,380/week'",
    )
    pickup_time: Optional[str] = Field(
        None,
        description="Agreed pickup/loading time, e.g. '1:30 AM'",
    )
    departure_time: Optional[str] = Field(
        None,
        description="Driver departure time, e.g. '2:00 AM'",
    )
    delivery_eta: Optional[str] = Field(
        None,
        description="Expected delivery time, e.g. '5:30 AM'",
    )
    delivery_gate: Optional[str] = Field(
        None,
        description="Delivery location detail, e.g. 'Gate B-4'",
    )
    driver_name: Optional[str] = Field(
        None,
        description="Name of the assigned driver",
    )
    summary_text: str = Field(
        ...,
        description="Free-form AI summary of the negotiation",
    )
    action_items: list[str] = Field(
        default_factory=list,
        description="List of follow-up action items",
    )
