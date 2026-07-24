import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from persistence.repositories.log_repository import LogRepository

_configured = False


class MongoLogHandler(logging.Handler):
    """Handler de logging que persiste cada LogRecord na coleção `logs`
    (via LogRepository). Ignora registros do próprio driver `pymongo` para
    não gerar ruído/risco de recursão a cada escrita no Mongo.
    """

    def __init__(self, repository: LogRepository | None = None) -> None:
        super().__init__()
        self._repository = repository or LogRepository()

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == "pymongo" or record.name.startswith("pymongo."):
            return
        try:
            document: dict[str, Any] = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "ticker": getattr(record, "ticker", None),
                "exception": (
                    "".join(traceback.format_exception(*record.exc_info))
                    if record.exc_info
                    else None
                ),
            }
            self._repository.insert(document)
        except Exception:
            self.handleError(record)


def configure_logging() -> None:
    """Configura o logger raiz uma única vez por processo.

    Idempotente por flag de módulo: necessário porque tanto o Streamlit
    (app.py roda do zero a cada interação do usuário) quanto os scripts
    podem chamar esta função mais de uma vez no mesmo processo — sem essa
    proteção, handlers se acumulariam e cada log seria gravado N vezes.
    """
    global _configured
    if _configured:
        return

    settings = get_settings()
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        root_logger.addHandler(stream_handler)

    if not any(isinstance(h, MongoLogHandler) for h in root_logger.handlers):
        root_logger.addHandler(MongoLogHandler())

    # Mitigação extra (complementar ao filtro por nome em emit): reduz o
    # volume que o driver pymongo gera internamente, evitando ruído/risco
    # de recursão a cada operação no Mongo — inclusive as do próprio handler.
    logging.getLogger("pymongo").setLevel(logging.WARNING)

    _configured = True
