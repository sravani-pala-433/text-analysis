
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from textAnalysisService.auth.services.textset_service import TextSetService
from textAnalysisService.auth.schema import *
from textAnalysisService.auth.utils.Jwt_token import verify_access_token
import logging

router = APIRouter(tags=['Textset Management'], prefix="/api")

textset_service = TextSetService()

logger = logging.getLogger(__name__)


@router.post('/TextSets', response_model=TextSetResponse, status_code=status.HTTP_201_CREATED)
async def create_text_set(text_set: CreateTextSet, payload: JWTTokenPayload = Depends(verify_access_token)):
    try:
        logger.debug(f"create_text_set request : {text_set.title}")
        return await textset_service.create_text_set(text_set, payload.user_id)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to create textset: {text_set.title}", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error while login user. {str(e)}"},
        )


@router.post('/TextSets/search', response_model=PaginatedResponse[TextSetResponse], status_code=status.HTTP_200_OK)
async def search_text_set(criteria: TextSetSearchCriteria, pagination: Pagination = Depends(),
                          payload: JWTTokenPayload = Depends(verify_access_token)):
    try:
        logger.debug(f"search_text_set request ")
        return await textset_service.search_text_sets_by_criteria(criteria, pagination)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to get list of textset", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error while textSet search. {str(e)}"},
        )


@router.post('/TextItem/search', response_model=PaginatedResponse[TextItemResponse], status_code=status.HTTP_200_OK)
async def search_text_items(criteria: TextItemSearchCriteria, pagination: Pagination = Depends(),
                          payload: JWTTokenPayload = Depends(verify_access_token)):
    try:
        logger.debug(f"search_text_set request ")
        return await textset_service.search_text_items_by_criteria(criteria, pagination)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to get list of TextItem", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error while TextItem search. {str(e)}"},
        )

@router.post('/TextValue/Search', response_model=list[TextValueAttributeValue], status_code=status.HTTP_200_OK)
async def search_text_value(criteria: TextValueCriteria, payload: JWTTokenPayload = Depends(verify_access_token)):
    try:
        logger.debug(f"text_value: {criteria.text_value}")
        return await textset_service.search_text_value_by_criteria(criteria)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to get list of TextValue", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error while TextValue search. {str(e)}"},
        )


@router.get('/TextSets', response_model=TextSetListResponse, status_code=status.HTTP_200_OK)
async def get_all_text_set(payload: JWTTokenPayload = Depends(verify_access_token)):
    try:
        logger.debug(f"get_all_text_set request ")
        return await textset_service.get_text_set()
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to get list of textset", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error while login user. {str(e)}"},
        )


@router.get('/TextSets/{owner_id}', response_model=TextSetListResponse, status_code=status.HTTP_200_OK)
async def get_all_text_sets_by_owner_id(owner_id: UUID, payload: JWTTokenPayload = Depends(verify_access_token)):
    try:
        logger.debug(f"get_all_text_sets_by_owner_id request ")
        return await textset_service.get_text_sets_by_owner(payload.user_id)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to get list of textset", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error while login user. {str(e)}"},
        )

@router.get('/TextSets/{test_set_id}/attributes', response_model=AttributeListResponse, status_code=status.HTTP_200_OK)
async def get_attributes_by_text_set_id(text_set_id: UUID, payload: JWTTokenPayload = Depends(verify_access_token)):
    try:
        logger.debug(f"get_all_text_sets_by_owner_id request text_set_id : {text_set_id}")
        return await textset_service.get_attributes_by_text_set_id(text_set_id)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to get list of Attributes", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error while performing request. {str(e)}"},
        )



@router.get('/TextItems/{text_set_id}', response_model=TextItemListResponse, status_code=status.HTTP_200_OK)
async def get_text_items_by_set_id(text_set_id: UUID, payload: JWTTokenPayload = Depends(verify_access_token)):
    try:
        logger.debug(f"get_text_items_by_set_id request ")
        return await textset_service.get_text_items_by_set_id(text_set_id)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to get list of textset", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error while login user. {str(e)}"},
        )


@router.post('/TextSets/{text_set_id}/items/search', response_model=list[SearchResultItem],status_code=status.HTTP_200_OK)
async def get_all_text_items_by_target(text_set_id: UUID, search_request: SearchByItemRequest,
                                       payload: JWTTokenPayload = Depends(verify_access_token)):
    try:
        logger.debug(f"get_all_text_items_by_target request ")
        return await textset_service.get_all_text_items_by_target(text_set_id, search_request)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to get list of text items", exc_info=e)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error while getting data . {str(e)}"},
        )

