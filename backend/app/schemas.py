from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


SourceName = Literal["codex", "hermes"]


class UsageTotals(BaseModel):
    inputTokens: int
    cacheReadTokens: int
    cacheWriteTokens: int
    outputTokens: int
    reasoningTokens: int
    totalTokens: int


class UsagePoint(UsageTotals):
    bucket: str
    source: SourceName


class RemoteUsageEvent(BaseModel):
    schemaVersion: int = Field(1, ge=1, le=1)
    eventId: str = Field(min_length=8, max_length=200)
    source: SourceName
    accountKey: Optional[str] = Field(
        default=None, pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$"
    )
    accountLabel: Optional[str] = Field(default=None, min_length=1, max_length=120)
    sessionHash: str = Field(min_length=8, max_length=200)
    occurredAt: float
    model: str = Field(default="unknown", max_length=200)
    inputTokens: int = Field(default=0, ge=0, le=2_000_000_000_000_000)
    cacheReadTokens: int = Field(default=0, ge=0, le=2_000_000_000_000_000)
    cacheWriteTokens: int = Field(default=0, ge=0, le=2_000_000_000_000_000)
    outputTokens: int = Field(default=0, ge=0, le=2_000_000_000_000_000)
    reasoningTokens: int = Field(default=0, ge=0, le=2_000_000_000_000_000)
    totalTokens: int = Field(default=0, ge=0, le=8_000_000_000_000_000)
    replaceSession: bool = False


class IngestRequest(BaseModel):
    schemaVersion: int = Field(1, ge=1, le=1)
    batchId: str = Field(min_length=8, max_length=200)
    events: List[RemoteUsageEvent] = Field(min_length=1, max_length=200)
