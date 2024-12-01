"""
Custom exceptions for the networking_base application.
These exceptions help provide specific error handling for different scenarios
in our CRM system.
"""


class AnalysisError(Exception):
    """
    Exception raised when interaction analysis fails.
    This could be due to API errors, parsing issues, or other analysis-related problems.

    Attributes:
        message -- explanation of the error
        original_error -- the underlying error that caused this exception (optional)
    """

    def __init__(self, message, original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
