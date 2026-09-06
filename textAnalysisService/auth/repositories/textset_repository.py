import uuid

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import array

from textAnalysisService.auth import models
from textAnalysisService.auth.models import TextSet, TextItem, Attribute, AttributeValue
from textAnalysisService.auth.schema import *
from sqlalchemy import or_, and_, desc, asc, text, func,  select
from sqlalchemy import update

import logging

logger = logging.getLogger(__name__)


class TextSetRepository:
    def __init__(self, session: Session):
        self.session = session

    async def create_text_set(self, text_set_request: CreateTextSet, user_id: UUID) -> models.TextSet:
        """create a text set from the database"""
        new_text_set = TextSet(
            title=text_set_request.title,
            description=text_set_request.description,
            owner_id=user_id  # Ensure this is a UUID
        )
        self.session.add(new_text_set)
        self.session.flush()  # Executes the INSERT statement
        return new_text_set

    async def get_text_set(self) -> list[models.TextSet]:
        """Get all text sets from the database"""
        return self.session.query(TextSet).all()

    async def get_text_sets_by_owner(self, owner_id: UUID) -> list[models.TextSet]:
        textsets = self.session.query(TextSet).filter(TextSet.owner_id == owner_id).all()
        return textsets

    async def get_attributes_by_text_set_id(self, text_set_id: UUID) -> list[models.Attribute]:
        attributes = self.session.query(Attribute).filter(Attribute.text_set_id == text_set_id).all()
        return attributes

    async def get_attributes_by_text_set_id(self, text_set_id: UUID) -> list[models.Attribute]:
        attributes = self.session.query(Attribute).filter(Attribute.text_set_id == text_set_id).all()
        return attributes

    async def increment_item_count(self, text_set_id: UUID, inserted_count: int) -> int:
        self.session.query(TextSet).filter_by(id=text_set_id).update({
            TextSet.entry_count: TextSet.entry_count + inserted_count
        })
        return inserted_count

    async def search_text_sets_by_criteria(self, criteria: TextSetSearchCriteria, pagination: Pagination):
        """

        :param criteria:
        :param pagination:
        :return:
        """
        textset_search_query = self.session.query(TextSet)
        if criteria.title:
            pattern = f"%{criteria.title}%"
            textset_search_query = textset_search_query.filter(TextSet.title.like(f"%{criteria.title}%"))
        if criteria.created_id:
            textset_search_query = textset_search_query.filter(TextSet.owner_id == criteria.created_id)
        if criteria.created_at_from:
            textset_search_query = textset_search_query.filter(
                TextSet.created_at.between(criteria.created_at_from, criteria.created_at_to))
        if criteria.textSetIdsIn:
            textset_search_query = textset_search_query.filter(TextSet.id.in_(criteria.textSetIdsIn))

        if pagination.order_by:
            column = getattr(TextSet, pagination.order_by, None)
            if column:
                if pagination.order_type == "desc":
                    textset_search_query = textset_search_query.order_by(desc(column))
                else:
                    textset_search_query = textset_search_query.order_by(asc(column))
            else:
                raise ValueError(f"Invalid order_by column: {pagination.order_by}")
        total = textset_search_query.count()
        logger.info(f"textset_search_query {str(textset_search_query)}")
        results = textset_search_query.offset((pagination.page - 1) * pagination.page_size).limit(
            pagination.page_size).all()

        return {"total": total, "items": results}

    async def create_text_items(self, text_items_list: list[TextSet]) -> int:
        """create a text set from the database"""
        logger.debug(f"create_text_items {len(text_items_list)} : first object : {text_items_list[0]}")
        self.session.add_all(text_items_list)
        # self.session.bulk_insert_mappings(text_items_list, return_defaults=False)
        # self.session.flush()  # Executes the INSERT statement
        return len(text_items_list)

    async def create_attributes(self, attribute_list: list[Attribute]) -> int:
        """create a text set from the database"""
        logger.debug(f"create_attributes {len(attribute_list)} : first object : {attribute_list}")
        self.session.add_all(attribute_list)
        self.session.flush()  # Executes the INSERT statement
        return len(attribute_list)

    async def update_attribute(self, attribute_lsit: list[Attribute]) -> int:
        """create a text set from the database"""
        logger.debug(f"create_attribute_values {len(attribute_lsit)} ")
        for item in attribute_lsit:
            stmt = (
                update(Attribute)
                .where(Attribute.attribute_id == item.attribute_id)
                .values(
                    select_choices=item.select_choices,
                    num_range_low=item.num_range_low,
                    num_range_high=item.num_range_high
                )
            )
            self.session.execute(stmt)
        return len(attribute_lsit)

    async def create_attribute_values(self, attribute_value_list: list[AttributeValue]) -> int:
        """create a text set from the database"""
        logger.debug(f"create_attribute_values {len(attribute_value_list)} ")
        for item in attribute_value_list:
            logger.debug(
                f" attribute_value_list  item.creator_id {item.creator_id} item.attribute_id{item.attribute_id} ")

            existing_item = self.session.query(AttributeValue).filter(AttributeValue.attribute_id == item.attribute_id,
                                                                      AttributeValue.creator_id == item.creator_id).first()
            if existing_item:
                logger.debug(f" existing_item found hence updating {existing_item.__dict__} ")
                # If the item exists, update it
                existing_item.num_value = item.num_value
                existing_item.text_value = item.text_value
                # existing_item.creator_name = item.creator_name
                existing_item.select_value = item.select_value
            else:
                # If it does not exist, add the new item
                logger.debug(f" new item is inserting  {item.__dict__} ")
                self.session.add(item)
                self.session.flush()  # Executes the INSERT statement
        return len(attribute_value_list)

    async def search_all_text_items_by_criteria(self, text_set_id: uuid, criteria:SearchByItemRequest, target_embedings) -> list[
        models.TextItem]:
        """

        :param criteria:
        :param pagination:
        :return:
        """
        if criteria.target_text_item_id_in:
            target_text_item_ids = criteria.target_text_item_id_in
        logger.debug(f" text_set_id {text_set_id} : search criteria : {target_embedings}")
        text_item_search_query = """
                    WITH distances AS (
                        SELECT
                            text_item_id,
                            text_content,
                            pca_vector,
                            embeddings,
                            (embeddings <=>  CAST(:target_embedings AS vector)) AS distance
                        FROM "TextItem"
                        WHERE text_set_id = :text_set_id
                     """
        if criteria.target_text_item_id_in:
            text_item_search_query += """
                         AND text_item_id = ANY(:text_item_ids)
                     """
        text_item_search_query += """
                    )
                    SELECT *, 1 - distance AS similarity
                    FROM distances
                    WHERE distance < :distance_threshold
                    ORDER BY distance
                    LIMIT :limit;
                    """
        params = {
            'target_embedings': target_embedings,
            'text_set_id': text_set_id,
            'distance_threshold': criteria.distance,
            'limit': criteria.max_returns
        }
        if criteria.target_text_item_id_in:
            params['text_item_ids'] = criteria.target_text_item_id_in
        # Execute the query with dynamic parameters
        text_item_search_query_result = self.session.execute(text(text_item_search_query), params)

        # Fetch the result into a list of dictionaries
        results = text_item_search_query_result.mappings().all()
        logger.info(f"textset_search_query {str(text_item_search_query)}")
        logger.info(f" results : {results}")
        return results

    async def search_text_items_by_criteria(self, criteria: TextItemSearchCriteria, pagination: Pagination):
        """

        :param criteria:
        :param pagination:
        :return:
        """
        text_item_search_query = self.session.query(TextItem)
        if criteria.creator_id:
            text_item_search_query = text_item_search_query.filter(TextItem.creator_id == criteria.creator_id)
        if criteria.creator_name:
            text_item_search_query = text_item_search_query.filter(TextItem.creator_name == criteria.creator_name)
        if criteria.created_at_from:
            text_item_search_query = text_item_search_query.filter(
                TextItem.created_at.between(criteria.created_at_from, criteria.created_at_to))
        if criteria.text_set_ids_in:
            text_item_search_query = text_item_search_query.filter(
                TextItem.text_set_id.in_(criteria.text_set_ids_in))
        if criteria.external_item_id_in:
            text_item_search_query = text_item_search_query.filter(
                TextItem.external_item_id.in_(criteria.external_item_id_in))
        if criteria.parent_external_item_id_in:
            text_item_search_query = text_item_search_query.filter(
                TextItem.parent_external_item_id.in_(criteria.parent_external_item_id_in))
        if criteria.post_date_from:
            text_item_search_query = text_item_search_query.filter(
                TextItem.post_date.between(criteria.post_date_from, criteria.post_date_to))

        if criteria.attributes:
            attribute_ids = list(criteria.attributes.keys())

            logger.debug(f"attribute_ids : {attribute_ids}")

            query_result = (
                self.session.query(Attribute)
                .filter(Attribute.attribute_id.in_(attribute_ids))
                .all()
            )
            attributes = {
                attr.attribute_id: attr.attribute_type
                for attr in query_result
            }

            attribute_conditions = []
            for attribute_id, attribute_value in criteria.attributes.items():
                attribute_type = attributes.get(attribute_id)
                logger.debug(f"attribute_id : {attribute_id} : attribute_value {attribute_value}")

                # Handle different attribute types and apply filters
                if attribute_type == "Text":
                    attribute_conditions.append(and_(
                        AttributeValue.attribute_id == attribute_id,
                        AttributeValue.text_value.ilike(f"%{attribute_value}%")
                    ))
                elif attribute_type == "Numeric":
                    if isinstance(attribute_value.split("|"), list):
                        attribute_values = attribute_value.split("|")
                        if len(attribute_values) >= 2:
                            attribute_conditions.append(and_(
                            AttributeValue.attribute_id == attribute_id,
                            AttributeValue.num_value.between(attribute_values[0], attribute_values[1])
                            ))
                        else:
                            attribute_conditions.append(and_(
                            AttributeValue.attribute_id == attribute_id,
                            AttributeValue.num_value == attribute_values[0]
                            ))

                elif attribute_type == "Select":
                    if isinstance(attribute_value.split("|"), list):  # If attribute_value is a list of values
                        # Multiple values check in the ARRAY
                        attribute_values = attribute_value.split("|")
                        attribute_conditions.append(and_(
                            AttributeValue.attribute_id == attribute_id,
                            or_(
                                AttributeValue.select_value.any(value) for value in attribute_values
                            )
                        ))
                    else:  # Single value check
                        attribute_conditions.append(and_(
                            AttributeValue.attribute_id == attribute_id,
                            AttributeValue.select_value.any(attribute_value)  # Correct usage here
                        ))
            # Build subquery for matching creator_ids
            if attribute_conditions:
                subquery = (
                    self.session.query(AttributeValue.creator_id)
                    .filter(or_(*attribute_conditions))  # Combine all conditions with OR
                    .group_by(AttributeValue.creator_id)
                    .having(func.count(AttributeValue.creator_id) >= len(attribute_ids))
                )
                text_item_search_query = text_item_search_query.filter(TextItem.creator_id.in_(subquery))


        if pagination.order_by:
            column = getattr(TextItem, pagination.order_by, None)
            if column:
                if pagination.order_type == "desc":
                    text_item_search_query = text_item_search_query.order_by(desc(column))
                else:
                    text_item_search_query = text_item_search_query.order_by(asc(column))
            else:
                raise ValueError(f"Invalid order_by column: {pagination.order_by}")
        total = text_item_search_query.count()
        logger.info(f"textset_search_query {str(text_item_search_query)}")
        results = text_item_search_query.offset((pagination.page - 1) * pagination.page_size).limit(
            pagination.page_size).all()

        logger.info(f" results : {results}")
        return {"total": total, "items": results}

    async def get_text_values_by_attribute_id(self, attribute_id: UUID, query_string: Optional[str]) -> list[str]:
        logger.debug(f" attribute_id : {attribute_id} query_string : {query_string}")
        query = self.session.query(AttributeValue.text_value).filter(AttributeValue.attribute_id == attribute_id)
        if query_string is not None:
            query = query.filter(AttributeValue.text_value.ilike(f"%{query_string}%"))

        logger.info(f"textvalue_search_query {str(query)}")
        text_items = query.distinct().all()
        logger.info(f"text_items: {text_items}")
        return text_items


    async def get_text_items_by_set_id(self, text_set_id: UUID) -> list[models.TextItem]:
        text_items = self.session.query(TextItem).filter(TextItem.text_set_id == text_set_id).all()
        return text_items

    async def get_text_items_by_item_id(self, text_item_id: Optional[UUID], query_string: Optional[str]) -> Optional[
        models.TextItem]:
        query = text_item = self.session.query(TextItem)
        if text_item_id is not None:
            query = query.filter(TextItem.text_item_id == text_item_id)
        elif query_string is not None:
            query = query.filter(TextItem.text_content.ilike(f"%{query_string}%"))
        else:
            query
        text_item = query.first()
        return text_item
