# src/parallel/__init__.py
"""
Parallel scraping infrastructure for Iran Jobs Intelligence Platform.

This module provides thread-safe components for parallel job scraping:
- WorkerPool: Orchestrates multiple worker threads
- JobQueue: Thread-safe queue for job distribution
- ScrapeWorker: Individual worker thread logic
"""
from .worker_pool import WorkerPool
from .job_queue import JobQueue, JobItem, JobQueueStats
from .worker import ScrapeWorker

__all__ = [
    'WorkerPool',
    'JobQueue',
    'JobItem',
    'JobQueueStats',
    'ScrapeWorker',
]