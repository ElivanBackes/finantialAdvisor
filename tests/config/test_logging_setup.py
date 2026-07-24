import logging
import sys

from config.logging_setup import MongoLogHandler


class _FakeLogRepository:
    def __init__(self) -> None:
        self.inserted: list[dict] = []

    def insert(self, document: dict):
        self.inserted.append(document)
        return None


class _FailingLogRepository:
    def insert(self, document: dict):
        raise RuntimeError("Mongo indisponível")


def _make_record(
    name: str = "services.asset_service",
    level: int = logging.INFO,
    msg: str = "mensagem de teste",
    extra: dict | None = None,
    exc_info=None,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=exc_info,
    )
    for key, value in (extra or {}).items():
        setattr(record, key, value)
    return record


def test_emit_persists_info_record():
    repo = _FakeLogRepository()
    handler = MongoLogHandler(repository=repo)

    handler.emit(_make_record())

    assert len(repo.inserted) == 1
    doc = repo.inserted[0]
    assert doc["level"] == "INFO"
    assert doc["logger"] == "services.asset_service"
    assert doc["message"] == "mensagem de teste"


def test_emit_propagates_ticker_from_extra():
    repo = _FakeLogRepository()
    handler = MongoLogHandler(repository=repo)

    handler.emit(_make_record(extra={"ticker": "PETR4.SA"}))

    assert repo.inserted[0]["ticker"] == "PETR4.SA"


def test_emit_without_ticker_extra_sets_none():
    repo = _FakeLogRepository()
    handler = MongoLogHandler(repository=repo)

    handler.emit(_make_record())

    assert repo.inserted[0]["ticker"] is None


def test_emit_ignores_pymongo_records():
    repo = _FakeLogRepository()
    handler = MongoLogHandler(repository=repo)

    handler.emit(_make_record(name="pymongo.topology"))

    assert repo.inserted == []


def test_emit_formats_real_exception():
    repo = _FakeLogRepository()
    handler = MongoLogHandler(repository=repo)

    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()

    handler.emit(_make_record(level=logging.ERROR, msg="falhou", exc_info=exc_info))

    exception_text = repo.inserted[0]["exception"]
    assert exception_text is not None
    assert "ValueError" in exception_text
    assert "boom" in exception_text


def test_emit_does_not_raise_when_repository_fails():
    handler = MongoLogHandler(repository=_FailingLogRepository())

    # handleError, por padrão, só imprime em sys.stderr — não deve propagar.
    handler.emit(_make_record())
