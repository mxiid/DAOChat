from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import Counter, Histogram
import time
from functools import wraps
import logging
from typing import Callable, Any

# Metrics
CHAT_REQUESTS = Counter('chat_requests_total', 'Total chat requests', ['status'])
RESPONSE_TIME = Histogram('response_time_seconds', 'Response time in seconds')
TOKEN_USAGE = Counter('token_usage_total', 'Total tokens used', ['type'])

logger = logging.getLogger(__name__)

class ChatMonitoring:
    @staticmethod
    def track_request(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                CHAT_REQUESTS.labels(status='success').inc()
                return result
            except Exception as e:
                CHAT_REQUESTS.labels(status='error').inc()
                logger.error(f"Error in {func.__name__}: {str(e)}")
                raise e
            finally:
                RESPONSE_TIME.observe(time.time() - start_time)
        return wrapper

    @staticmethod
    def track_tokens(prompt_tokens: int, completion_tokens: int):
        TOKEN_USAGE.labels(type='prompt').inc(prompt_tokens)
        TOKEN_USAGE.labels(type='completion').inc(completion_tokens) 