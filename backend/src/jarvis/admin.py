"""Router admin para CRUD de usuarios, config e logs."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .db import (
    create_user,
    delete_user,
    get_global_config,
    get_user_by_id,
    get_user_config,
    list_users,
    set_global_config,
    set_user_config,
    update_user,
    update_user_password,
)
from .deps import get_admin_user
from .logs import get_thread_messages, list_threads
from .schemas import (
    ConfigResponse,
    ConfigUpdate,
    PasswordUpdate,
    ThreadListResponse,
    ThreadSummary,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/admin", dependencies=[Depends(get_admin_user)])


def _conn(request: Request):
    return request.app.state.auth_db


def _db_path(request: Request) -> str:
    return request.app.state.settings.db_path


# --- Users CRUD ---


@router.get("/users", response_model=list[UserResponse])
async def admin_list_users(request: Request):
    """Lista todos os usuarios."""
    users = await list_users(_conn(request))
    return [UserResponse(**u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(body: UserCreate, request: Request):
    """Cria novo usuario."""
    from aiosqlite import IntegrityError

    try:
        user = await create_user(
            _conn(request),
            username=body.username,
            email=body.email,
            plain_password=body.password,
            role=body.role,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username ou email ja existe.",
        )

    return UserResponse(**user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def admin_get_user(user_id: int, request: Request):
    """Retorna dados de um usuario."""
    user = await get_user_by_id(_conn(request), user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado.",
        )
    return UserResponse(**user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def admin_update_user(user_id: int, body: UserUpdate, request: Request):
    """Atualiza dados de um usuario."""
    user = await update_user(
        _conn(request),
        user_id,
        email=body.email,
        role=body.role,
        is_active=body.is_active,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado.",
        )
    return UserResponse(**user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(user_id: int, request: Request):
    """Remove um usuario."""
    deleted = await delete_user(_conn(request), user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado.",
        )


@router.put("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def admin_update_password(user_id: int, body: PasswordUpdate, request: Request):
    """Atualiza senha de um usuario."""
    updated = await update_user_password(_conn(request), user_id, body.password)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado.",
        )


# --- Config ---


@router.get("/config", response_model=ConfigResponse)
async def admin_get_global_config(request: Request):
    """Retorna config global."""
    config = await get_global_config(_conn(request))
    return ConfigResponse(**config)


@router.put("/config", response_model=ConfigResponse)
async def admin_set_global_config(body: ConfigUpdate, request: Request):
    """Atualiza config global (merge com existente)."""
    updates = body.model_dump(exclude_none=True)
    if updates:
        await set_global_config(_conn(request), updates)
    config = await get_global_config(_conn(request))
    return ConfigResponse(**config)


@router.get("/users/{user_id}/config", response_model=ConfigResponse)
async def admin_get_user_config(user_id: int, request: Request):
    """Retorna config de um usuario."""
    user = await get_user_by_id(_conn(request), user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado.",
        )
    config = await get_user_config(_conn(request), user_id)
    return ConfigResponse(**config)


@router.put("/users/{user_id}/config", response_model=ConfigResponse)
async def admin_set_user_config(user_id: int, body: ConfigUpdate, request: Request):
    """Atualiza config de um usuario (merge com existente)."""
    user = await get_user_by_id(_conn(request), user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado.",
        )
    updates = body.model_dump(exclude_none=True)
    if updates:
        await set_user_config(_conn(request), user_id, updates)
    config = await get_user_config(_conn(request), user_id)
    return ConfigResponse(**config)


# --- Logs ---


@router.get("/logs", response_model=ThreadListResponse)
async def admin_list_threads(
    request: Request,
    user_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Lista threads de conversa."""
    db_path = _db_path(request)
    threads, total = await list_threads(db_path, user_id=user_id, limit=limit, offset=offset)

    # Buscar usernames para os threads
    conn = _conn(request)
    summaries = []
    for t in threads:
        username = None
        if t["user_id"] is not None:
            user = await get_user_by_id(conn, t["user_id"])
            username = user["username"] if user else None

        summaries.append(ThreadSummary(
            thread_id=t["thread_id"],
            user_id=t["user_id"],
            username=username,
        ))

    return ThreadListResponse(threads=summaries, total=total)


@router.get("/logs/{thread_id:path}")
async def admin_get_thread_messages(thread_id: str, request: Request):
    """Retorna mensagens de um thread."""
    db_path = _db_path(request)
    messages = await get_thread_messages(db_path, thread_id)
    return {"thread_id": thread_id, "messages": messages}
