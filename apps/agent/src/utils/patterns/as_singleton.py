import threading
from collections.abc import Callable
from functools import wraps
from typing import Any


def as_singleton[T](cls: type[T]) -> Callable[..., T]:
    """
    Note:
        Thread-safe decorator for singleton pattern, using
        double-checked locking to ensure only one instance
        of a class is created across multiple threads.

    Returns:
        Callable[..., T]: Factory returning the single instance of the class.
    """
    instances: dict[type[T], Any] = {}
    lock = threading.Lock()

    @wraps(cls)
    def get_instance(*args, **kwargs) -> T:
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
