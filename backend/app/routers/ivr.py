"""
Twilio IVR Router — KissanFlow Helpline
Farmers call a toll-free / Twilio number; Twilio POSTs to these endpoints
and reads the TwiML response aloud to the caller.

Key Webhook Endpoints:
  - POST /api/ivr/incoming   — Welcome message + main menu
  - POST /api/ivr/gather     — Handle keypress, route to sub-menu
  - POST /api/ivr/status     — Check booking status by mobile (caller ID)
  - POST /api/ivr/grievance  — Raise grievance via IVR (creates DB record)
  - POST /api/ivr/book-info  — Slot booking information & guidance
"""
import os
import hmac
import hashlib
import base64
from typing import Annotated, Optional
from fastapi import APIRouter, Form, Request, Depends, Header, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.grievance import GrievanceCategory
from app.services.ivr_service import (
    lookup_farmer_by_mobile,
    get_active_booking,
    create_ivr_grievance,
)

router = APIRouter(tags=["ivr"])

TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "+911800XXXXXXX")
IVR_BASE_URL = os.environ.get("IVR_BASE_URL", "http://localhost:8000")


# ─── TwiML XML Generators ─────────────────────────────────────────────────────

def twiml(content: str) -> Response:
    """Wrap content in XML envelope with correct TwiML media type."""
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response>{content}</Response>'
    return Response(content=xml, media_type="application/xml")


def say(text: str, language: str = "en-IN", voice: str = "Polly.Aditi") -> str:
    """Generate a <Say> TwiML verb. Polly.Aditi is Amazon Polly's Indian bilingual voice."""
    return f'<Say language="{language}" voice="{voice}">{text}</Say>'


def gather(action: str, num_digits: int = 1, timeout: int = 8, method: str = "POST") -> str:
    """Wrap content in a <Gather> verb that captures keypad DTMF."""
    return f'<Gather numDigits="{num_digits}" action="{action}" timeout="{timeout}" method="{method}">'


# ─── Twilio Signature Security ────────────────────────────────────────────────

async def verify_twilio_signature(request: Request, x_twilio_signature: Optional[str] = Header(None)):
    """
    Twilio request signature validation dependency, applied to every IVR route (#1).

    - TWILIO_AUTH_TOKEN not configured → demo mode, permit (local SIH demo).
    - Configured but X-Twilio-Signature missing → 403.
    - Configured and header present → validate HMAC-SHA1 per Twilio's spec.
    """
    if not TWILIO_AUTH_TOKEN:
        # Development / demo mode — no token configured, permit
        return True

    if not x_twilio_signature:
        raise HTTPException(status_code=403, detail="Missing Twilio signature")

    # Construct the data string for signature verification
    url = str(request.url)
    form_data = await request.form()
    # Sort parameters alphabetically by key
    sorted_params = sorted(form_data.items(), key=lambda x: x[0])
    s = url + "".join([f"{k}{v}" for k, v in sorted_params])

    expected = base64.b64encode(
        hmac.new(TWILIO_AUTH_TOKEN.encode("utf-8"), s.encode("utf-8"), hashlib.sha1).digest()
    ).decode("utf-8")

    if not hmac.compare_digest(expected, x_twilio_signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    return True


# Apply signature validation to every IVR webhook route (#1).
router.dependencies.append(Depends(verify_twilio_signature))


# ─── Voice Prompts ────────────────────────────────────────────────────────────

WELCOME_MESSAGE = (
    "Welcome to KissanFlow Helpline. "
    "किसानफ्लो हेल्पलाइन में आपका स्वागत है. "
)

MAIN_MENU_PROMPT = (
    "Press 1 to check your booking status. "
    "अपनी बुकिंग और कतार स्थिति जानने के लिए 1 दबाएं. "
    "Press 2 to raise a grievance. "
    "शिकायत दर्ज करने के लिए 2 दबाएं. "
    "Press 3 for booking information. "
    "स्लॉट बुकिंग जानकारी के लिए 3 दबाएं. "
    "Press 9 to repeat this menu. "
    "इस मेनू को दोहराने के लिए 9 दबाएं. "
    "Press 0 to talk to an operator. "
    "अधिकारी से बात करने के लिए 0 दबाएं."
)


# ─── Endpoint 1: Incoming Call (Entrypoint) ───────────────────────────────────

@router.post("/incoming")
async def ivr_incoming(request: Request):
    """
    Initial entry point when farmer calls the Twilio number.
    Speaks welcome message and gathers menu selection.
    """
    base_url = str(request.base_url).rstrip("/")
    gather_url = f"{base_url}/api/ivr/gather"

    content = (
        say(WELCOME_MESSAGE)
        + gather(gather_url)
        + say(MAIN_MENU_PROMPT)
        + "</Gather>"
        + say("We did not receive your input. Please call again. Goodbye.")
    )
    return twiml(content)


# ─── Endpoint 2: Gather (Handle Keypress) ──────────────────────────────────────

@router.post("/gather")
@router.post("/menu")  # Alias for backward compatibility
async def ivr_gather(
    request: Request,
    Digits: str = Form(default=""),
    From: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Handles keypress from main menu and routes caller to the appropriate sub-flow.
    """
    base_url = str(request.base_url).rstrip("/")

    # Option 1: Check Booking & Queue Status
    if Digits == "1":
        return await _status_response(From, base_url, db)

    # Option 2: Raise Grievance sub-menu
    if Digits == "2":
        return _grievance_menu_response(base_url)

    # Option 3: Booking Info
    if Digits == "3":
        return _book_info_response(base_url)

    # Option 9: Repeat Menu
    if Digits == "9":
        gather_url = f"{base_url}/api/ivr/gather"
        content = (
            gather(gather_url)
            + say(MAIN_MENU_PROMPT)
            + "</Gather>"
            + say("We did not receive your input. Goodbye.")
        )
        return twiml(content)

    # Option 0: Speak to Helpline Operator
    if Digits == "0":
        content = say(
            "Please hold while we connect your call to the on-duty Mandi Procurement Helpdesk Officer. "
            "कृपया प्रतीक्षा करें, आपकी कॉल मंडी सहायता अधिकारी से जोड़ी जा रही है. "
            "Our office hours are Monday to Saturday, 9 AM to 6 PM. Thank you for calling KissanFlow."
        )
        return twiml(content)

    # Invalid digit — repeat menu
    gather_url = f"{base_url}/api/ivr/gather"
    content = (
        say("Invalid option selected. अमान्य विकल्प.")
        + gather(gather_url)
        + say(MAIN_MENU_PROMPT)
        + "</Gather>"
    )
    return twiml(content)


# ─── Endpoint 3: Check Booking Status by Mobile (Caller ID) ───────────────────

@router.post("/status")
async def ivr_status(
    request: Request,
    From: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Direct endpoint to check status for caller ID.
    Can be called directly by Twilio or redirected from gather.
    """
    base_url = str(request.base_url).rstrip("/")
    return await _status_response(From, base_url, db)


async def _status_response(caller: str, base_url: str, db: AsyncSession) -> Response:
    gather_url = f"{base_url}/api/ivr/gather"
    farmer = await lookup_farmer_by_mobile(caller, db)

    if not farmer:
        content = (
            say(
                "We could not find a registered KissanFlow account linked to your calling number. "
                "आपके नंबर से कोई पंजीकृत किसान खाता नहीं मिला. "
                "Please register at your nearest CSC centre or on the KissanFlow portal."
            )
            + gather(gather_url)
            + say("Press 9 to return to the main menu, or press 0 to speak to an operator.")
            + "</Gather>"
        )
        return twiml(content)

    booking = await get_active_booking(farmer.id, db)
    if not booking:
        content = (
            say(
                f"Hello {farmer.name}. You currently have no active slot bookings in KissanFlow. "
                f"नमस्ते {farmer.name}, वर्तमान में आपकी कोई सक्रिय स्लॉट बुकिंग नहीं है. "
                "To book a slot, visit kissanflow.in or your nearest CSC centre."
            )
            + gather(gather_url)
            + say("Press 9 to return to the main menu.")
            + "</Gather>"
        )
        return twiml(content)

    token = booking["token"]
    centre = booking["centre"]
    crop = booking["crop"]
    status = booking["status"]
    slot_date = booking["slot_date"]
    slot_time = booking["slot_time"]
    spaced_token = ". ".join(list(token))

    if status in ("IN_QUEUE", "ARRIVED"):
        pos = booking.get("queue_position") or "3"
        eta = booking.get("eta_minutes") or "15"
        spoken_en = (
            f"Hello {farmer.name}. Your token {spaced_token} is in queue at {centre}. "
            f"You are number {pos}. Estimated wait: {eta} minutes."
        )
        spoken_hi = (
            f"नमस्ते {farmer.name}। आपका टोकन {spaced_token} {centre} में कतार में है। "
            f"आप कतार में {pos} नंबर पर हैं। अनुमानित प्रतीक्षा समय {eta} मिनट है।"
        )
    elif status == "PROCESSING":
        spoken_en = (
            f"Hello {farmer.name}. Your {crop} produce is currently being weighed and processed at {centre}. "
            f"Please be present at the procurement counter."
        )
        spoken_hi = (
            f"नमस्ते {farmer.name}। आपकी {crop} की फसल वर्तमान में {centre} में प्रोसेस हो रही है।"
        )
    else:  # BOOKED
        spoken_en = (
            f"Hello {farmer.name}. Your {crop} slot is confirmed. "
            f"Token number: {spaced_token} at {centre} on {slot_date} at {slot_time}."
        )
        spoken_hi = (
            f"नमस्ते {farmer.name}। आपकी {crop} बुकिंग पक्की है। "
            f"टोकन नंबर: {spaced_token}, {centre}, दिनांक {slot_date}, समय {slot_time}।"
        )

    content = (
        say(f"{spoken_en} {spoken_hi}")
        + gather(gather_url)
        + say("Press 9 to return to the main menu, or press 0 to speak to an operator.")
        + "</Gather>"
        + say("Thank you for calling KissanFlow. Goodbye.")
    )
    return twiml(content)


# ─── Endpoint 4: Raise Grievance via IVR ──────────────────────────────────────

def _grievance_menu_response(base_url: str) -> Response:
    """Plays grievance category options and gathers single digit."""
    action_url = f"{base_url}/api/ivr/grievance"
    content = (
        gather(action_url)
        + say(
            "Press 1 for Slot Issue. स्लॉट समस्या के लिए 1 दबाएं. "
            "Press 2 for Payment Issue. भुगतान समस्या के लिए 2 दबाएं. "
            "Press 3 for Quality Dispute. गुणवत्ता विवाद के लिए 3 दबाएं. "
            "Press 4 for Weighment Dispute. वजन विवाद के लिए 4 दबाएं. "
            "Press 9 to return to the main menu."
        )
        + "</Gather>"
        + say("We did not receive your input. Returning to main menu.")
        + f'<Redirect method="POST">{base_url}/api/ivr/incoming</Redirect>'
    )
    return twiml(content)


@router.post("/grievance")
async def ivr_grievance(
    request: Request,
    Digits: str = Form(default=""),
    From: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Receives grievance category keypress, creates a DB record linked to the caller,
    and speaks back the generated reference ID.
    """
    base_url = str(request.base_url).rstrip("/")
    gather_url = f"{base_url}/api/ivr/gather"

    if Digits == "9":
        return twiml(
            gather(gather_url)
            + say(MAIN_MENU_PROMPT)
            + "</Gather>"
        )

    category_map = {
        "1": GrievanceCategory.SLOT_ISSUE,
        "2": GrievanceCategory.PAYMENT_ISSUE,
        "3": GrievanceCategory.QUALITY_DISPUTE,
        "4": GrievanceCategory.WEIGHMENT_DISPUTE,
    }
    category = category_map.get(Digits)

    if not category:
        return twiml(
            say("Invalid grievance category selected.")
            + gather(gather_url)
            + say(MAIN_MENU_PROMPT)
            + "</Gather>"
        )

    farmer = await lookup_farmer_by_mobile(From, db)
    if not farmer:
        content = say(
            "We could not verify your registered account from this number. "
            "Please call from your registered mobile number or visit kissanflow.in to lodge a grievance. Goodbye."
        )
        return twiml(content)

    ref_id = await create_ivr_grievance(farmer.id, category, db)
    spaced_ref = ". ".join(list(ref_id))

    content = (
        say(
            f"Your grievance has been registered successfully. Your reference number is {spaced_ref}. "
            f"आपकी शिकायत सफलतापूर्वक दर्ज कर ली गई है। आपका संदर्भ नंबर {spaced_ref} है। "
            "Our grievance redressal officer will review your ticket within 48 hours."
        )
        + gather(gather_url)
        + say("Press 9 to return to the main menu, or press 0 to speak to an operator.")
        + "</Gather>"
        + say("Thank you for calling KissanFlow Helpline. Goodbye.")
    )
    return twiml(content)


# ─── Endpoint 5: Slot Booking Guidance ────────────────────────────────────────

@router.post("/book-info")
async def ivr_book_info(request: Request):
    """
    Endpoint that speaks slot booking guidance and CSC information.
    """
    base_url = str(request.base_url).rstrip("/")
    return _book_info_response(base_url)


def _book_info_response(base_url: str) -> Response:
    gather_url = f"{base_url}/api/ivr/gather"
    content = (
        say(
            "To book a procurement slot, visit kissanflow.in or call your local CSC Common Service Centre. "
            "Please keep your Aadhaar number and land records ready. "
            "स्लॉट बुक करने के लिए, kissanflow.in पर जाएं या नजदीकी सीएससी केंद्र पर संपर्क करें। "
            "अपना आधार नंबर और खतौनी तैयार रखें।"
        )
        + gather(gather_url)
        + say("Press 9 to return to the main menu.")
        + "</Gather>"
        + say("Thank you for calling KissanFlow. Goodbye.")
    )
    return twiml(content)