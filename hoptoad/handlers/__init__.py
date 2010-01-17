"""Implementations of different handlers that communicate with hoptoad in
various different protocols.
"""
import logging

from django.conf import settings

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
    all_settings = dir(settings)

    if 'HOPTOAD_HANDLER_NAME' not in all_settings or\
        settings.HOPTOAD_HANDLER_NAME.lower() == 'threadpool':

        if 'HOPTOAD_THREAD_COUNT' in all_settings:
            threads = settings.HOPTOAD_THREAD_COUNT
        else:
            threads = 4

        return ThreadedNotifier(threads, *args, **kwargs)
