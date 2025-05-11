from functools import lru_cache

import pydantic


@lru_cache
def is_pydantic_v2() -> bool:
    return pydantic.VERSION.startswith("2")
