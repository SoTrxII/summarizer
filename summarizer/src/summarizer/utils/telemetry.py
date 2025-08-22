from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_traces_provider(resource: Resource, endpoint: str) -> TracerProvider:
    tracer_provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    return tracer_provider


def setup_log_provider(resource: Resource, endpoint: str) -> LoggerProvider:
    logger_provider = LoggerProvider(resource=resource)
    # Aspire Dashboard logs visualization
    exporter = OTLPLogExporter(endpoint=endpoint)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

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
