"""
Daladan Platform — AI Router
Two GenAI-powered endpoints using Google Gemini:
  1. POST /api/ai/optimize-listing  — streaming product description
  2. POST /api/ai/summarize-chat    — structured deal summary (JSON)
"""
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from google import genai
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.auth import RoleChecker, get_current_user
from backend.middleware.rate_limit import limiter, RATE_LIMIT_AI

from backend.config import get_settings
from backend.database import async_session
from backend.models import DealGroup, Message, User
from backend.schemas.ai import (
    DealSummaryResponse,
    OptimizeListingRequest,
    SummarizeChatRequest,
)

logger = logging.getLogger("daladan.ai")
settings = get_settings()

router = APIRouter(prefix="/api/ai", tags=["AI"])

MODEL = "gemini-2.0-flash"

# ── Lazy Gemini client ──
_client = None


def _get_client() -> genai.Client:
    """Return a cached Gemini client, creating it on first call."""
    global _client
    if _client is None:
        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="GOOGLE_API_KEY is not configured. Add it to your .env file.",
            )
        _client = genai.Client(api_key=api_key)
    return _client


# ═══════════════════════════════════════════════════════
#  Endpoint 1: Streaming Product Description
# ═══════════════════════════════════════════════════════

LISTING_SYSTEM_PROMPT = """\
You are an expert agricultural marketing copywriter for Daladan, a B2B produce marketplace in Uzbekistan.
Given raw crop data, write a compelling, professional product listing.
Include:
- A catchy one-line title with an emoji
- A vivid 2-3 sentence description highlighting quality, origin, and best use cases
- Shelf life and storage recommendations
- 3-4 hashtag-style tags at the end (e.g. #Organic #GradeA)
Write in English. Be concise but persuasive. Do NOT use markdown formatting — plain text only.
"""


async def _stream_listing(request: OptimizeListingRequest) -> AsyncGenerator[str, None]:
    """Yield text chunks from the Gemini streaming response."""
    organic_label = "Yes — certified organic" if request.is_organic else "No"
    user_prompt = (
        f"Product: {request.product_name}\n"
        f"Variety: {request.variety or 'N/A'}\n"
        f"Quantity available: {request.quantity_kg} kg\n"
        f"Price: ${request.price_per_kg}/kg\n"
        f"Region: {request.region or 'Uzbekistan'}\n"
        f"Organic: {organic_label}\n\n"
        "Write the listing now."
    )

    try:
        response = _get_client().models.generate_content_stream(
            model=MODEL,
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=LISTING_SYSTEM_PROMPT,
                temperature=0.8,
                max_output_tokens=512,
            ),
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as exc:
        logger.error("Gemini streaming error: %s", exc)
        yield f"\n\n[Error generating description: {exc}]"


@router.post(
    "/optimize-listing",
    dependencies=[Depends(RoleChecker(["producer"]))],
)
@limiter.limit(RATE_LIMIT_AI)
async def optimize_listing(request: Request, payload: OptimizeListingRequest):
    """
    Generate an AI-powered marketing description for a crop listing.
    Returns a streaming text/plain response.
    """
    return StreamingResponse(
        _stream_listing(payload),
        media_type="text/plain; charset=utf-8",
    )


# ═══════════════════════════════════════════════════════
#  Endpoint 2: Structured Chat Summary
# ═══════════════════════════════════════════════════════

SUMMARY_SYSTEM_PROMPT = """\
You are an AI assistant for Daladan, a B2B agricultural marketplace.
Given a chat transcript from a deal negotiation, extract a structured JSON summary.

Return ONLY valid JSON with these fields:
{
  "deal_number": <int>,
  "title": "<product>",
  "agreed_price": "<price string or null>",
  "quantity": "<quantity string or null>",
  "total_value": "<value string or null>",
  "pickup_time": "<time string or null>",
  "departure_time": "<time string or null>",
  "delivery_eta": "<ETA string or null>",
  "delivery_gate": "<gate/location or null>",
  "driver_name": "<name or null>",
  "summary_text": "<1-2 paragraph narrative summary>",
  "action_items": ["<action 1>", "<action 2>", ...]
}

Be precise. Extract exact numbers, times, and names from the conversation.
If information is not mentioned, set the field to null.
"""


@router.post(
    "/summarize-chat",
    response_model=DealSummaryResponse,
    dependencies=[Depends(get_current_user)],
)
@limiter.limit(RATE_LIMIT_AI)
async def summarize_chat(request: Request, payload: SummarizeChatRequest):
    """
    Summarize a deal's chat history using AI.
    Returns a structured JSON summary with agreed terms and action items.
    """
    # ── Fetch deal + messages ──
    async with async_session() as session:
        if payload.deal_id:
            stmt = (
                select(DealGroup)
                .where(DealGroup.id == payload.deal_id)
                .options(selectinload(DealGroup.messages))
            )
        else:
            stmt = (
                select(DealGroup)
                .where(DealGroup.deal_number == payload.deal_number)
                .options(selectinload(DealGroup.messages))
            )

        result = await session.execute(stmt)
        deal = result.scalar_one_or_none()

        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

        if not deal.messages:
            raise HTTPException(status_code=400, detail="No messages in this deal")

        # Fetch sender names for the transcript
        sender_ids = {m.sender_id for m in deal.messages if m.sender_id}
        users_result = await session.execute(
            select(User).where(User.id.in_(sender_ids))
        )
        users_map = {u.id: u.full_name for u in users_result.scalars().all()}

    # ── Build transcript ──
    lines = [f"Deal #{deal.deal_number} — {deal.title}"]
    lines.append(f"Status: {deal.status.value}")
    lines.append("---")

    for msg in deal.messages:
        if msg.is_system:
            sender_name = "SYSTEM"
        else:
            sender_name = users_map.get(msg.sender_id, "Unknown")
        lines.append(f"[{msg.created_at}] {sender_name}: {msg.content}")

    transcript = "\n".join(lines)

    # ── Call Gemini ──
    try:
        response = _get_client().models.generate_content(
            model=MODEL,
            contents=f"Summarize this deal chat:\n\n{transcript}",
            config=genai.types.GenerateContentConfig(
                system_instruction=SUMMARY_SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
        )

        raw_text = response.text.strip()
        data = json.loads(raw_text)
        return DealSummaryResponse(**data)

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini JSON: %s\nRaw: %s", exc, raw_text)
        raise HTTPException(
            status_code=502,
            detail="AI returned invalid JSON. Please try again.",
        )
    except Exception as exc:
        logger.error("Gemini summarization error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {exc}",
        )
