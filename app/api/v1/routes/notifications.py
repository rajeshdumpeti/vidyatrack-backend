from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.notifications import OutboxRunOut
from app.workers.outbox_worker import process_outbox_batch

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/outbox/run", response_model=OutboxRunOut)
def run_outbox_worker(
    db: Session = Depends(get_db),
    _user: dict = Depends(require_management),
):
    processed = process_outbox_batch(db, limit=50)
    return OutboxRunOut(processed=processed)
