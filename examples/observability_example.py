"""
Example: Using SkillMeat Observability Features

This example demonstrates how to use structured logging, distributed tracing,
and metrics in your SkillMeat code.
"""

import time
import logging
from skillmeat.observability import setup_logging, LogContext, trace_operation
from skillmeat.observability.metrics import (
    bundle_operation_duration,
    bundle_exports_total,
    artifact_operations_total,
    track_operation
)


def main():
    """Main function demonstrating observability features."""

    # 1. Setup structured logging
    print("=== Setting up structured logging ===")
    setup_logging(level=logging.INFO, structured=True)

    # Get logger with automatic context
    from skillmeat.observability.logging_config import get_logger_with_context
    logger = get_logger_with_context(__name__)

    # 2. Set request context (simulating an API request)
    print("\n=== Setting request context ===")
    trace_id = LogContext.set_trace_id()
    request_id = LogContext.set_request_id()
    LogContext.set_user_id("user-123")

    print(f"Trace ID: {trace_id}")
    print(f"Request ID: {request_id}")

    # 3. Structured logging with context
    print("\n=== Structured logging ===")
    logger.info("Starting bundle export operation", extra={
        "bundle_id": "bundle-456",
        "operation": "export",
        "format": "tar.gz"
    })

    # 4. Distributed tracing
    print("\n=== Distributed tracing ===")
    with trace_operation("bundle.export", bundle_id="bundle-456") as span:
        # Simulate loading artifacts
        time.sleep(0.1)
        span.set_attribute("artifact_count", 5)
        span.add_event("artifacts_loaded")

        logger.info("Artifacts loaded", extra={
            "count": 5
        })

        # Simulate nested operation
        with trace_operation("bundle.validate") as validate_span:
            time.sleep(0.05)
            validate_span.set_attribute("validation_status", "passed")
            validate_span.add_event("validation_complete")

            logger.info("Bundle validation complete")

        # Simulate export
        time.sleep(0.15)
        span.set_attribute("output_size_bytes", 1024000)
        span.add_event("export_complete")

        logger.info("Bundle export complete", extra={
            "size_bytes": 1024000,
            "format": "tar.gz"
        })

    # 5. Recording metrics
    print("\n=== Recording metrics ===")

    # Counter
    bundle_exports_total.labels(
        status="success",
        format="tar.gz"
    ).inc()
    print("Incremented bundle exports counter")

    # Histogram (manual timing)
    start = time.perf_counter()
    time.sleep(0.2)
    duration = time.perf_counter() - start
    bundle_operation_duration.labels(operation="export").observe(duration)
    print(f"Recorded bundle operation duration: {duration:.3f}s")

    # 6. Using decorator for automatic timing
    print("\n=== Using decorators ===")

    @track_operation("artifact", "deploy")
    def deploy_artifact(artifact_id: str):
        """Example function with automatic timing."""
        logger.info(f"Deploying artifact {artifact_id}")
        time.sleep(0.1)
        logger.info(f"Artifact {artifact_id} deployed")

    deploy_artifact("artifact-789")

    # Record artifact operation metrics
    artifact_operations_total.labels(
        operation="deploy",
        type="skill",
        status="success"
    ).inc()

    # 7. Error handling with tracing
    print("\n=== Error handling ===")
    try:
        with trace_operation("bundle.import", bundle_id="bundle-error") as span:
            logger.info("Attempting bundle import")
            # Simulate error
            raise ValueError("Invalid bundle format")
    except ValueError as e:
        logger.error("Bundle import failed", exc_info=True, extra={
            "bundle_id": "bundle-error",
            "error_type": type(e).__name__
        })

    # 8. View context
    print("\n=== Current context ===")
    context = LogContext.get_context()
    print(f"Trace ID: {context['trace_id']}")
    print(f"Request ID: {context['request_id']}")
    print(f"User ID: {context['user_id']}")

    print("\n=== Observability example complete ===")
    print("Check logs above to see structured JSON output")
    print("In production, these logs would be:")
    print("  - Shipped to Loki for aggregation")
    print("  - Traced in distributed tracing system")
    print("  - Metrics collected by Prometheus")


if __name__ == "__main__":
    main()
