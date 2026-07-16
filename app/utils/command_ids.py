import uuid


def generate_command_id() -> str:
    """Generate a unique command UUID."""
    return str(uuid.uuid4())
