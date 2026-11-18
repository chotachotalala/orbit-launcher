"""Validated, serializable launcher entries."""

from dataclasses import asdict, dataclass
from urllib.parse import urlsplit
from uuid import uuid4

KINDS = {"app": "Программа", "folder": "Папка", "file": "Файл", "url": "Сайт"}


@dataclass(frozen=True)
class Entry:
    id: str
    name: str
    target: str
    kind: str = "app"
    aliases: str = ""
    favorite: bool = False
    launches: int = 0
    last_used: float = 0
    source: str = "manual"

    @classmethod
    def create(cls, name: str, target: str, kind: str = "app", **kwargs) -> "Entry":
        return cls.from_dict(
            {"id": uuid4().hex, "name": name, "target": target, "kind": kind, **kwargs}
        )

    @classmethod
    def from_dict(cls, value: dict) -> "Entry":
        if not isinstance(value, dict):
            raise ValueError("Запись должна быть объектом.")
        name, target = value.get("name"), value.get("target")
        kind = value.get("kind", "app")
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValueError("Название должно содержать от 1 до 120 символов.")
        if not isinstance(target, str) or not target.strip() or len(target) > 4096:
            raise ValueError("Укажите путь или адрес длиной до 4096 символов.")
        if any(c in target for c in "\r\n\x00") or kind not in KINDS:
            raise ValueError("Некорректный адрес или тип записи.")
        target = target.strip()
        if kind == "url":
            try:
                parsed = urlsplit(target)
                valid = (
                    parsed.scheme in {"https", "http"}
                    and parsed.hostname
                    and not parsed.username
                    and not parsed.password
                )
                _ = parsed.port
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("Нужен адрес http:// или https:// без логина и пароля.")
        aliases = value.get("aliases", "")
        if not isinstance(aliases, str) or len(aliases) > 500:
            raise ValueError("Ключевые слова должны быть строкой до 500 символов.")
        entry_id = value.get("id", uuid4().hex)
        if not isinstance(entry_id, str) or not entry_id or len(entry_id) > 100:
            raise ValueError("Некорректный идентификатор.")
        return cls(
            entry_id,
            name.strip(),
            target,
            kind,
            aliases.strip(),
            bool(value.get("favorite", False)),
        )

    def to_dict(self) -> dict:
        return asdict(self)
