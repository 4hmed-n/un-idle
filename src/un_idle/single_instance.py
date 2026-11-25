"""Single instance lock to prevent multiple app instances."""
from __future__ import annotations

import logging
import platform
import sys
from pathlib import Path

logger = logging.getLogger("un_idle.single_instance")


class SingleInstanceLock:
    """Ensures only one instance of the app runs at a time."""
    
    def __init__(self, name: str = "un-idle"):
        self._name = name
        self._lock = None
        self._acquired = False
        
    def acquire(self) -> bool:
        """
        Try to acquire single-instance lock.
        Returns True if acquired, False if another instance is running.
        """
        system = platform.system()
        
        if system == "Windows":
            return self._acquire_windows()
        else:
            return self._acquire_unix()
    
    def _acquire_windows(self) -> bool:
        """Use named mutex on Windows."""
        try:
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.argtypes = [
                wintypes.LPVOID,
                wintypes.BOOL,
                wintypes.LPCWSTR
            ]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            
            ERROR_ALREADY_EXISTS = 183
            mutex_name = f"Global\\{self._name}"
            
            self._lock = kernel32.CreateMutexW(None, True, mutex_name)
            
            if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
                logger.info("Another instance is already running")
                return False
            
            logger.info("Single instance lock acquired (Windows mutex)")
            self._acquired = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to create mutex: {e}")
            # Fail open - allow running even if lock fails
            return True
    
    def _acquire_unix(self) -> bool:
        """Use lock file on Unix-like systems."""
        try:
            import fcntl
            
            # Use temp directory for lock file
            if platform.system() == "Darwin":
                lock_dir = Path.home() / "Library" / "Application Support" / "un-idle"
            else:
                import os
                lock_dir = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
            
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_file = lock_dir / f"{self._name}.lock"
            
            self._lock = open(lock_file, 'w')
            fcntl.lockf(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock.write(str(Path.cwd()))
            self._lock.flush()
            
            logger.info(f"Single instance lock acquired (Unix lock file: {lock_file})")
            self._acquired = True
            return True
            
        except BlockingIOError:
            logger.info("Another instance is already running")
            return False
        except Exception as e:
            logger.error(f"Failed to create lock file: {e}")
            # Fail open
            return True
    
    def release(self) -> None:
        """Release the lock."""
        if not self._acquired:
            return
        
        system = platform.system()
        
        if system == "Windows":
            try:
                if self._lock:
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    kernel32.CloseHandle(self._lock)
                    logger.debug("Windows mutex released")
            except Exception as e:
                logger.error(f"Failed to release mutex: {e}")
        else:
            try:
                if self._lock:
                    import fcntl
                    fcntl.lockf(self._lock, fcntl.LOCK_UN)
                    self._lock.close()
                    logger.debug("Unix lock file released")
            except Exception as e:
                logger.error(f"Failed to release lock file: {e}")
        
        self._acquired = False
    
    def __enter__(self):
        if not self.acquire():
            logger.info("Exiting because another instance is running")
            sys.exit(0)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
