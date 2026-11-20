"""Pydantic-модели запросов и ответов."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list)


class GenieChatRequest(ChatRequest):
    """Запрос к облачной Джинни. with_audio — вернуть ещё и её голос."""

    with_audio: bool = False


class XChatRequest(ChatRequest):
    """Запрос к X-агенту: провайдер, модель и обмен контекстом с Дроном."""

    provider: str | None = None
    model: str | None = None
    share_context: bool = True
    timeout: float | None = None


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    autoplay: bool = False


class SttRequest(BaseModel):
    audio: str = Field(min_length=16)
    format: str = Field(default="webm", max_length=16)


class SettingsPatch(BaseModel):
    profile: Literal["dron", "vanja", "babushka"] | None = None
    theme: Literal["neon", "genie"] | None = None
    scale: float | None = Field(default=None, ge=1.0, le=2.0)
    large_mode: bool | None = None
    sound: bool | None = None
    animation: bool | None = None
    theater_mode: bool | None = None
    timezone: str | None = Field(default=None, max_length=64)
    default_agent: Literal["dron", "genie"] | None = None
    panels_collapsed: bool | None = None
    duet_mode: bool | None = None
    dron_temperature: float | None = Field(default=None, ge=0.0, le=1.5)
    dron_max_tokens: int | None = Field(default=None, ge=32, le=2000)
    voice_model: str | None = Field(default=None, max_length=64)
    voice_autoplay: bool | None = None
    voice_length_scale: float | None = Field(default=None, ge=0.5, le=2.0)
    voice_pitch_factor: float | None = Field(default=None, ge=0.5, le=1.5)
    voice_bass_gain: int | None = Field(default=None, ge=0, le=15)


class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ErrorResponse(BaseModel):
    error: ErrorBody
