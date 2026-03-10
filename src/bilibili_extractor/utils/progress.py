"""Progress display utilities."""


class ProgressBar:
    """Display progress for long-running operations."""

    def __init__(self, total: int, description: str = ""):
        """Initialize progress bar.

        Args:
            total: Total number of steps
            description: Description of the operation
        """
        self.total = total
        self.description = description
        self.current = 0

    def update(self, n: int = 1) -> None:
        """Update progress.

        Args:
            n: Number of steps to advance
        """
        raise NotImplementedError("Will be implemented in task 19")

    def close(self) -> None:
        """Close the progress bar."""
        raise NotImplementedError("Will be implemented in task 19")
