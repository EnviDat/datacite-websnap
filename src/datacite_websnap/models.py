"""Pydantic models for DataCite API responses."""

from pydantic import BaseModel


class DoiAttributes(BaseModel):
    doi: str
    xml: str | None = None


class DoiObject(BaseModel):
    attributes: DoiAttributes


class Meta(BaseModel):
    total: int
    totalPages: int


class Links(BaseModel):
    next: str | None = None


class DoisResponse(BaseModel):
    data: list[DoiObject]
    meta: Meta
    links: Links


class SingleDoiResponse(BaseModel):
    data: DoiObject
