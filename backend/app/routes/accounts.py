from fastapi import APIRouter, Depends, HTTPException, status

from app.account_store import AccountStoreError, read_accounts_state
from app.audit import audit_event
from app.dependencies import require_bearer_payload
from app.models import AccountsStateResponse


router = APIRouter(prefix="/accounts", tags=["analytics"])


@router.get(
    "",
    response_model=AccountsStateResponse,
    summary="Get account states",
    description="Returns current account states for the main operational players.",
)
def get_accounts(_: dict = Depends(require_bearer_payload)) -> AccountsStateResponse:
    try:
        return read_accounts_state()
    except AccountStoreError as exc:
        audit_event("error", f"action=read_accounts status=failure reason={type(exc).__name__}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Account storage service is temporarily unavailable.",
        ) from exc
