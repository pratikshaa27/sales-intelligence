from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str = "Operation completed successfully"


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMeta
