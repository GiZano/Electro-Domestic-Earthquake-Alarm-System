import os
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("IOT_API_KEY", "ci-test-key-123")
os.environ.setdefault("MOBILE_WS_TOKEN", "ci-ws-token-456")
os.environ.setdefault("ENROLLMENT_TOKEN", "ci-enroll-token-789")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

_mock_wait = patch("src.main.wait_for_db").start()
_mock_create = patch("src.main.models.Base.metadata.create_all").start()
_mock_redis = patch("src.main.redis_client").start()
