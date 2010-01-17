import sys
import re
import logging

from django.core.exceptions import MiddlewareNotUsed
from django.views.debug import get_safe_settings
from django.conf import settings

from protocols import htv2
from handlers import get_handler


logger = logging.getLogger(__name__)


class HoptoadNotifierMiddleware(object):
    def __init__(self):
        """Initialize the middleware."""
        all_settings = dir(settings)

        if 'HOPTOAD_API_KEY' not in all_settings or not settings.HOPTOAD_API_KEY:
            raise MiddlewareNotUsed

        if settings.DEBUG and \
           (not 'HOPTOAD_NOTIFY_WHILE_DEBUG' in all_settings
            or not settings.HOPTOAD_NOTIFY_WHILE_DEBUG ):
            raise MiddlewareNotUsed

        self.timeout = ( settings.HOPTOAD_TIMEOUT
                         if 'HOPTOAD_TIMEOUT' in all_settings else None )

        self.notify_404 = ( settings.HOPTOAD_NOTIFY_404
                            if 'HOPTOAD_NOTIFY_404' in all_settings else False )
        self.notify_403 = ( settings.HOPTOAD_NOTIFY_403
                            if 'HOPTOAD_NOTIFY_403' in all_settings else False )
        self.ignore_agents = ( map(re.compile, settings.HOPTOAD_IGNORE_AGENTS)
                            if 'HOPTOAD_IGNORE_AGENTS' in all_settings else [] )

        self.handler = get_handler(settings)

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

        excc, _, tb = sys.exc_info()

        payload = _generate_payload(request, exc, tb)
        self.handler.enqueue(payload, self.timeout)

        return None

