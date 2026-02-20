import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse
from urllib.request import Request, urlopen

from app.core.config import settings


def _strapi_origin() -> str:
    parsed = urlparse(settings.strapi_base_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _to_absolute_media_url(value: str) -> str:
    if not value.startswith("/"):
        return value
    return f"{_strapi_origin()}{value}"


def _normalize_media_urls(payload: Any) -> Any:
    if isinstance(payload, dict):
        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if key in {"url", "previewUrl"} and isinstance(value, str):
                normalized[key] = _to_absolute_media_url(value)
            else:
                normalized[key] = _normalize_media_urls(value)
        return normalized

    if isinstance(payload, list):
        return [_normalize_media_urls(item) for item in payload]

    return payload


def _merge_query_items(
    raw_query: str | None,
    extra_query_params: dict[str, str | int | None] | None = None,
) -> list[tuple[str, str]]:
    query_items = parse_qsl(raw_query or "", keep_blank_values=True)
    if not extra_query_params:
        return query_items

    for key, value in extra_query_params.items():
        if value is None:
            continue
        query_items = [(k, v) for k, v in query_items if k != key]
        query_items.append((key, str(value)))
    return query_items


def fetch_collection(
    content_type: str,
    raw_query: str | None = None,
    extra_query_params: dict[str, str | int | None] | None = None,
) -> dict[str, Any]:
    """
    Fetch a Strapi collection/document list with auth token support.
    Example raw_query:
      "populate=*&filters[slug][$eq]=home&pagination[pageSize]=10"
    """
    if not settings.strapi_api_token:
        raise ValueError("STRAPI_API_TOKEN is not configured")

    query_items = _merge_query_items(
        raw_query=raw_query, extra_query_params=extra_query_params
    )
    query_keys = {key for key, _ in query_items}
    if "populate" not in query_keys:
        query_items.append(("populate", "*"))

    query = urlencode(query_items, doseq=True)
    url = f"{settings.strapi_base_url.rstrip('/')}/{content_type.lstrip('/')}"
    if query:
        url = f"{url}?{query}"

    request = Request(
        url=url,
        headers={
            "Authorization": f"Bearer {settings.strapi_api_token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=settings.strapi_timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
            payload = json.loads(response_body)
            return _normalize_media_urls(payload)
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Strapi HTTP {exc.code}: {error_body or exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to reach Strapi: {exc.reason}") from exc
