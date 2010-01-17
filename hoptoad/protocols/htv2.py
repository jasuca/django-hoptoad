import traceback
import urllib2
import yaml
from xml.dom.minidom import getDOMImplementation

from django.views.debug import get_safe_settings
from django.conf import settings


def _parse_environment(request):
    """Return an environment mapping for a notification from the given request."""
    env = dict( (str(k), str(v)) for (k, v) in get_safe_settings().items() )
    env.update( dict( (str(k), str(v)) for (k, v) in request.META.items() ) )

    env['REQUEST_URI'] = request.build_absolute_uri()

    return env

def _parse_traceback(trace):
    """Return the given traceback string formatted for a notification."""
    p_traceback = [ "%s:%d:in `%s'" % (filename, lineno, funcname)
                    for filename, lineno, funcname, _
                    in traceback.extract_tb(trace) ]
    p_traceback.reverse()

    return p_traceback

def _parse_message(exc):
    """Return a message for a notification from the given exception."""
    return '%s: %s' % (exc.__class__.__name__, str(exc))

def _parse_request(request):
    """Return a request mapping for a notification from the given request."""
    request_get = dict( (str(k), str(v)) for (k, v) in request.GET.items() )
    request_post = dict( (str(k), str(v)) for (k, v) in request.POST.items() )
    return request_post if request_post else request_get

def _parse_session(session):
    """Return a request mapping for a notification from the given session."""
    return dict( (str(k), str(v)) for (k, v) in session.items() )


def generate_payload(request):
    """Generate an XML payload for a Hoptoad notification.

    Parameters:
    request -- A Django HTTPRequest.  This is required.

    """
    p_message = message if message else _parse_message(exc)
    p_error_class = error_class if error_class else exc.__class__.__name__
    p_traceback = _parse_traceback(trace) if trace else []
    p_environment = _parse_environment(request)
    p_request = _parse_request(request)
    p_session = _parse_session(request.session)

    # api v2 from: http://help.hoptoadapp.com/faqs/api-2/notifier-api-v2
    xdoc = getDOMImplementation().createDocument(None, "notice", None)
    # set the notice element to version 2.0
    xdoc.firstChild.setAttribute('version', '2.0')
    xmlify(xmlresp, ())
    # generate notice..

    return xmlresp.toxml('utf-8')

    return yaml.dump({ 'notice': {
        'api_key':       settings.HOPTOAD_API_KEY,
        'error_class':   p_error_class,
        'error_message': p_message,
        'backtrace':     p_traceback,
        'request':       { 'url': request.build_absolute_uri(),
                           'params': p_request },
        'session':       { 'key': '', 'data': p_session },
        'environment':   p_environment,
    }}, default_flow_style=False)

def _ride_the_toad(payload, timeout):
    """Send a notification (an HTTP POST request) to Hoptoad.

    Parameters:
    payload -- the YAML payload for the request from _generate_payload()
    timeout -- the maximum timeout, in seconds, or None to use the default
    """
    headers = { 'Content-Type': 'application/x-yaml',
                'Accept': 'text/xml, application/xml', }
    r = urllib2.Request('http://hoptoadapp.com/notices', payload, headers)
    try:
        if timeout:
            urllib2.urlopen(r, timeout=timeout)
        else:
            urllib2.urlopen(r)
    except urllib2.URLError:
        pass

def report(payload, timeout):
    return _ride_the_toad(payload, timeout)
