import logging

import os

logger = logging.getLogger(__name__)



def setup_tracing():

    jaeger_host = os.getenv('JAEGER_AGENT_HOST')

    if not jaeger_host:

        logger.info("Jaeger not configured, skipping tracing setup")

        return


    try:

        from opentelemetry import trace

        from opentelemetry.sdk.trace import TracerProvider

        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        from opentelemetry.exporter.jaeger.thrift import JaegerExporter


        from opentelemetry.instrumentation.django import DjangoInstrumentor

        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

        from opentelemetry.instrumentation.redis import RedisInstrumentor

        from opentelemetry.instrumentation.requests import RequestsInstrumentor


        try:

            from opentelemetry.instrumentation.celery import CeleryInstrumentor

        except ImportError:

            CeleryInstrumentor = None


        service_name = os.getenv('OTEL_SERVICE_NAME', 'ecommerce-backend')

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


        logger.info(f"Configured Jaeger exporter: {jaeger_host}:{jaeger_port}")


        DjangoInstrumentor().instrument()

        logger.info("Instrumented Django")


        Psycopg2Instrumentor().instrument()

        logger.info("Instrumented Psycopg2 (PostgreSQL)")


        RedisInstrumentor().instrument()

        logger.info("Instrumented Redis")


        RequestsInstrumentor().instrument()

        logger.info("Instrumented Requests (HTTP client)")


        if CeleryInstrumentor:

            CeleryInstrumentor().instrument()

            logger.info("Instrumented Celery")


        logger.info(f"Tracing configured for {service_name}")


    except ImportError as e:

        logger.warning(f"OpenTelemetry packages not installed: {e}")

    except Exception as e:

        logger.error(f"Failed to setup tracing: {e}")



def get_tracer(name: str = __name__):

    try:

        from opentelemetry import trace

        return trace.get_tracer(name)

    except ImportError:

        return None



def trace_function(span_name: str = None):

    def decorator(func):

        def wrapper(*args, **kwargs):

            tracer = get_tracer()

            if not tracer:

                return func(*args, **kwargs)


            name = span_name or func.__name__

            with tracer.start_as_current_span(name):

                return func(*args, **kwargs)


        return wrapper

    return decorator



def add_span_attributes(**attributes):

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

    try:

        from opentelemetry import trace


        span = trace.get_current_span()

        if span and span.is_recording():

            span.record_exception(exception)

            if attributes:

                for key, value in attributes.items():

                    span.set_attribute(key, value)

    except Exception as e:

        logger.debug(f"Failed to record exception: {e}")

