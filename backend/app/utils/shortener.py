import secrets
import string

_ALPHABET = string.ascii_letters + string.digits
"""
Алфавит: цифры + заглавные + строчные буквы = 62 символа
62^6 = ~56 миллиардов уникальных комбинаций
"""


def generate_short_id(length: int = 6) -> str:
    """Генерирует криптографически безопасный случайный short_id.

    Args:
        length: длина идентификатора (по умолчанию 6)

    Returns:
        Строка из символов [a-zA-Z0-9] заданной длины
    """
    if length < 4:
        raise ValueError(
            f"Длина short_id должна быть >= 4, получено: {length}"
        )

    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
