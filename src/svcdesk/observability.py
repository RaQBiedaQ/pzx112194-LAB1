# ai-generated: 85% - Claude (AI assistant) generated this module from MONITORING-SPEC.md sections 1-2 under the student's direction; the student chose the bucket ladder (see config.py) and reviewed the middleware against the cardinality and route-template rules.
"""Lab 3: the RED request histogram (MONITORING-SPEC.md M-03 to M-07) and the ASGI middleware that
observes it. A dedicated registry (not prometheus_client's global default) keeps this module importable
more than once (e.g. by the own-tests suite) without a "duplicated metrics" error.

Deliberately plain prometheus_client, not an OpenTelemetry Prometheus exporter: the course's own
"when a check fails" table (HANDOUT.md) names an OTel exporter's extra labels (such as
`otel_scope_name`) as the usual cause of L3-CORE-2.05 (exactly three labels, no more).
"""
import time
from typing import Optional

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Histogram, generate_latest

from . import config

REGISTRY = CollectorRegistry()

# M-04: one histogram, in seconds, labelled exactly http_request_method, http_route,
# http_response_status_code (plus "le" on the buckets) - the OTel HTTP semantic conventions' Prometheus form.
REQUEST_HISTOGRAM = Histogram(
    "http_server_request_duration_seconds",
    "Duration of HTTP requests served by svcdesk, in seconds.",
    labelnames=("http_request_method", "http_route", "http_response_status_code"),
    buckets=config.REQUEST_DURATION_BUCKETS,
    registry=REGISTRY,
)

# M-05: every request that matches no route gets this one constant http_route value.
UNMATCHED_ROUTE = "unmatched"

# /metrics itself is left out (M-04 allows it): scraping it would otherwise observe the scrape request
# under its own route, which is not interesting and would complicate the cardinality probe (M-07).
_EXCLUDED_PATHS = frozenset({"/metrics"})


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


class MetricsMiddleware:
    """Pure ASGI middleware (not BaseHTTPMiddleware) so it sees the real status Starlette sends and the
    route Starlette's Router attaches to scope["route"] once it has matched - including the 404 path,
    where no route is attached and scope.get("route") stays None."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in _EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_holder = {"code": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration = time.perf_counter() - start
        route = scope.get("route")
        route_template: Optional[str] = getattr(route, "path", None)
        REQUEST_HISTOGRAM.labels(
            http_request_method=scope.get("method", "GET"),
            http_route=route_template or UNMATCHED_ROUTE,
            http_response_status_code=str(status_holder["code"]),
        ).observe(duration)
