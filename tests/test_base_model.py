from enum import IntEnum
from typing import Annotated

import pytest
from pydantic import Field, ValidationError

from pydantic_enum.base_model import MyBaseModel
from pydantic_enum.check_version import is_pydantic_v2


class Color(IntEnum):
    RED = 1
    BLUE = 2
    GREEN = 3


class ColorItem(MyBaseModel):
    color: Annotated[str, Color]
    if is_pydantic_v2():
        default: Annotated[str, Field(Color.RED), Color]
    else:
        default: Annotated[str, Color] = Field(Color.RED)
    empty: Annotated[str | None, Color] = Field(default=None)


def test_json_schema_enum():
    expected = [e.name for e in Color]
    if is_pydantic_v2():
        assert ColorItem.model_fields["color"].json_schema_extra["enum"] == expected
    else:
        assert ColorItem.__fields__["color"].field_info.extra["enum"] == expected


def test_default():
    assert ColorItem(color="BLUE").default == Color.RED.name
    assert ColorItem(color="BLUE").empty is None


def test_instantiation_from_string():
    assert ColorItem(color="BLUE").color == Color.BLUE.name


def test_instantiation_from_int():
    assert ColorItem(color=Color.BLUE.value).color == Color.BLUE.name


def test_instantiation_from_enum():
    assert ColorItem(color=Color.BLUE).color == Color.BLUE.name


def test_invalid_string():
    with pytest.raises(ValidationError):
        ColorItem(color="YELLOW")


def test_invalid_value():
    with pytest.raises(ValidationError):
        ColorItem(color=("BLUE", 1))


def test_list():
    class Favorite(MyBaseModel):
        colors: Annotated[list[str], list[Color]]

    assert Favorite(colors=[Color.RED, Color.GREEN]).colors == [
        Color.RED.name,
        Color.GREEN.name,
    ]


def test_tuple():
    class Favorite(MyBaseModel):
        colors: Annotated[tuple[str, str], tuple[Color, Color]]

    assert Favorite(colors=(Color.RED, Color.GREEN)).colors == (
        Color.RED.name,
        Color.GREEN.name,
    )


def test_non_annotated():
    class Favorite(MyBaseModel):
        user_id: int
        color: Annotated[str, Color]

    assert Favorite(user_id=1, color=Color.RED).color == Color.RED.name


if is_pydantic_v2():

    def test_json_schema():
        expected = {
            "properties": {
                "color": {
                    "enum": ["RED", "BLUE", "GREEN"],
                    "title": "Color",
                    "type": "string",
                },
                "default": {
                    "type": "string",
                    "default": 1,
                    "enum": ["RED", "BLUE", "GREEN"],
                    "title": "Default",
                },
                "empty": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "default": None,
                    "enum": ["RED", "BLUE", "GREEN"],
                    "title": "Empty",
                },
            },
            "required": ["color"],
            "title": "ColorItem",
            "type": "object",
        }

        assert ColorItem.model_json_schema() == expected

else:

    def test_json_schema():
        expected = {
            "properties": {
                "color": {
                    "enum": ["RED", "BLUE", "GREEN"],
                    "title": "Color",
                    "type": "string",
                },
                "default": {
                    "type": "string",
                    "default": 1,
                    "enum": ["RED", "BLUE", "GREEN"],
                    "title": "Default",
                },
                "empty": {
                    "title": "Empty",
                    "enum": ["RED", "BLUE", "GREEN"],
                    "type": "string",
                },
            },
            "required": ["color"],
            "title": "ColorItem",
            "type": "object",
        }
        assert ColorItem.schema() == expected
