#!/usr/bin/env python3
"""
Test script for unified exception handling
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'spine_ultrasound_ui'))

from spine_ultrasound_ui.core.exception_handler import global_exception_handler, AppException, ErrorCategory, ErrorSeverity

def test_exception_handling():
    """Test the exception handler functionality"""

    # Test AppException
    try:
        raise AppException(
            "Test network error",
            ErrorCategory.NETWORK,
            ErrorSeverity.ERROR,
            "网络连接失败",
            "请检查网络连接"
        )
    except Exception as e:
        global_exception_handler.handle_exception(e, "test_network")

    # Test unexpected exception
    try:
        raise ValueError("Unexpected error")
    except Exception as e:
        global_exception_handler.handle_exception(e, "test_unexpected")

    # Test retry decorator
    @global_exception_handler.wrap_function
    def failing_function():
        raise ConnectionError("Connection failed")

    try:
        failing_function()
    except Exception as e:
        print(f"Function failed after retries: {e}")

    # Print error stats
    stats = global_exception_handler.get_error_stats()
    print("Error statistics:", stats)

if __name__ == "__main__":
    test_exception_handling()