import os
import pytest
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("IOT_API_KEY", "ci-test-key-123")
os.environ.setdefault("MOBILE_WS_TOKEN", "ci-ws-token-456")
os.environ.setdefault("ENROLLMENT_TOKEN", "ci-enroll-token-789")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
def crypto_keypair():
    sk = ec.generate_private_key(ec.SECP256R1())
    pk = sk.public_key()
    pk_hex = pk.public_bytes(encoding=Encoding.DER, format=PublicFormat.SubjectPublicKeyInfo).hex()
    return {"sk": sk, "pk": pk, "pk_hex": pk_hex}


@pytest.fixture
def signer(crypto_keypair):
    def sign(message: str) -> str:
        sig = crypto_keypair["sk"].sign(message.encode(), ec.ECDSA(hashes.SHA256()))
        return sig.hex()
    return sign


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_redis():
    with patch("src.worker.redis_sync") as mock:
        mock.brpop.return_value = (None, None)
        mock.set.return_value = True
        mock.setex.return_value = True
        mock.publish.return_value = 1
        mock.lpush.return_value = 1
        yield mock
