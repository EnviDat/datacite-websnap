"""Pydantic models for API responses."""

from pydantic import BaseModel


class RelatedItemIdentifier(BaseModel):
    relatedItemIdentifier: str | None = None
    relatedItemIdentifierType: str | None = None


class RelatedItem(BaseModel):
    relatedItemType: str | None = None
    relationType: str | None = None
    relatedItemIdentifier: RelatedItemIdentifier | None = None


class DoiAttributes(BaseModel):
    doi: str
    xml: str | None = None
    url: str
    relatedItems: list[RelatedItem] | None = None


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


class SciCatDistributionObject(BaseModel):
    contentUrl: str
    name: str | None = None


class SciCatDoiResponse(BaseModel):
    distribution: list[SciCatDistributionObject]
