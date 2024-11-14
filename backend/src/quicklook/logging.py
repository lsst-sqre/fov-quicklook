import logging


class _CustomFilter(logging.Filter):
    def __init__(self, ignore_patterns: list[str]):
        self.ignore_patterns = ignore_patterns

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(pattern in record.getMessage() for pattern in self.ignore_patterns)


def filter_logs(ignore_patterns: list[str]):  # pragma: no cover
    logging.getLogger('uvicorn.access').addFilter(_CustomFilter(ignore_patterns))
