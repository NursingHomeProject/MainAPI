from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal
from app.modules.auth.models import User

logger = logging.getLogger(__name__)


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    statement = select(User).where(User.email == normalized_email)
    return db.scalar(statement)


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    password: str,
    is_active: bool = True,
    is_superuser: bool = False,
) -> User:
    user = User(
        full_name=full_name.strip(),
        email=email.strip().lower(),
        password_hash=hash_password(password),
        is_active=is_active,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def seed_admin_user() -> None:
    if not settings.seed_admin_on_startup:
        return

    try:
        with SessionLocal() as db:
            existing_user = get_user_by_email(db, settings.admin_email)
            if existing_user is not None:
                return

            create_user(
                db,
                full_name=settings.admin_full_name,
                email=settings.admin_email,
                password=settings.admin_password,
                is_active=True,
                is_superuser=True,
            )
            logger.info("Admin seed created for %s", settings.admin_email)
    except SQLAlchemyError as exc:
        logger.warning("Admin seed skipped because the database is not ready: %s", exc)
    except Exception as exc:
        logger.warning("Admin seed skipped: %s", exc)
