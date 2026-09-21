import hashlib
import hmac
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from backend import auth


class PasswordTests(unittest.TestCase):
    def test_password_hash_is_salted_and_verifiable(self):
        first = auth.hash_password("Factory123")
        second = auth.hash_password("Factory123")
        self.assertNotEqual(first, second)
        self.assertNotIn("Factory123", first)
        self.assertTrue(auth.verify_password("Factory123", first))
        self.assertFalse(auth.verify_password("Wrong123", first))
        self.assertFalse(auth.verify_password("Factory123", "invalid"))

    def test_registration_validation(self):
        with self.assertRaises(ValidationError):
            auth.RegisterRequest(name="A", email="not-an-email", password="password")
        request = auth.RegisterRequest(name="  Factory   Manager ", email=" MANAGER@EXAMPLE.COM ", password="Factory123")
        self.assertEqual(request.name, "Factory Manager")
        self.assertEqual(request.email, "manager@example.com")


class TokenTests(unittest.TestCase):
    user = {"user_id": "user-1", "name": "Factory Manager", "email": "manager@example.com",
            "role": "user", "active": True, "token_version": 0}

    def test_valid_token_restores_user(self):
        with patch.object(auth, "_auth_secret", return_value=b"test-secret"), \
             patch.object(auth.users, "find_one", return_value=self.user) as find:
            token = auth.create_token(self.user)
            self.assertEqual(auth.authenticate_token(token), self.user)
        find.assert_called_once_with({"user_id": "user-1", "active": True})

    def test_tampered_expired_and_revoked_tokens_are_rejected(self):
        with patch.object(auth, "_auth_secret", return_value=b"test-secret"):
            token = auth.create_token(self.user)
            self.assertIsNone(auth.authenticate_token(token[:-1] + ("A" if token[-1] != "A" else "B")))

            header, payload, _ = token.split(".")
            claims = json.loads(auth._b64decode(payload))
            claims["exp"] = int(datetime.now(timezone.utc).timestamp()) - 1
            payload = auth._b64encode(json.dumps(claims, separators=(",", ":")).encode())
            signature = auth._b64encode(hmac.new(b"test-secret", f"{header}.{payload}".encode(), hashlib.sha256).digest())
            self.assertIsNone(auth.authenticate_token(f"{header}.{payload}.{signature}"))

            with patch.object(auth.users, "find_one", return_value={**self.user, "token_version": 1}):
                self.assertIsNone(auth.authenticate_token(token))


class EndpointTests(unittest.TestCase):
    def test_register_stores_only_a_password_hash(self):
        request = auth.RegisterRequest(name="Factory Manager", email="manager@example.com", password="Factory123")
        captured = {}
        fake_users = MagicMock()
        fake_users.insert_one.side_effect = lambda user: captured.update(user)
        with patch.object(auth, "users", fake_users), patch.object(auth, "create_token", return_value="token"):
            result = auth.register(request)
        self.assertEqual(result["user"]["email"], "manager@example.com")
        self.assertNotIn("password", captured)
        self.assertTrue(auth.verify_password("Factory123", captured["password_hash"]))

    def test_duplicate_registration_is_conflict(self):
        request = auth.RegisterRequest(name="Factory Manager", email="manager@example.com", password="Factory123")
        fake_users = MagicMock()
        fake_users.insert_one.side_effect = DuplicateKeyError("duplicate")
        with patch.object(auth, "users", fake_users), self.assertRaises(HTTPException) as error:
            auth.register(request)
        self.assertEqual(error.exception.status_code, 409)

    def test_login_and_logout_lifecycle(self):
        user = {"user_id": "user-1", "name": "Factory Manager", "email": "manager@example.com",
                "password_hash": auth.hash_password("Factory123"), "active": True, "token_version": 0}
        fake_users = MagicMock()
        fake_users.find_one.return_value = user
        with patch.object(auth, "users", fake_users), patch.object(auth, "create_token", return_value="token"):
            result = auth.login(auth.LoginRequest(email="MANAGER@example.com", password="Factory123"))
            self.assertEqual(result["access_token"], "token")
            auth.logout(SimpleNamespace(state=SimpleNamespace(user=user)))
        fake_users.update_one.assert_any_call(
            {"user_id": "user-1"},
            {"$inc": {"token_version": 1}, "$set": {"logged_out_at": unittest.mock.ANY}},
        )

    def test_invalid_login_has_generic_error(self):
        fake_users = MagicMock()
        fake_users.find_one.return_value = None
        with patch.object(auth, "users", fake_users), self.assertRaises(HTTPException) as error:
            auth.login(auth.LoginRequest(email="unknown@example.com", password="Wrong123"))
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.detail, "Email or password is incorrect.")


if __name__ == "__main__":
    unittest.main()
