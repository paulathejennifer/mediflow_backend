"""
Gunicorn configuration for MediFlow Backend.

Uses Uvicorn workers for async support with Gunicorn's
process management for production stability.
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Worker processes
workers = int(os.getenv("WEB_CONCURRENCY", min(multiprocessing.cpu_count() + 1, 3)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_tmp_dir = "/dev/shm"

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# Process naming
proc_name = "mediflow-backend"

# Server mechanics
preload_app = False
max_requests = 1000
max_requests_jitter = 50
