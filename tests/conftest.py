import os

os.environ.setdefault("NERON_API_KEY", "test-api-key")
os.environ["NERON_SANDBOX_BACKEND"] = "python"
os.environ["NERON_SANDBOX_SYSTEMD_USE_SUDO"] = "false"
os.environ.setdefault("NERON_TASK_WORKER_ENABLED", "false")
