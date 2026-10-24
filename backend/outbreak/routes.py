from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
import os
from services.db import get_db

router = APIRouter()

def verify_admin_token(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
    authorization: str | None = Header(None),
    token: str | None = Query(None),
):
    """
    Requirement 6: Require env ADMIN_TOKEN or return 404.
    If ADMIN_TOKEN is not set or does not match, return 404 (not 401/403).
    """
    expected = os.getenv("ADMIN_TOKEN")
    if not expected or not expected.strip():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    provided = x_admin_token or token
    if not provided and authorization:
        if authorization.lower().startswith("bearer "):
            provided = authorization[7:].strip()
        else:
            provided = authorization.strip()

    if not provided or provided.strip() != expected.strip():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    return True


@router.post("/evaluate/{case_id}")
async def evaluate_outbreak_case(
    case_id: str,
    admin: bool = Depends(verify_admin_token),
):
    """
    Admin endpoint to trigger or simulate evaluation of a disease case.
    Privacy: Never returns raw phone numbers.
    """
    from outbreak.service import evaluate_case
    result = await evaluate_case(case_id)
    # Mask any phone numbers in result
    return _sanitize_result(result)


@router.post("/new-detection")
async def new_detection(
    data: dict,
    admin: bool = Depends(verify_admin_token),
):
    """
    Legacy endpoint for new detection.
    Writing to detections table is stopped per requirement 4.
    Requires ADMIN_TOKEN and returns 404 if invalid.
    """
    case_id = data.get("case_id")
    if case_id:
        from outbreak.service import evaluate_case
        result = await evaluate_case(case_id)
        return {"status": "evaluated", "result": _sanitize_result(result)}

    return {
        "status": "deprecated",
        "message": "Direct detection table insertion is discontinued. Use disease_cases.",
    }


def _sanitize_result(res: dict) -> dict:
    if not isinstance(res, dict):
        return {"status": "done"}
    cleaned = {}
    for k, v in res.items():
        if "phone" in k.lower():
            continue
        if isinstance(v, list):
            cleaned[k] = [_sanitize_result(item) if isinstance(item, dict) else item for item in v]
        elif isinstance(v, dict):
            cleaned[k] = _sanitize_result(v)
        else:
            cleaned[k] = v
    return cleaned