from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.services.strapi import fetch_collection

router = APIRouter(prefix="/cms", tags=["cms"])


def _school_filter_params(
    school_id: int | None,
    school_code: str | None,
) -> dict[str, str | int]:
    params: dict[str, str | int] = {}
    if school_id is not None:
        params["filters[school_id][$eq]"] = school_id
    if school_code:
        params["filters[school_code][$containsi]"] = school_code.strip()
    return params


@router.get("/{content_type}")
def get_cms_collection(
    content_type: str,
    query: str | None = Query(
        default=None,
        description="Raw Strapi query string, e.g. filters[slug][$eq]=home&populate=*",
    ),
    school_id: int | None = Query(default=None),
    school_code: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        return fetch_collection(
            content_type=content_type,
            raw_query=query,
            extra_query_params=_school_filter_params(
                school_id=school_id, school_code=school_code
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
