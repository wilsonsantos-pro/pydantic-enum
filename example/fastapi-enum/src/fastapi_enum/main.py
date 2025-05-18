from enum import IntEnum
from typing import Annotated

from fastapi import FastAPI
from pydantic import Field

from pydantic_enum.base_model import MyBaseModel


class Status(IntEnum):
    PENDING = 1
    APPROVED = 2


class Priority(IntEnum):
    LOW = 1
    HIGH = 2


class Item(MyBaseModel):
    name: str = Field(description="Item name")
    status: Annotated[str, Status]
    priority: Priority  # Will not be automatically converted because is not "Annotated"


app = FastAPI()


@app.get("/item", response_model=Item)
def get_item():
    return {
        "status": Status.PENDING,  # Will be converted to "APPROVED"
        "priority": 2,  # Will be not be converted
        "name": "arst",
    }


@app.get("/error", response_model=Item)
def get_error():
    return {
        "status": 666,  # Will raise validation error
        "priority": 1,
        "name": "qwfp",
    }


@app.get("/schema", response_model=dict)
def get_schema():
    return Item.model_json_schema()
