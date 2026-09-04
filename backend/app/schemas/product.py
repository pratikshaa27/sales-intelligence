import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.product import EmbeddingStatus, ProductStatus


class ProductCategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str

    model_config = {"from_attributes": True}


class CreateProductCategoryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    description: str = ""


class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=1, max_length=64)
    category_id: uuid.UUID | None = None
    short_description: str = Field(default="", max_length=500)
    detailed_description: str = ""
    target_industries: list[str] = Field(default_factory=list)
    target_company_size: list[str] = Field(default_factory=list)
    target_geographic_regions: list[str] = Field(default_factory=list)
    business_problems: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    pricing_model: str = ""
    minimum_contract_value: float | None = None
    required_technical_capabilities: list[str] = Field(default_factory=list)
    supported_integrations: list[str] = Field(default_factory=list)
    ideal_customer_profile: str = ""
    common_use_cases: list[str] = Field(default_factory=list)
    competitor_alternatives: list[str] = Field(default_factory=list)


class CreateProductRequest(ProductBase):
    pass


class UpdateProductRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=64)
    status: ProductStatus | None = None
    category_id: uuid.UUID | None = None
    short_description: str | None = Field(default=None, max_length=500)
    detailed_description: str | None = None
    target_industries: list[str] | None = None
    target_company_size: list[str] | None = None
    target_geographic_regions: list[str] | None = None
    business_problems: list[str] | None = None
    key_features: list[str] | None = None
    benefits: list[str] | None = None
    pricing_model: str | None = None
    minimum_contract_value: float | None = None
    required_technical_capabilities: list[str] | None = None
    supported_integrations: list[str] | None = None
    ideal_customer_profile: str | None = None
    common_use_cases: list[str] | None = None
    competitor_alternatives: list[str] | None = None


class ProductDocumentOut(BaseModel):
    id: uuid.UUID
    file_name: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductOut(ProductBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    status: ProductStatus
    embedding_status: EmbeddingStatus
    category: ProductCategoryOut | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListItem(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    short_description: str
    status: ProductStatus
    embedding_status: EmbeddingStatus
    category: ProductCategoryOut | None = None
    target_industries: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
