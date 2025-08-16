"""
Progress Manager for displaying loading bars and status updates
Enhanced with live log updates and UI responsiveness
"""

from PyQt5.QtWidgets import QProgressDialog, QApplication, QTextEdit, QVBoxLayout, QWidget, QDialog, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QEventLoop
import time
from typing import Optional, Callable, List
from collections import deque
import threading


class LiveProgressDialog(QDialog):
    """Custom progress dialog with live log updates"""
    
    def __init__(self, title: str, message: str, maximum: int = 100, 
                 cancelable: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Message label
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # Progress bar
        from PyQt5.QtWidgets import QProgressBar, QPushButton
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Live log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(150)
        self.log_display.setPlainText("")
        layout.addWidget(self.log_display)
        
        # Cancel button
        if cancelable:
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.clicked.connect(self.reject)
            layout.addWidget(self.cancel_button)
            self.was_canceled = False
        else:
            self.was_canceled = False
            
        self.setLayout(layout)
        
        # Style the dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #3c3c3c;
                text-align: center;
                color: white;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4a9eff;
                border-radius: 2px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                border: 1px solid #444;
                padding: 5px;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                padding: 5px 15px;
                border-radius: 3px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
        """)
        
        # Log buffer for thread-safe updates
        self.log_buffer = deque(maxlen=100)
        self.log_lock = threading.Lock()
        
        # Timer for updating UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._process_log_buffer)
        self.update_timer.start(100)  # Update every 100ms
        
    def setValue(self, value: int):
        """Set progress bar value"""
        self.progress_bar.setValue(value)
        
    def setLabelText(self, text: str):
        """Update main message label"""
        self.message_label.setText(text)
        
    def add_log(self, message: str):
        """Add a log message to the live display (thread-safe)"""
        with self.log_lock:
            self.log_buffer.append(f"[{time.strftime('%H:%M:%S')}] {message}")
            
    def _process_log_buffer(self):
        """Process buffered log messages and update UI"""
        if self.log_buffer:
            with self.log_lock:
                new_messages = list(self.log_buffer)
                self.log_buffer.clear()
                
            if new_messages:
                current_text = self.log_display.toPlainText()
                if current_text:
                    current_text += "\n"
                current_text += "\n".join(new_messages)
                
                # Keep only last 20 lines to prevent overflow
                lines = current_text.split("\n")
                if len(lines) > 20:
                    current_text = "\n".join(lines[-20:])
                    
                self.log_display.setPlainText(current_text)
                # Scroll to bottom
                scrollbar = self.log_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
        # Process events to keep UI responsive
        QApplication.processEvents()
        
    def wasCanceled(self) -> bool:
        """Check if dialog was canceled"""
        return self.was_canceled
        
    def reject(self):
        """Handle cancel button"""
        self.was_canceled = True
        super().reject()
        
    def closeEvent(self, event):
        """Clean up on close"""
        self.update_timer.stop()
        super().closeEvent(event)


class ProgressManager(QObject):
    """Enhanced manager for displaying progress dialogs with live updates"""
    
    # Signals for updating progress from background threads
    update_progress = pyqtSignal(int)
    update_message = pyqtSignal(str)
    add_log_message = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialog: Optional[LiveProgressDialog] = None
        self.parent = parent
        self.pulse_timer = None
        self.pulse_value = 0
        self.is_pulsing = False
        self.last_update_time = 0
        self.update_frequency = 0.1  # Update UI every 100ms minimum
        
    def show_progress(self, title: str, message: str, maximum: int = 100, 
                     cancelable: bool = False, parent=None, show_logs: bool = True):
        """Show an enhanced progress dialog with optional live logs"""
        if self.dialog:
            self.close()
            
        parent = parent or self.parent
        self.dialog = LiveProgressDialog(title, message, maximum, cancelable, parent)
        
        # Connect signals
        self.update_progress.connect(self.dialog.setValue)
        self.update_message.connect(self.dialog.setLabelText)
        self.add_log_message.connect(self.dialog.add_log)
        
        # Hide log display if not needed
        if not show_logs:
            self.dialog.log_display.hide()
            self.dialog.setMinimumHeight(150)
            
        self.dialog.show()
        QApplication.processEvents()
        
    def start_pulse(self, title: str, message: str, parent=None, show_logs: bool = True):
        """Start a pulsing progress bar for indeterminate operations"""
        self.show_progress(title, message, 100, False, parent, show_logs)
        self.is_pulsing = True
        self.pulse_value = 0
        
        # Create timer for pulsing animation
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._pulse_animation)
        self.pulse_timer.start(50)  # Update every 50ms
        
    def _pulse_animation(self):
        """Animate the progress bar in a pulsing pattern"""
        if not self.dialog or not self.is_pulsing:
            if self.pulse_timer:
                self.pulse_timer.stop()
            return
            
        # Create a smooth pulse effect
        self.pulse_value = (self.pulse_value + 2) % 101
        if self.pulse_value <= 50:
            self.dialog.setValue(self.pulse_value * 2)
        else:
            self.dialog.setValue(100 - (self.pulse_value - 50) * 2)
        
        # Process events to prevent "Not Responding"
        QApplication.processEvents()
        
    def update(self, value: int, message: str = None, log: str = None, force: bool = False):
        """Update progress with rate limiting to prevent UI freezing"""
        current_time = time.time()
        
        # Rate limit updates unless forced
        if not force and (current_time - self.last_update_time) < self.update_frequency:
            return
            
        self.last_update_time = current_time
        
        if self.dialog:
            self.dialog.setValue(value)
            if message:
                self.dialog.setLabelText(message)
            if log:
                self.dialog.add_log(log)
                
            # Process events to keep UI responsive
            QApplication.processEvents()
            
    def set_message(self, message: str):
        """Update just the message"""
        if self.dialog:
            self.dialog.setLabelText(message)
            QApplication.processEvents()
            
    def log(self, message: str):
        """Add a log message to the live display"""
        if self.dialog:
            self.dialog.add_log(message)
            
    def process_events(self):
        """Manually process events to keep UI responsive"""
        QApplication.processEvents()
        
    def close(self):
        """Close the progress dialog"""
        self.is_pulsing = False
        if self.pulse_timer:
            self.pulse_timer.stop()
            self.pulse_timer = None
        if self.dialog:
            self.dialog.close()
            self.dialog = None
            
    def is_canceled(self) -> bool:
        """Check if the user canceled the operation"""
        return self.dialog.wasCanceled() if self.dialog else False


class ProgressContext:
    """Context manager for progress dialogs with live updates"""
    
    def __init__(self, parent, title: str, message: str, maximum: int = 100, 
                 pulse: bool = False, cancelable: bool = False, show_logs: bool = True):
        self.manager = ProgressManager(parent)
        self.title = title
        self.message = message
        self.maximum = maximum
        self.pulse = pulse
        self.cancelable = cancelable
        self.parent = parent
        self.show_logs = show_logs
        
    def __enter__(self):
        if self.pulse:
            self.manager.start_pulse(self.title, self.message, self.parent, self.show_logs)
        else:
            self.manager.show_progress(self.title, self.message, self.maximum, 
                                      self.cancelable, self.parent, self.show_logs)
        return self.manager
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.close()
        return False


def with_progress(title: str, message: str, pulse: bool = True, show_logs: bool = True):
    """Decorator to automatically show progress for a function"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Try to get parent widget from self
            parent = getattr(self, 'parent_window', self) if hasattr(self, 'parent_window') else self
            
            with ProgressContext(parent, title, message, pulse=pulse, show_logs=show_logs) as progress:
                # Pass progress manager to function if it accepts it
                import inspect
                sig = inspect.signature(func)
                if 'progress' in sig.parameters:
                    return func(self, *args, progress=progress, **kwargs)
                else:
                    return func(self, *args, **kwargs)
        return wrapper
    return decorator


class ResponsiveWorker(QThread):
    """Base worker thread that ensures UI responsiveness"""
    
    progress_update = pyqtSignal(int, str, str)  # value, message, log
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.error = None
        
    def run(self):
        """Run the function in a separate thread"""
        try:
            self.result = self.func(*self.args, **self.kwargs)
            self.finished_signal.emit(self.result)
        except Exception as e:
            self.error = str(e)
            self.error_signal.emit(self.error)
            
    def update_progress(self, value: int, message: str = None, log: str = None):
        """Emit progress update signal"""
        self.progress_update.emit(value, message or "", log or "")


def run_with_progress(parent, func, *args, title: str = "Processing", 
                      message: str = "Please wait...", **kwargs):
    """Run a function with a progress dialog, ensuring UI responsiveness"""
    progress = ProgressManager(parent)
    progress.show_progress(title, message, show_logs=True)
    
    # Create worker thread
    worker = ResponsiveWorker(func, *args, **kwargs)
    
    # Connect signals
    def on_progress(value, msg, log):
        progress.update(value, msg, log)
        
    worker.progress_update.connect(on_progress)
    
    # Start worker
    worker.start()
    
    # Process events while waiting
    while worker.isRunning():
        QApplication.processEvents()
        time.sleep(0.01)
        
        if progress.is_canceled():
            worker.terminate()
            worker.wait()
            progress.close()
            return None
            
    progress.close()
    
    if worker.error:
        raise Exception(worker.error)
        
    return worker.result