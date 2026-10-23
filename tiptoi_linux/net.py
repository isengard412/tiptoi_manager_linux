"""HTTPS-only URL opener shared by the catalog, portal and .gme downloads."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request

from tiptoi_linux.i18n import _


class HTTPSOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if urllib.parse.urlparse(newurl).scheme != "https":
            # WHY: urlopen follows 301/302 to plain http by default, silently defeating the scheme check below
            raise urllib.error.URLError(
                _("refusing to follow redirect to non-https URL: {url}").format(url=newurl)
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class UserAgentHandler(urllib.request.BaseHandler):
    """Send a project User-Agent - ravensburger.cloud answers 403 to the default Python-urllib one."""

    USER_AGENT = "tiptoi-manager-linux/0.1 (+https://github.com/isengard412/tiptoi_manager_linux)"

    def http_request(self, request):
        if not request.has_header("User-Agent"):
            request.add_unredirected_header("User-Agent", self.USER_AGENT)
        return request

    https_request = http_request


https_opener = urllib.request.build_opener(HTTPSOnlyRedirectHandler, UserAgentHandler)
