import os
from fastapi import APIRouter, Form, Request, Response, BackgroundTasks
from twilio.request_validator import RequestValidator

from farmer_store import mark_message_processed
from services.whatsapp_service import handle_incoming_message

router = APIRouter()

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
SKIP_TWILIO_SIGNATURE = os.getenv("SKIP_TWILIO_SIGNATURE", "false").lower() == "true"


@router.post("/webhook/whatsapp")
@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    From:              str = Form(...),
    Body:              str = Form(""),
    NumMedia:          str = Form("0"),
    MediaUrl0:         str = Form(None),
    MediaContentType0: str = Form(None),
    Latitude:          str = Form(None),
    Longitude:         str = Form(None),
    MessageSid:        str = Form(None),
    ProfileName:       str = Form(None),
    SmsStatus:         str = Form(None),
):
    # 1. Twilio Signature Validation
    if not SKIP_TWILIO_SIGNATURE and TWILIO_AUTH_TOKEN:
        signature = request.headers.get("X-Twilio-Signature")
        if not signature:
            print("⚠️ [Webhook] Missing X-Twilio-Signature header.")
            return Response(status_code=403, content="Missing signature")

        # Reconstruct public URL
        if PUBLIC_BASE_URL:
            url = f"{PUBLIC_BASE_URL.rstrip('/')}{request.url.path}"
        else:
            url = str(request.url)

        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        form_params = await request.form()
        params = dict(form_params)

        if not validator.validate(url, params, signature):
            print(f"⚠️ [Webhook] Twilio signature validation failed for {url}")
            return Response(status_code=403, content="Invalid signature")

    # 2. Deduplication check
    if MessageSid:
        is_new = mark_message_processed(MessageSid)
        if not is_new:
            print(f"[WhatsApp] Duplicate message {MessageSid} ignored.")
            return Response(content="<Response/>", media_type="text/xml")

    form_data = {
        "From": From,
        "Body": Body,
        "NumMedia": NumMedia,
        "MediaUrl0": MediaUrl0,
        "MediaContentType0": MediaContentType0,
        "Latitude": Latitude,
        "Longitude": Longitude,
        "MessageSid": MessageSid,
        "ProfileName": ProfileName,
    }

    # 3. Offload processing to background task; return <Response/> immediately
    background_tasks.add_task(handle_incoming_message, form_data)
    return Response(content="<Response/>", media_type="text/xml")


@router.get("/whatsapp/test")
def test_webhook():
    return {"status": "WhatsApp webhook running ✅"}