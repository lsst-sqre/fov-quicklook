import logging
from quicklook.logging import _CustomFilter


def test_custom_filter_allows_non_ignored_messages():
    filter = _CustomFilter(ignore_patterns=["ignore this"])
    record = logging.LogRecord(name="test", level=logging.INFO, pathname="", lineno=0, msg="this should pass", args=(), exc_info=None)
    assert filter.filter(record) is True


def test_custom_filter_blocks_ignored_messages():
    filter = _CustomFilter(ignore_patterns=["ignore this"])
    record = logging.LogRecord(name="test", level=logging.INFO, pathname="", lineno=0, msg="ignore this message", args=(), exc_info=None)
    assert filter.filter(record) is False


def test_custom_filter_partial_ignore():
    filter = _CustomFilter(ignore_patterns=["ignore"])
    record = logging.LogRecord(name="test", level=logging.INFO, pathname="", lineno=0, msg="ignore this message", args=(), exc_info=None)
    assert filter.filter(record) is False


def test_custom_filter_no_ignore_patterns():
    filter = _CustomFilter(ignore_patterns=[])
    record = logging.LogRecord(name="test", level=logging.INFO, pathname="", lineno=0, msg="this should pass", args=(), exc_info=None)
    assert filter.filter(record) is True
