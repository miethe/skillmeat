"""Per-request SQLAlchemy session management.

This module provides a FastAPI dependency generator that yields a single
SQLAlchemy session for the lifetime of one HTTP request.  The session is:

- Committed automatically when the request handler returns without error.
- Rolled back automatically when an unhandled exception propagates.
- Closed unconditionally in the finally block so connections are returned
  to the pool promptly.

Usage::

    from skillmeat.cache.session import get_db_session
    from sqlalchemy.orm import Session

    def some_dependency(session: Session = Depends(get_db_session)):
        ...

Or via the pre-built ``Annotated`` alias in ``skillmeat.api.dependencies``::

    from skillmeat.api.dependencies import DbSessionDep

    @router.get("/example")
    def example(session: DbSessionDep):
        ...
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session


def get_db_session() -> Generator[Session, None, None]:
    """Yield a per-request SQLAlchemy session.

    Intended for use as a FastAPI ``Depends`` provider.  A new session is
    created from the application-wide session factory (``SessionLocal`` in
    ``skillmeat.cache.models``) for every request.

    The session factory is initialised lazily on the first call via
    ``get_session()`` — the same lazy-init path used by the rest of the cache
    layer — so no explicit startup wiring is required here.

    Lifecycle
    ---------
    1. A fresh ``Session`` is opened at the start of the request.
    2. The session is yielded to the route handler (and any downstream
       dependencies that also declare ``DbSessionDep``).
    3. On a clean return: ``session.commit()`` is called.
    4. On any exception: ``session.rollback()`` is called, then the exception
       re-raises so FastAPI can return the appropriate error response.
    5. ``session.close()`` is always called in the ``finally`` block.

    Yields
    ------
    Session
        An open SQLAlchemy ``Session`` bound to the cache database.

    Examples
    --------
    Direct use in a route::

        from fastapi import APIRouter, Depends
        from sqlalchemy.orm import Session
        from skillmeat.cache.session import get_db_session

        router = APIRouter()

        @router.get("/items")
        def list_items(session: Session = Depends(get_db_session)):
            return session.query(MyModel).all()

    Via the pre-built alias::

        from skillmeat.api.dependencies import DbSessionDep

        @router.get("/items")
        def list_items(session: DbSessionDep):
            return session.query(MyModel).all()
    """
    # Import here to avoid circular imports at module load time and to
    # piggyback on the existing lazy-init logic in models.get_session().
    from skillmeat.cache.models import get_session

    session: Session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
