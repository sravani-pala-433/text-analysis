# schemas.py
import math

from pydantic import BaseModel, EmailStr, UUID4, Field, validator, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Literal, TypeVar, Generic, Dict

from pydantic.generics import GenericModel

from textAnalysisService.auth.config.database import Base


class CreateTextSet(BaseModel):
    title: str
    description: str

    class Config:
        from_attributes = True


class TextSetResponse(CreateTextSet):
    id: UUID
    created_at: datetime
    entry_count: int

    class Config:
        from_attributes = True


class AttributeResponse(BaseModel):
    attribute_id: UUID
    attribute_type: str
    attribute_name: str
    num_range_low: int
    num_range_high: int
    select_choices: List[str] = Field(..., description="A list representing a attribute options")

    class Config:
        from_attributes = True


class GetResponse(CreateTextSet):
    textsetId: UUID
    registered_user_id: UUID  # Include user ID in response

    class Config:
        from_attributes = True


# schemas.py

class RegisteredUserCreate(BaseModel):
    user_name: str
    email: EmailStr
    password: str  # Plain password input

    class Config:
        from_attributes = True


class RegisteredUserResponse(BaseModel):
    id: UUID
    user_name: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class JWTTokenPayload(BaseModel):
    user_id: UUID
    username: str
    exp: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: UUID
    name: str


T = TypeVar("T")


class TextSetSearchCriteria(BaseModel):
    title: Optional[str] = None
    textSetIdsIn: Optional[List[UUID4]] = None  # New criterion
    created_id: Optional[UUID4] = None
    created_at_from: Optional[datetime] = None
    created_at_to: Optional[datetime] = None


class TextItemSearchCriteria(BaseModel):
    text_set_ids_in: Optional[List[UUID4]] = None  # New criterion
    external_item_id_in: Optional[List[UUID4]] = None
    parent_external_item_id_in: Optional[List[UUID4]] = None
    creator_id: Optional[UUID4] = None
    creator_name: Optional[str] = None
    post_date_from: Optional[datetime] = None
    post_date_to: Optional[datetime] = None
    created_at_from: Optional[datetime] = None
    created_at_to: Optional[datetime] = None
    attributes: Optional[Dict[UUID4, str]] = None  # Maps attribute_id (UUID4) to attribute_value (string)


class TextSetSearchResponse(BaseModel):
    items: List[TextSetResponse]
    total: int

class TextValueAttributeValue(BaseModel):
    text_value: str

class TextValueCriteria(BaseModel):
    attribute_id: UUID
    text_value: Optional[str]= None


class TextContentRow(BaseModel):
    creator_id: str
    creator_name: str
    text_content: str
    post_date: datetime
    external_item_id: Optional[str] = None
    parent_external_item_id: Optional[str] = None
    attributes: dict


class TextEmbeddingRow(TextContentRow):
    embeddings: List[float] = Field(..., description="A list representing a vector")
    pca_vector: List[float] = Field(..., description="A list representing a vector")


class SearchResultItem(BaseModel):
    text_item_id: UUID4
    text_content: str
    similarity: float
    distance: float
    distance_type: str


class SearchByItemRequest(BaseModel):
    target_text_item_id: Optional[UUID4] = None
    target_text_item_id_in: List[UUID4]= Field(default=[])
    query_string: Optional[str] = None
    creator_id: Optional[str] = None
    distance: float = Field(default=0.5, gt=0, le=1)
    distance_algo: Optional[Literal["euclidean", "cosine"]] = "cosine"
    max_returns: int = Field(default=500, ge=10, le=1000)

    @field_validator("distance_algo")
    def validate_order_type(cls, value):
        if value not in ("cosine", "euclidean"):
            raise ValueError("distance_algo must be 'euclidean' or 'cosine'")
        return value

class TextItemsContent(BaseModel):
    text_item_id: UUID4
    text_content: str

    class Config:
        from_attributes = True

class TextEmbeddingRowV1(TextItemsContent):
    embeddings: List[float] = Field(..., description="A list representing a vector")
    pca_vector: List[float] = Field(..., description="A list representing a vector")


class TextItemResponse(BaseModel):
    text_item_id: UUID4
    text_set_id: UUID4
    creator_id: Optional[str] = None
    creator_name: Optional[str] = None
    text_content: str
    post_date: datetime
    external_item_id: Optional[str] = None
    parent_external_item_id: Optional[str] = None
    # embeddings: List[float]
    pca_vector: List[float]

    class Config:
        from_attributes = True


class TextItemListResponse(BaseModel):
    items: List[TextItemResponse]


class AttributeListResponse(BaseModel):
    items: List[AttributeResponse]


class TextSetListResponse(BaseModel):
    items: List[TextSetResponse]


class PaginatedResponse(GenericModel, Generic[T]):
    total: int
    page: int
    page_size: int
    items: List[T]


class Pagination(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=5000)
    order_by: Optional[str] = None  # Field to specify the column for ordering
    order_type: Optional[Literal["asc", "desc"]] = "asc"  # Default is ascending

    @field_validator("order_type")
    def validate_order_type(cls, value):
        if value not in ("asc", "desc"):
            raise ValueError("order_type must be 'asc' or 'desc'")
        return value


def map_schema_to_model(schema: BaseModel, model: Base) -> Base:
    """
    Maps a Pydantic schema to an SQLAlchemy model.

    Args:
        schema (BaseModel): The Pydantic schema.
        model (Base): The SQLAlchemy model instance.

    Returns:
        Base: The updated SQLAlchemy model instance.
    """
    for key, value in schema.model_dump(exclude_unset=True).items():
        setattr(model, key, value)
    return model


