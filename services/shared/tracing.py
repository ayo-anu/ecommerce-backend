"""OpenTelemetry tracing for FastAPI services."""
import logging
import os
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def setup_tracing(app, service_name: str):
    """Configure OpenTelemetry tracing for a FastAPI app."""
    jaeger_host = os.getenv('JAEGER_AGENT_HOST')
    if not jaeger_host:
        logger.info(f"Jaeger not configured for {service_name}, skipping tracing setup")
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter

        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        resource = Resource(attributes={
            SERVICE_NAME: service_name
        })

        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        jaeger_port = int(os.getenv('JAEGER_AGENT_PORT', 6831))
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )

        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        logger.info(f"Configured Jaeger exporter for {service_name}: {jaeger_host}:{jaeger_port}")

        FastAPIInstrumentor.instrument_app(app)
        logger.info(f"Instrumented FastAPI for {service_name}")

        HTTPXClientInstrumentor().instrument()
        logger.info(f"Instrumented HTTPX (HTTP client) for {service_name}")

        try:
            RedisInstrumentor().instrument()
            logger.info(f"Instrumented Redis for {service_name}")
        except Exception as e:
            logger.warning(f"Failed to instrument Redis: {e}")

        logger.info(f"OpenTelemetry tracing configured successfully for {service_name}")

        return trace.get_tracer(service_name)

    except ImportError as e:
        logger.warning(f"OpenTelemetry packages not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to setup tracing for {service_name}: {e}")
        return None


def get_tracer(service_name: str = __name__):
    """Get a tracer instance."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(service_name)
    except ImportError:
        return None


@contextmanager
def trace_span(span_name: str, attributes: dict = None):
    """Context manager for traced spans."""
    tracer = get_tracer()
    if not tracer:
        yield None
        return

    with tracer.start_as_current_span(span_name) as span:
        if attributes and span.is_recording():
            for key, value in attributes.items():
                if value is None:
                    continue
                elif isinstance(value, (str, int, float, bool)):
                    span.set_attribute(key, value)
                else:
                    span.set_attribute(key, str(value))
        yield span


def add_span_attributes(**attributes):
    """Add attributes to the current span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            for key, value in attributes.items():
                if value is None:
                    continue
                elif isinstance(value, (str, int, float, bool)):
                    span.set_attribute(key, value)
                else:
                    span.set_attribute(key, str(value))
    except Exception as e:
        logger.debug(f"Failed to add span attributes: {e}")


def record_exception(exception: Exception, attributes: dict = None):
    """Record an exception on the current span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            span.record_exception(exception)
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))
    except Exception as e:
        logger.debug(f"Failed to record exception: {e}")


def inject_trace_context(headers: dict) -> dict:
    """Inject trace context into HTTP headers."""
    try:
        from opentelemetry.propagate import inject
        inject(headers)
    except Exception as e:
        logger.debug(f"Failed to inject trace context: {e}")
    return headers


def extract_trace_context(headers: dict):
    """Extract trace context from HTTP headers."""
    try:
        from opentelemetry.propagate import extract
        return extract(headers)
    except Exception as e:
        logger.debug(f"Failed to extract trace context: {e}")
        return None
