"""
OpenTelemetry Distributed Tracing for FastAPI Services.

This module provides distributed tracing configuration for all AI microservices.
"""
import logging
import os
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def setup_tracing(app, service_name: str):
    """
    Configure OpenTelemetry tracing for FastAPI application.

    Args:
        app: FastAPI application instance
        service_name: Name of the service (e.g., "recommendation-engine")

    Returns:
        Tracer instance for manual instrumentation
    """
    # Only setup tracing if Jaeger is configured
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

        # Auto-instrumentation
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: service_name
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # Configure Jaeger exporter
        jaeger_port = int(os.getenv('JAEGER_AGENT_PORT', 6831))
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )

        # Add span processor
        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        logger.info(f"Configured Jaeger exporter for {service_name}: {jaeger_host}:{jaeger_port}")

        # Auto-instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        logger.info(f"Instrumented FastAPI for {service_name}")

        # Instrument HTTP client
        HTTPXClientInstrumentor().instrument()
        logger.info(f"Instrumented HTTPX (HTTP client) for {service_name}")

        # Instrument Redis
        try:
            RedisInstrumentor().instrument()
            logger.info(f"Instrumented Redis for {service_name}")
        except Exception as e:
            logger.warning(f"Failed to instrument Redis: {e}")

        logger.info(f"OpenTelemetry tracing configured successfully for {service_name}")

        # Return tracer for manual instrumentation
        return trace.get_tracer(service_name)

    except ImportError as e:
        logger.warning(f"OpenTelemetry packages not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to setup tracing for {service_name}: {e}")
        return None


def get_tracer(service_name: str = __name__):
    """
    Get a tracer instance for manual instrumentation.

    Args:
        service_name: Name of the service

    Returns:
        Tracer instance or None if tracing not configured
    """
    try:
        from opentelemetry import trace
        return trace.get_tracer(service_name)
    except ImportError:
        return None


@contextmanager
def trace_span(span_name: str, attributes: dict = None):
    """
    Context manager for creating traced spans.

    Usage:
        with trace_span("predict_recommendation", {"user_id": user_id}):
            # your code here
            result = model.predict()

    Args:
        span_name: Name of the span
        attributes: Optional attributes to add to the span
    """
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
    """
    Add attributes to the current span.

    Usage:
        add_span_attributes(
            model_version="v1.2.3",
            confidence_score=0.95,
            prediction_time_ms=23.5
        )

    Args:
        **attributes: Key-value pairs to add to the current span
    """
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
    """
    Record an exception in the current span.

    Args:
        exception: The exception to record
        attributes: Optional additional attributes
    """
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
    """
    Inject trace context into HTTP headers for propagation.

    Usage:
        headers = {"Content-Type": "application/json"}
        headers = inject_trace_context(headers)
        response = httpx.get(url, headers=headers)

    Args:
        headers: Existing headers dict

    Returns:
        Headers dict with trace context injected
    """
    try:
        from opentelemetry.propagate import inject
        inject(headers)
    except Exception as e:
        logger.debug(f"Failed to inject trace context: {e}")
    return headers


def extract_trace_context(headers: dict):
    """
    Extract trace context from HTTP headers.

    This is typically done automatically by FastAPI instrumentation,
    but can be used manually if needed.

    Args:
        headers: Request headers
    """
    try:
        from opentelemetry.propagate import extract
        return extract(headers)
    except Exception as e:
        logger.debug(f"Failed to extract trace context: {e}")
        return None
