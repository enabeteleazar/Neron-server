

find /etc/neron/core -type f -name "*.pyc" -delete
find /etc/neron/core -type d -name "__pycache__" -exec rm -rf {} +
