"""operations domain package."""

def process_request(*args, **kwargs):
    """Load Operations lazily so workflow imports remain acyclic."""
    from .operations_agent import process_request as run
    return run(*args, **kwargs)
