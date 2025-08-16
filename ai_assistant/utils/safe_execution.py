"""
Safe Execution Decorators and Context Managers
Provides automatic error handling and recovery
"""

import functools
import logging
from typing import Any, Callable, Optional
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import Qt

from .error_tracker import track_error, get_error_tracker

def safe_execute(context: str = "", 
                 show_error: bool = True,
                 default_return: Any = None,
                 critical: bool = False):
    """
    Decorator to safely execute functions with error tracking
    
    Args:
        context: Description of what the function does
        show_error: Whether to show error dialog to user
        default_return: Value to return if error occurs
        critical: Whether this is a critical error that should stop execution
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Build context string
                func_context = context or f"Executing {func.__name__}"
                
                # Get additional info
                additional_info = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs": list(kwargs.keys())
                }
                
                # Track the error
                severity = "CRITICAL" if critical else "ERROR"
                error_report = track_error(
                    e, 
                    func_context,
                    severity=severity,
                    **additional_info
                )
                
                # Show error to user if requested
                if show_error:
                    try:
                        QApplication.restoreOverrideCursor()
                        
                        if critical:
                            error_msg = f"""
                            <h3>Critical Error Occurred</h3>
                            <p><b>What happened:</b> {func_context}</p>
                            <p><b>Error:</b> {str(e)}</p>
                            <p><b>Error Code:</b> {type(e).__name__}</p>
                            <br>
                            <p>This error has been logged. Please contact support with error code: 
                            <b>{error_report.get('session_id', 'unknown')}</b></p>
                            """
                            QMessageBox.critical(None, "Critical Error", error_msg)
                        else:
                            error_msg = f"""
                            <b>An error occurred:</b><br>
                            {str(e)}<br><br>
                            <i>This has been logged for debugging.</i>
                            """
                            QMessageBox.warning(None, "Error", error_msg)
                    except:
                        # If GUI is not available, just log
                        logging.error(f"Could not show error dialog: {e}")
                
                # Log to console
                logging.error(f"[{severity}] {func_context}: {e}")
                
                # Return default value
                return default_return
                
        return wrapper
    return decorator

def safe_async_execute(context: str = ""):
    """Decorator for async functions with error tracking"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                func_context = context or f"Async executing {func.__name__}"
                track_error(e, func_context)
                logging.error(f"{func_context}: {e}")
                return None
        return wrapper
    return decorator

class SafeExecutionContext:
    """Context manager for safe execution blocks"""
    
    def __init__(self, context: str = "", suppress: bool = False, default: Any = None):
        """
        Args:
            context: Description of the operation
            suppress: Whether to suppress the exception
            default: Default value to return if error occurs
        """
        self.context = context
        self.suppress = suppress
        self.default = default
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.error = exc_val
            track_error(exc_val, self.context)
            logging.error(f"{self.context}: {exc_val}")
            
            if self.suppress:
                return True  # Suppress the exception
        return False

def retry_on_error(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator to retry function on error
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between attempts in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        logging.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                        time.sleep(delay)
                    else:
                        logging.error(f"All {max_attempts} attempts failed for {func.__name__}")
                        track_error(e, f"Failed after {max_attempts} attempts: {func.__name__}")
            
            raise last_error
        return wrapper
    return decorator

def validate_input(validation_func: Callable[[Any], bool], 
                  error_message: str = "Invalid input"):
    """
    Decorator to validate function inputs
    
    Args:
        validation_func: Function to validate the first argument
        error_message: Error message if validation fails
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if args and not validation_func(args[0]):
                error = ValueError(error_message)
                track_error(error, f"Input validation failed for {func.__name__}")
                raise error
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Convenience functions for common validations
def ensure_not_none(value: Any) -> bool:
    """Check if value is not None"""
    return value is not None

def ensure_not_empty(value: Any) -> bool:
    """Check if value is not empty"""
    return bool(value)

def ensure_file_exists(filepath: str) -> bool:
    """Check if file exists"""
    import os
    return os.path.exists(filepath) if filepath else False