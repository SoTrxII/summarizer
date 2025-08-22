
from json import dumps, loads
from pathlib import Path
from typing import List, Type, TypeVar

T = TypeVar('T')


def read_test_data(file_path: Path, model_class: Type[T]) -> List[T]:
    """Generic function to read and parse JSON files into model objects.
    This is non-trivial due to the mix of Pydantic models (required by SK) and TypedDict (used for some models).
    """
    with open(file_path) as f:
        data = loads(f.read())
        if isinstance(data, list):
            # Check if it's a TypedDict or Pydantic model
            if hasattr(model_class, 'model_validate'):
                # Pydantic model
                return [model_class(**item) for item in data]
            else:
                # TypedDict - just return the dict directly (TypedDict is structural typing)
                return data  # type: ignore
        else:
            # Single object
            if hasattr(model_class, 'model_validate'):
                return [model_class(**data)]
            else:
                return [data]  # type: ignore


def write_test_data(file_path: Path, data, ensure_ascii: bool = False) -> None:
    """Generic function to write data to JSON files."""
    with open(file_path, "w") as f:
        if hasattr(data, 'model_dump'):
            content = data.model_dump()
        elif isinstance(data, list) and data and hasattr(data[0], 'model_dump'):
            content = [item.model_dump() if hasattr(
                item, 'model_dump') else item for item in data]
        else:
            content = data
        f.write(dumps(content, ensure_ascii=ensure_ascii))
