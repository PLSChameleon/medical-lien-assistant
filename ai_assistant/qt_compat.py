"""
Qt compatibility layer for PyQt5/PyQt6
"""

try:
    # Try PyQt5 first (preferred for compatibility)
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    QT_VERSION = 5
    print("Using PyQt5")
except ImportError:
    try:
        # Fall back to PyQt6
        from PyQt6.QtWidgets import *
        from PyQt6.QtCore import *
        from PyQt6.QtGui import *
        QT_VERSION = 6
        print("Using PyQt6")
        
        # PyQt6 compatibility adjustments
        Qt.KeepAspectRatio = Qt.AspectRatioMode.KeepAspectRatio
        Qt.SmoothTransformation = Qt.TransformationMode.SmoothTransformation
        Qt.AlignCenter = Qt.AlignmentFlag.AlignCenter
        Qt.AlignTop = Qt.AlignmentFlag.AlignTop
        Qt.AlignLeft = Qt.AlignmentFlag.AlignLeft
        Qt.AlignRight = Qt.AlignmentFlag.AlignRight
        Qt.AlignBottom = Qt.AlignmentFlag.AlignBottom
        Qt.AlignVCenter = Qt.AlignmentFlag.AlignVCenter
        Qt.AlignHCenter = Qt.AlignmentFlag.AlignHCenter
        Qt.Horizontal = Qt.Orientation.Horizontal
        Qt.Vertical = Qt.Orientation.Vertical
        Qt.NoPen = Qt.PenStyle.NoPen
        Qt.SolidLine = Qt.PenStyle.SolidLine
        Qt.DashLine = Qt.PenStyle.DashLine
        Qt.DotLine = Qt.PenStyle.DotLine
        Qt.DashDotLine = Qt.PenStyle.DashDotLine
        Qt.DashDotDotLine = Qt.PenStyle.DashDotDotLine
        Qt.CustomDashLine = Qt.PenStyle.CustomDashLine
        
    except ImportError as e:
        raise ImportError("Neither PyQt5 nor PyQt6 is installed. Please install one of them.") from e