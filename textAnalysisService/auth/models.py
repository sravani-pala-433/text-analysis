from datetime import datetime

from pgvector.utils import Vector
from sqlalchemy import Column, String, DateTime, ForeignKey, TIMESTAMP, ARRAY, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from uuid import uuid4

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from textAnalysisService.auth.utils import hashing

from textAnalysisService.auth.config.database import Base
from textAnalysisService.auth.utils.custom_types import VectorType


class RegisteredUser(Base):
    __tablename__ = 'RegisteredUser'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_name = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    textsets = relationship("TextSet", back_populates="registered_user")

    def __init__(self, user_name, email, password):
        self.user_name = user_name
        self.email = email
        self.hashed_password = hashing.hash_password(password)
        self.created_at = datetime.now()

    def check_password(self, password):
        return hashing.verify_password(self.hashed_password, password)


class TextSet(Base):
    __tablename__ = "TextSet"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)  # Rename from textsetId to id
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    owner_id = Column(UUID(as_uuid=True), ForeignKey('RegisteredUser.id'))  # Rename from registered_user_id to owner_id

    registered_user = relationship("RegisteredUser", back_populates="textsets")
    entry_count = Column(Integer, default=0)
    # Relationships
    text_items = relationship('TextItem', back_populates='text_set')
    attributes = relationship('Attribute', back_populates='text_set')


class TextItem(Base):
    __tablename__ = 'TextItem'

    # Columns
    text_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text_set_id = Column(UUID(as_uuid=True), ForeignKey('TextSet.id'), nullable=False)
    creator_id = Column(String, nullable=False)
    creator_name = Column(String, nullable=False)
    text_content = Column(String, nullable=False)
    post_date = Column(DateTime, nullable=False)
    external_item_id = Column(String, nullable=True)
    parent_external_item_id = Column(String, nullable=True)

    embeddings = Column(VectorType(size=384), nullable=False)
    pca_vector = Column(VectorType(size=3), nullable=False)

    text_set = relationship('TextSet', back_populates='text_items')


class Attribute(Base):
    __tablename__ = 'Attribute'
    attribute_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attribute_type = Column(String, nullable=False)
    attribute_name = Column(String, nullable=False)
    num_range_low = Column(Integer, nullable=True)
    num_range_high = Column(Integer, nullable=True)
    select_choices = Column(ARRAY(String), nullable=True)
    text_set_id = Column(UUID(as_uuid=True), ForeignKey('TextSet.id'), nullable=False)
    text_set = relationship("TextSet", back_populates="attributes")
    attribute_values = relationship('AttributeValue', back_populates='attribute')


class AttributeValue(Base):
    __tablename__ = 'AttributeValue'
    attribute_value_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    num_value = Column(Integer, nullable=True)
    text_value = Column(String, nullable=True)
    select_value = Column(ARRAY(String), nullable=True)
    attribute_id = Column(UUID(as_uuid=True), ForeignKey('Attribute.attribute_id'), nullable=False)
    creator_id = Column(String, nullable=False)
    attribute = relationship('Attribute', back_populates='attribute_values')
