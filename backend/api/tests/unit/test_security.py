import time
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from src.security import verify_device_signature, verify_api_key, validate_iot_payload
from src.schemas import MisurationCreate
from fastapi import HTTPException


class TestVerifyDeviceSignature:
    def test_valid_signature(self, crypto_keypair, signer):
        message = "1234:1700000000"
        sig_hex = signer(message)
        assert verify_device_signature(crypto_keypair["pk_hex"], message, sig_hex) is True

    def test_invalid_signature(self, crypto_keypair):
        message = "1234:1700000000"
        wrong_sig = "a" * 128
        assert verify_device_signature(crypto_keypair["pk_hex"], message, wrong_sig) is False

    def test_empty_public_key(self, signer):
        message = "1234:1700000000"
        sig_hex = signer(message)
        assert verify_device_signature("", message, sig_hex) is False

    def test_empty_signature(self, crypto_keypair):
        message = "1234:1700000000"
        assert verify_device_signature(crypto_keypair["pk_hex"], message, "") is False

    def test_tampered_message(self, crypto_keypair, signer):
        message = "1234:1700000000"
        sig_hex = signer(message)
        tampered = "1234:1700000001"
        assert verify_device_signature(crypto_keypair["pk_hex"], tampered, sig_hex) is False

    def test_wrong_key_signature(self, crypto_keypair):
        wrong_sk = ec.generate_private_key(ec.SECP256R1())
        message = "1234:1700000000"
        wrong_sig = wrong_sk.sign(message.encode(), ec.ECDSA(hashes.SHA256())).hex()
        assert verify_device_signature(crypto_keypair["pk_hex"], message, wrong_sig) is False


class TestVerifyApiKey:
    def test_valid_key(self):
        with patch("src.security.IOT_API_KEY", "test-key-123"):
            assert verify_api_key("test-key-123") == "test-key-123"

    def test_invalid_key(self):
        with patch("src.security.IOT_API_KEY", "test-key-123"):
            with pytest.raises(HTTPException) as exc:
                verify_api_key("wrong-key")
            assert exc.value.status_code == 401

    def test_missing_key(self):
        with patch("src.security.IOT_API_KEY", "test-key-123"):
            with pytest.raises(HTTPException) as exc:
                verify_api_key(None)
            assert exc.value.status_code == 401


class TestValidateIoTPayload:
    @pytest.mark.asyncio
    async def test_valid_payload(self, crypto_keypair, signer):
        ts = int(time.time())
        value = 450
        message = f"{value}:{ts}"
        sig_hex = signer(message)

        misuration = MisurationCreate(
            value=value,
            misurator_id=1,
            device_timestamp=ts,
            signature_hex=sig_hex,
        )

        mock_misurator = MagicMock()
        mock_misurator.id = 1
        mock_misurator.active = True
        mock_misurator.public_key_hex = crypto_keypair["pk_hex"]

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_misurator

        result = await validate_iot_payload(misuration, api_key="valid", db=mock_db)
        assert result["misurator"] == mock_misurator
        assert result["misuration"] == misuration

    @pytest.mark.asyncio
    async def test_inactive_sensor(self, crypto_keypair, signer):
        ts = int(time.time())
        value = 450
        message = f"{value}:{ts}"
        sig_hex = signer(message)

        misuration = MisurationCreate(
            value=value,
            misurator_id=1,
            device_timestamp=ts,
            signature_hex=sig_hex,
        )

        mock_misurator = MagicMock()
        mock_misurator.active = False

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_misurator

        with pytest.raises(HTTPException) as exc:
            await validate_iot_payload(misuration, api_key="valid", db=mock_db)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_replay_attack(self, crypto_keypair, signer):
        ts = int(time.time()) - 7200
        value = 450
        message = f"{value}:{ts}"
        sig_hex = signer(message)

        misuration = MisurationCreate(
            value=value,
            misurator_id=1,
            device_timestamp=ts,
            signature_hex=sig_hex,
        )

        mock_misurator = MagicMock()
        mock_misurator.id = 1
        mock_misurator.active = True
        mock_misurator.public_key_hex = crypto_keypair["pk_hex"]

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_misurator

        with pytest.raises(HTTPException) as exc:
            await validate_iot_payload(misuration, api_key="valid", db=mock_db)
        assert exc.value.status_code == 403
        assert "Replay" in exc.value.detail

    @pytest.mark.asyncio
    async def test_nonexistent_sensor(self):
        ts = int(time.time())
        misuration = MisurationCreate(
            value=450,
            misurator_id=999,
            device_timestamp=ts,
            signature_hex="a" * 128,
        )

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc:
            await validate_iot_payload(misuration, api_key="valid", db=mock_db)
        assert exc.value.status_code == 403
