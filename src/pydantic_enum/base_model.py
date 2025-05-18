from collections.abc import Generator
from enum import Enum, IntEnum
from typing import Any, get_args, get_origin, get_type_hints

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import Self

from pydantic_enum.check_version import is_pydantic_v2

_EnumFieldOrigin = int | str | list[str] | tuple | None


class _BaseModel(BaseModel):

    @classmethod
    def get_model_fields(cls) -> dict[str, FieldInfo]:
        if is_pydantic_v2():
            return cls.model_fields
        return {n: f.field_info for n, f in cls.__fields__.items()}  # pyright: ignore

    @classmethod
    def sanitize_enum(
        cls, value: _EnumFieldOrigin, enum_cls: type[Enum]
    ) -> _EnumFieldOrigin | list[_EnumFieldOrigin] | tuple[_EnumFieldOrigin]:
        sanitized_value = None
        try:
            if isinstance(value, enum_cls):
                sanitized_value = value.name
            elif isinstance(value, int):
                sanitized_value = enum_cls(value).name
            elif isinstance(value, str):
                sanitized_value = enum_cls[value].name
            elif isinstance(value, list):
                return [cls.sanitize_enum(v, enum_cls) for v in value]  # pyright: ignore
            elif isinstance(value, tuple):
                return tuple(cls.sanitize_enum(v, enum_cls) for v in value)
            elif value is not None:
                raise ValueError()
        except (ValueError, KeyError) as exc:
            raise ValueError(cls.invalid_enum_value_msg(value, enum_cls)) from exc
        return sanitized_value

    @classmethod
    def invalid_enum_value_msg(cls, value: Any, enum_cls: type[Enum]) -> str:
        return (
            f"Invalid enum value: {value}. Must be one of: "
            f"{', '.join(f'{e.name} ({e.value})' for e in enum_cls)}"
        )

    @classmethod
    def enum_fields(cls) -> Generator[tuple[str, FieldInfo, type[Enum]], None, None]:
        field: FieldInfo
        annotations = get_type_hints(cls, include_extras=True)

        for field_name, field in cls.get_model_fields().items():
            enum_cls = None
            for meta in getattr(annotations[field_name], "__metadata__", []):
                if isinstance(meta, type) and issubclass(meta, IntEnum):
                    enum_cls = meta
                elif get_origin(meta) in (list, tuple):
                    enum_cls = get_args(meta)[0]

            if enum_cls:
                yield field_name, field, enum_cls

    @classmethod
    def _patch_enum_description(cls):
        for _, field, enum_cls in cls.enum_fields():
            if issubclass(enum_cls, IntEnum):
                # Add description
                if not field.description:
                    field.description = f"Enum values: {', '.join(e.name for e in enum_cls)}"


def create_model_v2() -> type[BaseModel]:
    # pylint: disable=import-outside-toplevel
    from pydantic import model_validator

    class _MyBaseModel(_BaseModel):
        @classmethod
        def __pydantic_init_subclass__(cls, **kwargs):
            super().__pydantic_init_subclass__(**kwargs)
            cls._patch_enum_description()

        @model_validator(mode="after")  # pyright: ignore
        def check_enum_value_after(self) -> Self:
            # needed for the default values
            for field_name, _, enum_cls in self.enum_fields():
                value = getattr(self, field_name)

                value = self.sanitize_enum(value, enum_cls)
                if value:
                    setattr(self, field_name, value)

            return self

        @model_validator(mode="before")  # pyright: ignore
        @classmethod
        def check_enum_value_before(cls, data: Any) -> Any:
            if not isinstance(data, dict):
                return data
            for field_name, _, enum_cls in cls.enum_fields():
                value = data.get(field_name)
                value = cls.sanitize_enum(value, enum_cls)

                if value:
                    data[field_name] = value

            return data

    return _MyBaseModel


def create_model_v1() -> type[BaseModel]:
    # pylint: disable=import-outside-toplevel
    from pydantic import root_validator

    class _MyBaseModel(_BaseModel):

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            cls._patch_enum_description()

        @root_validator(pre=True)
        @classmethod
        def check_enum_value_before(cls, values: dict[str, Any]) -> dict[str, Any]:
            return cls._validate_enums(values)

        @root_validator  # pyright: ignore
        @classmethod
        def check_enum_value_after(cls, values: dict[str, Any]) -> dict[str, Any]:
            # needed for the default values
            return cls._validate_enums(values)

        @classmethod
        def _validate_enums(cls, values: dict[str, Any]) -> dict[str, Any]:
            # pylint: disable=import-outside-toplevel
            for field_name, _, enum_cls in cls.enum_fields():
                value = values.get(field_name)
                value = cls.sanitize_enum(value, enum_cls)

                if value:
                    values[field_name] = value

            return values

    return _MyBaseModel


if is_pydantic_v2():
    MyBaseModel = create_model_v2()
else:
    MyBaseModel = create_model_v1()
