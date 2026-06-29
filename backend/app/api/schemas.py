from pydantic import BaseModel, HttpUrl

class QueryRequest(BaseModel):
    query: str

class URLRequest(BaseModel):
    url: HttpUrl
