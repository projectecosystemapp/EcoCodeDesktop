"""Performance optimizations for spec-driven workflow operations."""

import asyncio
import functools
import hashlib
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

from eco_api.logging import get_spec_logger

logger = get_spec_logger('performance')

F = TypeVar('F', bound=Callable[..., Any])

# Global thread pool for I/O operations
_io_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def get_io_executor() -> ThreadPoolExecutor:
    """Get or create the global I/O thread pool executor."""
    global _io_executor
    if _io_executor is None:
        with _executor_lock:
            if _io_executor is None:
                _io_executor = ThreadPoolExecutor(
                    max_workers=4,
                    thread_name_prefix='spec_io'
                )
    return _io_executor


class FileCache:
    """Simple file content cache with TTL and checksum validation."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def _evict_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, access_time in self._access_times.items()
            if current_time - access_time > self.ttl_seconds
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)
    
    def _evict_lru(self) -> None:
        """Remove least recently used entries if cache is full."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._access_times.keys(), key=self._access_times.get)
            self._cache.pop(oldest_key, None)
            self._access_times.pop(oldest_key, None)
    
    def get(self, file_path: Union[str, Path]) -> Optional[str]:
        """Get cached file content if valid."""
        key = str(file_path)
        
        with self._lock:
            self._evict_expired()
            
            if key not in self._cache:
                return None
            
            # Check if file has been modified
            try:
                file_stat = Path(file_path).stat()
                cached_entry = self._cache[key]
                
                if (cached_entry['mtime'] != file_stat.st_mtime or 
                    cached_entry['size'] != file_stat.st_size):
                    # File has been modified, remove from cache
                    self._cache.pop(key, None)
                    self._access_times.pop(key, None)
                    return None
                
                # Update access time
                self._access_times[key] = time.time()
                return cached_entry['content']
                
            except (OSError, KeyError):
                # File doesn't exist or cache entry is corrupted
                self._cache.pop(key, None)
                self._access_times.pop(key, None)
                return None
    
    def put(self, file_path: Union[str, Path], content: str) -> None:
        """Cache file content with metadata."""
        key = str(file_path)
        
        try:
            file_stat = Path(file_path).stat()
            
            with self._lock:
                self._evict_expired()
                self._evict_lru()
                
                self._cache[key] = {
                    'content': content,
                    'mtime': file_stat.st_mtime,
                    'size': file_stat.st_size,
                    'checksum': hashlib.md5(content.encode()).hexdigest()
                }
                self._access_times[key] = time.time()
                
        except OSError:
            # File doesn't exist, don't cache
            pass
    
    def invalidate(self, file_path: Union[str, Path]) -> None:
        """Remove file from cache."""
        key = str(file_path)
        with self._lock:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()


# Global file cache instance
_file_cache = FileCache()


def cached_file_read(file_path: Union[str, Path]) -> str:
    """Read file with caching for improved performance."""
    # Check cache first
    cached_content = _file_cache.get(file_path)
    if cached_content is not None:
        logger.debug(f"Cache hit for file: {file_path}")
        return cached_content
    
    # Read from disk
    logger.debug(f"Cache miss for file: {file_path}")
    try:
        content = Path(file_path).read_text(encoding='utf-8')
        _file_cache.put(file_path, content)
        return content
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise


async def async_file_read(file_path: Union[str, Path]) -> str:
    """Asynchronously read file with caching."""
    loop = asyncio.get_event_loop()
    executor = get_io_executor()
    return await loop.run_in_executor(executor, cached_file_read, file_path)


async def async_file_write(file_path: Union[str, Path], content: str) -> None:
    """Asynchronously write file and update cache."""
    def _write_file():
        Path(file_path).write_text(content, encoding='utf-8')
        _file_cache.put(file_path, content)
    
    loop = asyncio.get_event_loop()
    executor = get_io_executor()
    await loop.run_in_executor(executor, _write_file)


class AICallCache:
    """Cache for AI API calls to reduce redundant requests."""
    
    def __init__(self, max_size: int = 50, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def _make_key(self, model_id: str, prompt: str, **kwargs) -> str:
        """Create cache key from AI call parameters."""
        key_data = f"{model_id}:{prompt}:{str(sorted(kwargs.items()))}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _evict_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, access_time in self._access_times.items()
            if current_time - access_time > self.ttl_seconds
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)
    
    def _evict_lru(self) -> None:
        """Remove least recently used entries if cache is full."""
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._access_times.keys(), key=self._access_times.get)
            self._cache.pop(oldest_key, None)
            self._access_times.pop(oldest_key, None)
    
    def get(self, model_id: str, prompt: str, **kwargs) -> Optional[str]:
        """Get cached AI response if available."""
        key = self._make_key(model_id, prompt, **kwargs)
        
        with self._lock:
            self._evict_expired()
            
            if key in self._cache:
                self._access_times[key] = time.time()
                return self._cache[key]['response']
            
            return None
    
    def put(self, model_id: str, prompt: str, response: str, **kwargs) -> None:
        """Cache AI response."""
        key = self._make_key(model_id, prompt, **kwargs)
        
        with self._lock:
            self._evict_expired()
            self._evict_lru()
            
            self._cache[key] = {
                'response': response,
                'timestamp': time.time()
            }
            self._access_times[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cached responses."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()


# Global AI call cache
_ai_cache = AICallCache()


def cached_ai_call(func: F) -> F:
    """Decorator to cache AI API calls."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract model_id and prompt from arguments
        model_id = kwargs.get('model_id') or (args[0] if args else None)
        prompt = kwargs.get('prompt') or (args[1] if len(args) > 1 else None)
        
        if not model_id or not prompt:
            # Can't cache without model_id and prompt
            return func(*args, **kwargs)
        
        # Check cache
        cached_response = _ai_cache.get(model_id, prompt, **kwargs)
        if cached_response is not None:
            logger.debug(f"AI cache hit for model: {model_id}")
            return cached_response
        
        # Call function and cache result
        logger.debug(f"AI cache miss for model: {model_id}")
        response = func(*args, **kwargs)
        
        if response:  # Only cache successful responses
            _ai_cache.put(model_id, prompt, response, **kwargs)
        
        return response
    
    return wrapper


def performance_monitor(func: F) -> F:
    """Decorator to monitor function performance."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(
                f"Performance: {func.__name__} completed in {execution_time:.3f}s",
                extra={'execution_time': execution_time, 'function': func.__name__}
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Performance: {func.__name__} failed after {execution_time:.3f}s: {e}",
                extra={'execution_time': execution_time, 'function': func.__name__, 'error': str(e)}
            )
            raise
    
    return wrapper


async def batch_file_operations(operations: list[Callable]) -> list[Any]:
    """Execute multiple file operations concurrently."""
    executor = get_io_executor()
    loop = asyncio.get_event_loop()
    
    tasks = [
        loop.run_in_executor(executor, op)
        for op in operations
    ]
    
    return await asyncio.gather(*tasks, return_exceptions=True)


def clear_all_caches() -> None:
    """Clear all performance caches."""
    _file_cache.clear()
    _ai_cache.clear()
    logger.info("All performance caches cleared")


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about cache usage."""
    return {
        'file_cache': {
            'size': len(_file_cache._cache),
            'max_size': _file_cache.max_size,
            'ttl_seconds': _file_cache.ttl_seconds
        },
        'ai_cache': {
            'size': len(_ai_cache._cache),
            'max_size': _ai_cache.max_size,
            'ttl_seconds': _ai_cache.ttl_seconds
        }
    }