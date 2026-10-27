"""Функции аутентификации для учебного приложения."""
from hashlib import sha256


def hash_password(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
