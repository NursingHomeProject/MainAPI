from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_active_user
from app.modules.items.schemas import (
    ItemCreate,
    ItemDetailEnvelope,
    ItemListEnvelope,
    ItemMessageEnvelope,
    ItemResponse,
    ItemUpdate,
)
from app.modules.items.services import (
    create_item,
    deactivate_item,
    get_item_by_id,
    list_items,
    update_item,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("", response_model=ItemListEnvelope, summary="List items")
def get_items(
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = Query(default=False),
) -> ItemListEnvelope:
    items = list_items(db, include_inactive=include_inactive)
    return ItemListEnvelope(
        data=[ItemResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.post(
    "",
    response_model=ItemDetailEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
)
def create_item_route(
    payload: ItemCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ItemDetailEnvelope:
    item = create_item(db, payload)
    return ItemDetailEnvelope(data=ItemResponse.model_validate(item))


@router.get("/{item_id}", response_model=ItemDetailEnvelope, summary="Get item by id")
def get_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ItemDetailEnvelope:
    item = get_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item nao encontrado.",
        )
    return ItemDetailEnvelope(data=ItemResponse.model_validate(item))


@router.put("/{item_id}", response_model=ItemDetailEnvelope, summary="Update item")
def update_item_route(
    item_id: UUID,
    payload: ItemUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ItemDetailEnvelope:
    item = get_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item nao encontrado.",
        )

    updated_item = update_item(db, item, payload)
    return ItemDetailEnvelope(data=ItemResponse.model_validate(updated_item))


@router.delete("/{item_id}", response_model=ItemMessageEnvelope, summary="Deactivate item")
def delete_item_route(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ItemMessageEnvelope:
    item = get_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item nao encontrado.",
        )

    deactivated_item = deactivate_item(db, item)
    return ItemMessageEnvelope(
        message="Item inativado com sucesso.",
        data=ItemResponse.model_validate(deactivated_item),
    )
