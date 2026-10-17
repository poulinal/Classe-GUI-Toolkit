"""Memory usage monitoring and logging utility for CGT application."""

import psutil
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Setup logger
_log_dir = Path(__file__).parent.parent.parent / "logs"
_log_dir.mkdir(exist_ok=True)
_log_file = _log_dir / f"memory_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logger = logging.getLogger("CGT_MemoryLogger")
logger.setLevel(logging.DEBUG)

# File handler
file_handler = logging.FileHandler(_log_file)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_formatter = logging.Formatter(
    '[%(levelname)s] %(message)s'
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


class MemoryMonitor:
    """Periodic memory usage monitoring."""
    
    def __init__(self, interval: float = 5.0, memory_alert_threshold: float = 0.9):
        """
        Initialize memory monitor.
        
        Args:
            interval: Monitoring interval in seconds (default: 5.0)
            memory_alert_threshold: Alert when memory exceeds this fraction (default: 0.9 = 90%)
        """
        self.interval = interval
        self.memory_alert_threshold = memory_alert_threshold
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._process = psutil.Process()
        
    def start(self):
        """Start background monitoring thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Memory monitoring started (interval: %.1f seconds, alert threshold: %.0f%%)" 
                   % (self.interval, self.memory_alert_threshold * 100))
        
    def stop(self):
        """Stop background monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Memory monitoring stopped")
        
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            try:
                self._check_memory()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")
                time.sleep(self.interval)
                
    def _check_memory(self):
        """Check current memory usage and log if needed."""
        try:
            mem_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
            vm = psutil.virtual_memory()
            
            # Check if exceeds threshold
            if memory_percent > (self.memory_alert_threshold * 100):
                logger.warning(
                    f"MEMORY ALERT: Process using {memory_percent:.1f}% of system memory "
                    f"({mem_info.rss / 1024 / 1024 / 1024:.2f} GB). "
                    f"System: {vm.percent:.1f}% ({vm.used / 1024 / 1024 / 1024:.2f} / {vm.total / 1024 / 1024 / 1024:.2f} GB available)"
                )
            else:
                # Log at debug level for non-alert cases
                logger.debug(
                    f"Memory: {memory_percent:.1f}% ({mem_info.rss / 1024 / 1024 / 1024:.2f} GB) | "
                    f"System: {vm.percent:.1f}% ({vm.used / 1024 / 1024 / 1024:.2f} / {vm.total / 1024 / 1024 / 1024:.2f} GB)"
                )
        except Exception as e:
            logger.error(f"Error checking memory: {e}")


def log_critical_point(operation_name: str, details: str = ""):
    """
    Log a critical operation point with current memory usage.
    
    Args:
        operation_name: Name of the operation (e.g., "DeltaPDF_Load")
        details: Additional details about the operation
    """
    try:
        process = psutil.Process()
        mem_info = process.memory_info()
        memory_percent = process.memory_percent()
        vm = psutil.virtual_memory()
        
        msg = f"CRITICAL: {operation_name} | Memory: {memory_percent:.1f}% ({mem_info.rss / 1024 / 1024 / 1024:.2f} GB)"
        if details:
            msg += f" | Details: {details}"
        msg += f" | System: {vm.percent:.1f}% free: {vm.available / 1024 / 1024 / 1024:.2f} GB"
        
        logger.info(msg)
    except Exception as e:
        logger.error(f"Error logging critical point: {e}")


def get_memory_stats() -> dict:
    """
    Get current memory statistics.
    
    Returns:
        Dictionary with memory usage information
    """
    try:
        process = psutil.Process()
        mem_info = process.memory_info()
        vm = psutil.virtual_memory()
        
        return {
            'process_memory_mb': mem_info.rss / 1024 / 1024,
            'process_memory_percent': process.memory_percent(),
            'system_memory_percent': vm.percent,
            'system_available_gb': vm.available / 1024 / 1024 / 1024,
            'system_total_gb': vm.total / 1024 / 1024 / 1024,
        }
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return {}


# Global monitor instance
_monitor: Optional[MemoryMonitor] = None


def initialize_monitor(interval: float = 5.0, memory_alert_threshold: float = 0.9) -> MemoryMonitor:
    """
    Initialize and start the global memory monitor.
    
    Args:
        interval: Monitoring interval in seconds
        memory_alert_threshold: Alert when memory exceeds this fraction
        
    Returns:
        The initialized MemoryMonitor instance
    """
    global _monitor
    if _monitor is None:
        _monitor = MemoryMonitor(interval=interval, memory_alert_threshold=memory_alert_threshold)
        _monitor.start()
    return _monitor


def cleanup_monitor():
    """Stop the global memory monitor."""
    global _monitor
    if _monitor:
        _monitor.stop()
        _monitor = None
