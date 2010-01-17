"""Implementations of different handlers that communicate with hoptoad in
various different protocols.
"""
import logging

from hoptoad import get_hoptoad_settings
from handlers.threaded import ThreadedNotifier


logger = logging.getLogger(__name__)


class Notifier(object):
    """Interface for all various implementations to provide a seamless API
    to the notification middleware

    """
    def enqueue(self, payload, timeout):
        raise NotImplementedError

def get_handler(*args, **kwargs):
    """Returns an initialized handler object"""
    hoptoad_settings = get_hoptoad_settings()
    handler = hoptoad_settings.get("HOPTOAD_HANDLER", "threadpool")
    if handler.lower() == 'threadpool':
        threads = hoptoad_settings.get("HOPTOAD_THREAD_COUNT", 4)
        return ThreadedNotifier(threads , *args, **kwargs)
