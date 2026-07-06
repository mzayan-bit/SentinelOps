from __future__ import annotations

from math import ceil
from typing import Generic, Literal, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")
SortOrder = Literal["asc", "desc"]


class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    page: int | None = Field(default=None, ge=1)
    page_size: int | None = Field(default=None, ge=1, le=200)
    sort_by: str | None = None
    order: SortOrder = "desc"

    @property
    def effective_limit(self) -> int:
        return self.page_size or self.limit

    @property
    def effective_offset(self) -> int:
        if self.page is not None:
            return (self.page - 1) * self.effective_limit
        return self.offset

    @property
    def current_page(self) -> int:
        if self.page is not None:
            return self.page
        return (self.effective_offset // self.effective_limit) + 1


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    next: int | None
    previous: int | None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


def pagination_params(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=200),
    sort_by: str | None = Query(default=None),
    order: SortOrder = Query(default="desc"),
) -> PaginationParams:
    return PaginationParams(
        limit=limit,
        offset=offset,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        order=order,
    )


def build_page_meta(total: int, params: PaginationParams) -> PageMeta:
    page_size = params.effective_limit
    page = params.current_page
    pages = ceil(total / page_size) if total else 0
    return PageMeta(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        next=page + 1 if pages and page < pages else None,
        previous=page - 1 if page > 1 and pages else None,
    )


def paginate_items(items: list[T], params: PaginationParams) -> tuple[list[T], PageMeta]:
    total = len(items)
    start = params.effective_offset
    end = start + params.effective_limit
    return items[start:end], build_page_meta(total, params)
