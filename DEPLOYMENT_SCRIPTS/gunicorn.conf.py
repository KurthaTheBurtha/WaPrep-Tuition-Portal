# WaPrep Tuition Portal - Gunicorn Configuration
# Optimized for production deployment with security and performance settings

import multiprocessing
import os

# Server Socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = "waprep-tuition"

# Server Mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
worker_tmp_dir = "/dev/shm"
worker_exit_on_app_exit = False

# Environment Variables
raw_env = [
    "DJANGO_SETTINGS_MODULE=tuition.settings_production",
]

# Callbacks
def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker aborted (pid: %s)", worker.pid)

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def on_starting(server):
    server.log.info("Starting gunicorn server")

def on_reload(server):
    server.log.info("Reloading gunicorn server")

def on_exit(server):
    server.log.info("Exiting gunicorn server")

# Custom configuration based on environment
if os.environ.get('ENVIRONMENT') == 'production':
    # Production settings
    workers = multiprocessing.cpu_count() * 2 + 1
    worker_class = "sync"
    max_requests = 1000
    timeout = 30
    loglevel = "info"
    
elif os.environ.get('ENVIRONMENT') == 'staging':
    # Staging settings
    workers = multiprocessing.cpu_count() + 1
    worker_class = "sync"
    max_requests = 500
    timeout = 60
    loglevel = "debug"
    
else:
    # Development settings
    workers = 1
    worker_class = "sync"
    max_requests = 0  # Disable max requests for development
    timeout = 120
    loglevel = "debug"
    reload = True
