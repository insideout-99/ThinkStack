from pydantic import BaseModel, Field, HttpUrl

class DocumentMetadata(BaseModel):
    department: str | None = None
    category: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)

class QueryFilters(BaseModel):
    department: str | None = None
    category: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_type: str | None = None

class URLRequest(BaseModel):
    url: HttpUrl
    metadata: DocumentMetadata | None = None

class QueryRequest(BaseModel):
    query: str
    filters: QueryFilters | None = None

class FeedbackRequest(BaseModel):
    query_log_id: str | None = None
    rating: str
    comment: str | None = None
