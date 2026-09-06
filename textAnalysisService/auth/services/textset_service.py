import uuid

from fastapi import HTTPException, status
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from textAnalysisService.auth.config.database import get_session
from textAnalysisService.auth.models import TextItem, Attribute, AttributeValue
from textAnalysisService.auth.repositories.textset_repository import TextSetRepository
from textAnalysisService.auth.config import config
from textAnalysisService.auth.schema import TextContentRow, TextEmbeddingRow
from textAnalysisService.auth.schema import *
import logging
import numpy as np

from tokenizer.embedings import handle_embeddings_list_V1, get_embeddings_by_text

logger = logging.getLogger(__name__)


class TextSetService:

    async def create_text_set(self, text_set_request: CreateTextSet, user_id: UUID) -> TextSetResponse:
        try:
            logger.debug("Attempting to text_set creation: %s", text_set_request.title)
            with get_session() as session:
                textset_repo = TextSetRepository(session)
                new_text_set = await textset_repo.create_text_set(text_set_request, user_id)
                logger.info("Text Set created successfully: %s", new_text_set.id)
                return TextSetResponse.model_validate(new_text_set)
        except SQLAlchemyError as e:
            logger.error(f"Error saving TextSet: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving TextSet")
        except IntegrityError as e:
            logger.error("Database error while adding TextSet: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred.",
            ) from e
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.exception("Unexpected error during TextSet addition: %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while TextSet adding {str(e)}",
            ) from e

    async def create_text_sitems(self, text_set_id: UUID, text_items_list_request: list[TextEmbeddingRow]) -> int:
        try:
            logger.debug(f"Attempting to text_items_list_request creation: {len(text_items_list_request)}")
            with get_session() as session:
                textset_repo = TextSetRepository(session)
                text_item_rows = []
                existing_attributes = await textset_repo.get_attributes_by_text_set_id(text_set_id)
                logger.debug(f"existing_attributes : {existing_attributes}")
                existing_attribute_map = {item.attribute_name: item for item in existing_attributes}
                attribute_values = []
                attribute_upd_values = []
                for text_item_request in text_items_list_request:
                    logger.debug("text_item_request object : %s", text_item_request.creator_id)
                    text_item_row = TextItem(
                        text_set_id=text_set_id, creator_id=text_item_request.creator_id,
                        creator_name=text_item_request.creator_name,
                        text_content=text_item_request.text_content,
                        post_date=text_item_request.post_date,
                        external_item_id=text_item_request.external_item_id,
                        parent_external_item_id=text_item_request.parent_external_item_id,
                        embeddings=text_item_request.embeddings,
                        pca_vector=text_item_request.pca_vector)  # map_schema_to_model(text_item_request, TextItem)
                    logger.debug("text_item_request map_schema_to_model : %s", text_item_row.creator_id)
                    text_item_rows.append(text_item_row)
                    logger.debug(f" text_item_request.attributes {text_item_request.attributes} ")

                    for attribute_name, attribute_value in text_item_request.attributes.items():
                        existing_attribute = existing_attribute_map.get(attribute_name)
                        if existing_attribute is None:
                            logger.debug(f" text_item_request.existing_attribute skipping  {attribute_name} not found")
                            continue

                        num_value = None
                        text_value = None
                        select_value = None
                        if existing_attribute.attribute_type == "Numeric":
                            num_value = attribute_value
                            is_upd = False
                            if existing_attribute.num_range_low > num_value or existing_attribute.num_range_low == 0:
                                existing_attribute.num_range_low = num_value
                                is_upd = True
                            if existing_attribute.num_range_high < num_value:
                                existing_attribute.num_range_high = num_value
                                is_upd = True
                            if is_upd:
                                attribute_upd_values.append(existing_attribute)
                        if existing_attribute.attribute_type == "Select":
                            select_value = str(attribute_value).split('|')
                            is_subset = np.isin(select_value, existing_attribute.select_choices).all()
                            if not is_subset:
                                existing_attribute.select_choices = list(
                                    set(select_value).union(existing_attribute.select_choices))
                                attribute_upd_values.append(existing_attribute)
                        if existing_attribute.attribute_type == "Text":
                            text_value = str(attribute_value)

                        attribute_row = AttributeValue(
                            num_value=num_value,
                            text_value=text_value,
                            select_value=select_value,
                            creator_id=text_item_request.creator_id,
                            attribute_id=existing_attribute.attribute_id
                        )
                        attribute_values.append(attribute_row)

                logger.info(f"Text  length :{len(attribute_values)} attribute_values {attribute_values}")

                if len(text_item_rows) == 0:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="TextItems are empty")

                logger.debug(f"attribute_upd_values : {attribute_upd_values}")
                new_text_items_count = await textset_repo.create_text_items(text_item_rows)
                await textset_repo.create_attribute_values(attribute_values)
                await textset_repo.increment_item_count(text_set_id, len(text_item_rows))
                session.commit()
                await self.handleEmbedings(text_set_id)
                logger.info("Text Items created successfully count: %s", new_text_items_count)
                return new_text_items_count
        except SQLAlchemyError as e:
            logger.error(f"Error saving TextSet: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving TextSet")
        except IntegrityError as e:
            logger.error("Database error while adding TextSet: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred.",
            ) from e
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.exception("Unexpected error during TextSet addition: %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while TextSet adding {str(e)}",
            ) from e

    async def get_text_set(self) -> TextSetListResponse:
        try:
            with get_session() as session:
                textset_repo = TextSetRepository(session)
                text_sets = await textset_repo.get_text_set()
                items = [TextSetResponse.model_validate(item) for item in text_sets]
                text_set_list = TextSetListResponse(items=items)
                return TextSetListResponse.model_validate(text_set_list)
        except SQLAlchemyError as e:
            logger.error(f"Error fetching TextSets: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching TextSets")
        except Exception as e:
            logger.exception("Unexpected error during operation %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            ) from e

    async def search_text_sets_by_criteria(self, criteria: TextSetSearchCriteria,
                                           pagination: Pagination) -> PaginatedResponse[TextSetResponse]:
        try:
            with get_session() as session:
                textset_repo = TextSetRepository(session)
                text_sets = await textset_repo.search_text_sets_by_criteria(criteria, pagination)
                items = [TextSetResponse.model_validate(item) for item in text_sets["items"]]
                return PaginatedResponse[TextSetResponse](
                    total=text_sets["total"],
                    page=pagination.page,
                    page_size=pagination.page_size,
                    items=items
                )
        except SQLAlchemyError as e:
            logger.error(f"Error fetching TextSets for criteria {criteria}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching TextSets"
            )
        except Exception as e:
            logger.exception("Unexpected error during operation %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            ) from e

    async def search_text_value_by_criteria(self,criteria: TextValueCriteria):
        try:
            with get_session() as session:
                logger.debug(f"search_text_value_by_criteria : {criteria}")
                text_set_repo = TextSetRepository(session)
                text_values = await text_set_repo.get_text_values_by_attribute_id(criteria.attribute_id, criteria.text_value)
                logger.debug(f"text_values : {text_values}")
                text_value_objects = [TextValueAttributeValue(text_value=item.text_value) for item in text_values]
                return text_value_objects
        except SQLAlchemyError as e:
            logger.error(f"Error fetching TextValues by criteria {criteria}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching TextValues by criteria"
            )
        except Exception as e:
            logger.error(f"Error in search_text_value_by_criteria: {str(e)}", exc_info=e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            )

    async def search_text_items_by_criteria(self, criteria: TextItemSearchCriteria,
                                            pagination: Pagination) -> PaginatedResponse[TextItemResponse]:
        try:
            with get_session() as session:
                textset_repo = TextSetRepository(session)
                logger.debug(f"tcriteria : {criteria} : attributes {criteria.attributes}")
                text_items = await textset_repo.search_text_items_by_criteria(criteria, pagination)
                logger.debug(f"text items: {text_items}  ")
                items = [self._convert_item_row_item_response(item) for item in text_items["items"]]
                return PaginatedResponse[TextItemResponse](
                    total=text_items["total"],
                    page=pagination.page,
                    page_size=pagination.page_size,
                    items=items
                )
        except SQLAlchemyError as e:
            logger.error(f"Error fetching text_items for criteria {criteria}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching text_items"
            )
        except Exception as e:
            logger.exception("Unexpected error during operation %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            ) from e

    def _convert_item_row_item_response(self, text_item: TextItem) -> TextItemResponse:
        logger.debug(f"converting model {text_item}")
        # logger.debug(f"converting model {text_item.embeddings}")

        return TextItemResponse(
            text_item_id=text_item.text_item_id,
            text_set_id=text_item.text_set_id,
            creator_id=text_item.creator_id,
            creator_name=text_item.creator_name,
            text_content=text_item.text_content,
            external_item_id=text_item.external_item_id,
            parent_external_item_id=text_item.parent_external_item_id,
            post_date=text_item.post_date,
            # embeddings=[value for value in text_item.embeddings],  # Assuming embedding is already a list or array
            pca_vector=[value for value in text_item.pca_vector],  # Assuming pca_vector is already a list or array
        )

    async def get_attributes_by_text_set_id(self, text_set_id: UUID) -> AttributeListResponse:
        try:
            with get_session() as session:
                text_set_repo = TextSetRepository(session)
                attributes = await text_set_repo.get_attributes_by_text_set_id(text_set_id)
                items = [AttributeResponse.model_validate(item) for item in attributes]
                attribute_list = AttributeListResponse(items=items)
                return AttributeListResponse.model_validate(attribute_list)
        except SQLAlchemyError as e:
            logger.error(f"Error fetching attributes by text_set_id {text_set_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching Attributes"
            )
        except Exception as e:
            logger.exception("Unexpected error during operation %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            ) from e

    async def get_text_sets_by_owner(self, owner_id: UUID) -> TextSetListResponse:
        try:
            with get_session() as session:
                textset_repo = TextSetRepository(session)
                text_sets = await textset_repo.get_text_sets_by_owner(owner_id)
                items = [TextSetResponse.model_validate(item) for item in text_sets]
                text_set_list = TextSetListResponse(items=items)
                return TextSetListResponse.model_validate(text_set_list)
        except SQLAlchemyError as e:
            logger.error(f"Error fetching TextSets for owner {owner_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching TextSets"
            )
        except Exception as e:
            logger.exception("Unexpected error during operation %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            ) from e

    async def get_text_items_by_set_id(self, text_set_id: UUID) -> TextItemListResponse:
        try:
            with get_session() as session:
                textset_repo = TextSetRepository(session)
                text_items = await textset_repo.get_text_items_by_set_id(text_set_id)
                if not text_items:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No TextItems found for the given TextSet ID"
                    )
                text_items_list = TextItemListResponse(items=text_items)
                return TextItemListResponse.model_validate(text_items_list)
        except SQLAlchemyError as e:
            logger.error(f"Error fetching TextItems for TextSet {text_set_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching TextItems"
            )
        except Exception as e:
            logger.exception("Unexpected error during operation %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            ) from e

    def __calculate_similarity_and_distance(self, target_embedding, all_embeddings, distance_type):
        """Calculates similarity and distance between the target and all embeddings"""

        if distance_type == 'cosine':
            similarities = cosine_similarity([target_embedding], all_embeddings)[0]
            distances = 1 - similarities  # Convert similarity to distance for consistency
        elif distance_type == 'euclidean':
            distances = euclidean_distances([target_embedding], all_embeddings)[0]
            similarities = 1 / (1 + distances)  # Convert distance to a scaled similarity
        else:
            raise ValueError(f"Unsupported distance type: {distance_type}")
        return similarities, distances

    async def get_all_text_items_by_target(self, text_set_id: uuid, search_request: SearchByItemRequest) -> list[
        SearchResultItem]:
        try:
            with get_session() as session:
                text_set_repo = TextSetRepository(session)

                if search_request.query_string:
                   target_embedding = get_embeddings_by_text(query_str=search_request.query_string).tolist()
                else:
                    target_item = await text_set_repo.get_text_items_by_item_id(search_request.target_text_item_id,
                                                                                None)
                    logger.info(
                        f"Retrieved target embedding for text_item_id {target_item} in TextSet {text_set_id}")
                    target_embedding = list(target_item.embeddings)
                if target_embedding is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="embbeddings not found"
                    )

               #search_request.target_text_item_id = target_item.text_item_id
                text_items = await text_set_repo.search_all_text_items_by_criteria(text_set_id, search_request, target_embedding)

                results = [
                    SearchResultItem(
                        text_item_id=text_item["text_item_id"],
                        text_content=text_item["text_content"],
                        similarity=text_item["similarity"],
                        distance=text_item["distance"],
                        distance_type=search_request.distance_algo
                    )
                    for text_item in text_items
                ]
                logger.debug(f"results: {results}")
                logger.info(f"Query search for text_item_id {search_request.target_text_item_id} in TextSet {text_set_id} completed successfully")

                return results
        except SQLAlchemyError as e:
            logger.error(f"Error fetching TextItems for TextSet {text_set_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching TextItems"
            )
        except Exception as e:
            logger.exception("Unexpected error during operation %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            ) from e

    def __get_attribute_type(self, attribute_values):
        if len(attribute_values) > 1:
            return "SingleSelect"
        else:
            return attribute_values[0]

    async def handle_text_set_attributes(self, attributes, text_set_id: UUID):
        try:
            with get_session() as session:
                logger.info(f"attributes are loading for {text_set_id}")
                textset_repo = TextSetRepository(session)
                existing_attributes = await textset_repo.get_attributes_by_text_set_id(text_set_id)
                existing_attributes_map = {obj.attribute_name: obj for obj in existing_attributes}
                attribute_rows = [Attribute(attribute_name=dynamic['attribute_name'],
                                            attribute_type=dynamic['attribute_type'].title(), text_set_id=text_set_id,
                                            num_range_low=0, num_range_high=0, select_choices=[])
                                  for dynamic in attributes
                                  if dynamic['attribute_name'] != "Unnamed" and existing_attributes_map.get(
                        dynamic['attribute_name']) is None
                                  ]
                if len(attribute_rows) > 0:
                    await textset_repo.create_attributes(attribute_rows)

                logger.info(f"attributes are loading for attribute_rows : {len(attribute_rows)}")
                return len(attribute_rows)

        except SQLAlchemyError as e:
            logger.error(f"Error fetching TextItems for TextSet {text_set_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching TextItems"
            )
        except Exception as e:
            logger.exception("Unexpected error during operation %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            ) from e


    async def handleEmbedings(self, text_set_id) -> bool:
        try:
            with get_session() as session:
                textset_repo = TextSetRepository(session)
                text_items = await textset_repo.get_text_items_by_set_id(text_set_id)
                if len(text_items)>=3:
                    items = [TextItemsContent.model_validate(item) for item in text_items]
                    embdedings = handle_embeddings_list_V1(items)
                    embdedings_map = {obj.text_item_id: obj for obj in embdedings}
                    for item in text_items:
                        embedding_obj = embdedings_map.get(item.text_item_id)
                        item.embeddings = embedding_obj.embeddings
                        item.pca_vector = embedding_obj.pca_vector

        except SQLAlchemyError as e:
            logger.error(f"Error fetching TextItems for TextSet {text_set_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching TextItems"
            )
        except Exception as e:
            logger.exception("Unexpected error during operation %s.", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while operation {str(e)}",
            ) from e
