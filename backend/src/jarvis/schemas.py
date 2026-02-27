"""Modelos Pydantic para auth e admin."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


# --- Auth ---

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# --- User ---

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None


class PasswordUpdate(BaseModel):
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str


class MeResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str


# --- Config ---

class ConfigUpdate(BaseModel):
    system_prompt: str | None = None
    model_name: str | None = None
    history_window: int | None = None
    max_tool_steps: int | None = None


class ConfigResponse(BaseModel):
    system_prompt: str | None = None
    model_name: str | None = None
    history_window: int | None = None
    max_tool_steps: int | None = None


# --- Logs ---

class ThreadSummary(BaseModel):
    thread_id: str
    user_id: int | None = None
    username: str | None = None
    message_count: int = 0


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummary]
    total: int
