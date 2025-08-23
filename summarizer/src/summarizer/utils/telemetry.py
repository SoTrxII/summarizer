import logging
from asyncio import iscoroutinefunction
from functools import wraps

from opentelemetry.context import get_current
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer

tracer = get_tracer(__name__)


def setup_traces_provider(resource: Resource, endpoint: str) -> TracerProvider:
    tracer_provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    return tracer_provider


def setup_log_provider(resource: Resource, endpoint: str) -> LoggerProvider:
    logger_provider = LoggerProvider(resource=resource)

    # Setup OTLP exporter for Aspire Dashboard
    otlp_exporter = OTLPLogExporter(endpoint=endpoint)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(otlp_exporter))

    # Configure Python logging to use OpenTelemetry
    handler = LoggingHandler(level=logging.NOTSET,
                             logger_provider=logger_provider)

    # Get root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    return logger_provider


def setup_metrics_provider(resource: Resource, endpoint: str) -> MeterProvider:
    exporter = OTLPMetricExporter(endpoint=endpoint)

    return MeterProvider(
        metric_readers=[PeriodicExportingMetricReader(
            exporter, export_interval_millis=2000)],
        resource=resource,
        views=[
            View(instrument_name="*"),
        ],
    )


def span(func):
    """
    Decorator to start a new OpenTelemetry span and preserve the parent-child relationship.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        parent_context = get_current()
        with tracer.start_as_current_span(func.__name__, context=parent_context):
            return await func(*args, **kwargs)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        parent_context = get_current()
        with tracer.start_as_current_span(func.__name__, context=parent_context):
            return func(*args, **kwargs)

    return async_wrapper if iscoroutinefunction(func) else sync_wrapper
