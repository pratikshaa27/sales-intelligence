import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, require_permission, require_superadmin
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.product import ProductStatus
from app.repositories.product_repository import ProductCategoryRepository
from app.schemas.common import PaginatedData, SuccessResponse
from app.schemas.product import (
    CreateProductCategoryRequest,
    CreateProductRequest,
    ProductCategoryOut,
    ProductDocumentOut,
    ProductListItem,
    ProductOut,
    UpdateProductRequest,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/categories", response_model=SuccessResponse[list[ProductCategoryOut]])
async def list_categories(
    principal: Principal = Depends(require_permission("products.view")),
    db: AsyncSession = Depends(get_db),
):
    categories = await ProductCategoryRepository(db).list_all()
    return SuccessResponse(data=[ProductCategoryOut.model_validate(c) for c in categories])


@router.post("/categories", response_model=SuccessResponse[ProductCategoryOut], status_code=201)
async def create_category(
    body: CreateProductCategoryRequest,
    principal: Principal = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    repo = ProductCategoryRepository(db)
    if await repo.get_by_name(body.name):
        raise AppError("CONFLICT", f"Category '{body.name}' already exists", 409)
    category = await repo.create(name=body.name, description=body.description)
    await db.commit()
    return SuccessResponse(
        data=ProductCategoryOut.model_validate(category), message="Category created"
    )


@router.get("", response_model=SuccessResponse[PaginatedData[ProductListItem]])
async def list_products(
    search: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    industry: str | None = Query(None),
    status: ProductStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(require_permission("products.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    items, pagination = await service.list_paginated(
        organization_id=principal.organization_id,
        search=search,
        category_id=category_id,
        industry=industry,
        status=status,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[ProductListItem.model_validate(p) for p in items], pagination=pagination
    )
    return SuccessResponse(data=data)


@router.post("", response_model=SuccessResponse[ProductOut], status_code=201)
async def create_product(
    body: CreateProductRequest,
    principal: Principal = Depends(require_permission("products.create")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    product = await service.create(
        organization_id=principal.organization_id, user_id=principal.user.id, body=body
    )
    return SuccessResponse(data=ProductOut.model_validate(product), message="Product created")


@router.get("/{product_id}", response_model=SuccessResponse[ProductOut])
async def get_product(
    product_id: uuid.UUID,
    principal: Principal = Depends(require_permission("products.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    product = await service.get(organization_id=principal.organization_id, product_id=product_id)
    return SuccessResponse(data=ProductOut.model_validate(product))


@router.patch("/{product_id}", response_model=SuccessResponse[ProductOut])
async def update_product(
    product_id: uuid.UUID,
    body: UpdateProductRequest,
    principal: Principal = Depends(require_permission("products.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    product = await service.update(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        product_id=product_id,
        body=body,
    )
    return SuccessResponse(data=ProductOut.model_validate(product), message="Product updated")


@router.delete("/{product_id}", response_model=SuccessResponse[dict])
async def delete_product(
    product_id: uuid.UUID,
    principal: Principal = Depends(require_permission("products.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    await service.delete(
        organization_id=principal.organization_id, user_id=principal.user.id, product_id=product_id
    )
    return SuccessResponse(data={}, message="Product deleted")


@router.post("/{product_id}/archive", response_model=SuccessResponse[ProductOut])
async def archive_product(
    product_id: uuid.UUID,
    principal: Principal = Depends(require_permission("products.archive")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    product = await service.set_status(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        product_id=product_id,
        status=ProductStatus.ARCHIVED,
    )
    return SuccessResponse(data=ProductOut.model_validate(product), message="Product archived")


@router.post("/{product_id}/restore", response_model=SuccessResponse[ProductOut])
async def restore_product(
    product_id: uuid.UUID,
    principal: Principal = Depends(require_permission("products.archive")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    product = await service.set_status(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        product_id=product_id,
        status=ProductStatus.DRAFT,
    )
    return SuccessResponse(
        data=ProductOut.model_validate(product), message="Product restored to draft"
    )


@router.post("/{product_id}/reindex", response_model=SuccessResponse[ProductOut])
async def reindex_product(
    product_id: uuid.UUID,
    principal: Principal = Depends(require_permission("products.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    product = await service.reindex(
        organization_id=principal.organization_id, user_id=principal.user.id, product_id=product_id
    )
    return SuccessResponse(
        data=ProductOut.model_validate(product), message="Embedding generation queued"
    )


@router.get("/{product_id}/documents", response_model=SuccessResponse[list[ProductDocumentOut]])
async def list_product_documents(
    product_id: uuid.UUID,
    principal: Principal = Depends(require_permission("products.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    await service.get(organization_id=principal.organization_id, product_id=product_id)
    documents = await service.documents.list_for_product(product_id)
    return SuccessResponse(data=[ProductDocumentOut.model_validate(d) for d in documents])


@router.post(
    "/{product_id}/documents", response_model=SuccessResponse[ProductDocumentOut], status_code=201
)
async def upload_product_document(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    principal: Principal = Depends(require_permission("products.edit")),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    service = ProductService(db)
    document = await service.upload_document(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        product_id=product_id,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    return SuccessResponse(
        data=ProductDocumentOut.model_validate(document), message="Document uploaded"
    )
