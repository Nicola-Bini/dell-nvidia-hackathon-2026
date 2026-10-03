"""Routes only the owner's inbox credential may call (SCHEMA 8.6)."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_owner

router = APIRouter(prefix="/owner", tags=["owner only"])


@router.post("/changes/{change_id}/approve")
def approve(change_id: int, _: str = Depends(require_owner)) -> dict:
    raise HTTPException(status_code=501, detail="approve lands in wp4")


@router.post("/changes/{change_id}/reject")
def reject(change_id: int, _: str = Depends(require_owner)) -> dict:
    raise HTTPException(status_code=501, detail="reject lands in wp4")


@router.post("/changes/{change_id}/revert")
def revert(change_id: int, _: str = Depends(require_owner)) -> dict:
    raise HTTPException(status_code=501, detail="revert lands in wp4")


@router.post("/verify")
def verify(_: str = Depends(require_owner)) -> dict:
    raise HTTPException(status_code=501, detail="verify lands in wp4")
