"""English–Vietnamese lookup schemas; one term per request."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LookupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    term: str = Field(min_length=1, max_length=120)

    @field_validator("term")
    @classmethod
    def normalize_term(cls, value: str) -> str:
        value = " ".join(value.strip().lower().replace("’", "'").split())
        if len(value.split()) > 12 or not re.fullmatch(r"[a-z]+(?:['-][a-z]+)*(?: [a-z]+(?:['-][a-z]+)*)*", value):
            raise ValueError("Chỉ nhập một từ/cụm tiếng Anh, tối đa 12 từ; không nhập danh sách.")
        return value


class DictionaryExample(BaseModel):
    english: str = Field(min_length=1, max_length=1000)
    vietnamese: str = Field(min_length=1, max_length=1000)


class DictionaryMeaning(BaseModel):
    part_of_speech: str = Field(min_length=1, max_length=100)
    vietnamese: str = Field(min_length=1, max_length=2000)
    examples: list[DictionaryExample] = Field(max_length=3)


class DictionaryEntry(BaseModel):
    found: bool
    ipa: str | None
    meanings: list[DictionaryMeaning] = Field(max_length=12)

    @model_validator(mode="after")
    def check_found(self):
        if self.found != bool(self.meanings):
            raise ValueError("found must match whether meanings exist")
        return self


class LookupResponse(DictionaryEntry):
    term: str
    cached: bool
    source: Literal["gemini"] = "gemini"
