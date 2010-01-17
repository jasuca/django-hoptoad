import sys
import re
import logging
import itertools

from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings

from protocols import htv2
from handlers import get_handler


logger = logging.getLogger(__name__)


class HoptoadNotifierMiddleware(object):
    def __init__(self):
        """Initialize the middleware."""

        hoptoad_settings = getattr(settings, "HOPTOAD_SETTINGS", None)

        if not hoptoad_settings:
            # do some backward compatibility work to combine all hoptoad
            # settings in a dictionary
            hoptoad_settings = {}
            # for every attribute that starts with hoptoad
            for attr in itertools.ifilter(lambda x: x.startswith('HOPTOAD'),
                                          dir(settings)):
                hoptoad_settings[attr] = getattr(settings, attr)

            if not hoptoad_settings:
                # there were no settings for hoptoad at all..
                # should probably log here
                raise MiddlewareNotUsed

        if 'HOPTOAD_API_KEY' not in hoptoad_settings:
            # no api key, abort!
            raise MiddlewareNotUsed

        if setings.DEBUG:
            if not hoptoad_settings.get('HOPTOAD_NOTIFY_WHILE_DEBUG', None):
                # do not use hoptoad if you're in debug mode..
                raise MiddlewareNotUsed

        self.timeout = hoptoad_settings.get('HOPTOAD_TIMEOUT', None)
        self.notify_404 = hoptoad_settings.get('HOPTOAD_NOTIFY_404', False)
        self.notify_403 = hoptoad_settings.get('HOPTOAD_NOTIFY_403', False)

        ignorable_agents = hoptoad_settings.get('HOPTOAD_IGNORE_AGENTS', []
        self.ignore_agents = map(re.compile, ignorable_agents)

        self.handler = get_handler()

    def _ignore(self, request):
        """Return True if the given request should be ignored, False otherwise."""
        ua = request.META.get('HTTP_USER_AGENT', '')
        return any(i.search(ua) for i in self.ignore_agents)

    def process_response(self, request, response):
        """Process a reponse object.

        Hoptoad will be notified of a 404 error if the response is a 404
        and 404 tracking is enabled in the settings.

        Hoptoad will be notified of a 403 error if the response is a 403
        and 403 tracking is enabled in the settings.

        Regardless of whether Hoptoad is notified, the reponse object will
        be returned unchanged.
        """
        if self._ignore(request):
            return response

        if self.notify_404 and response.status_code == 404:
            error_class = 'Http404'

            message = 'Http404: Page not found at %s' % request.build_absolute_uri()
            payload = _generate_payload(request, error_class=error_class, message=message)

            self.handler.enqueue(payload, self.timeout)

        if self.notify_403 and response.status_code == 403:
            error_class = 'Http403'

            message = 'Http403: Forbidden at %s' % request.build_absolute_uri()
            payload = _generate_payload(request, error_class=error_class, message=message)

            self.handler.enqueue(payload, self.timeout)

        return response

    def process_exception(self, request, exc):
        """Process an exception.

        Hoptoad will be notified of the exception and None will be
        returned so that Django's normal exception handling will then
        be used.
        """
        if self._ignore(request):
            return None

        exc, _, tb = sys.exc_info()

        payload = _generate_payload(request, exc, tb)
        self.handler.enqueue(payload, self.timeout)

        return None

