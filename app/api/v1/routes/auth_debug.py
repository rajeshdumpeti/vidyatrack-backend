from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    # Returns the decoded user context from JWT: user_id, school_id, role
    return current_user
