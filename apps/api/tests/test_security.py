from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("s3cret")
    assert h != "s3cret"
    assert verify_password("s3cret", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    token = create_access_token(subject="user-123")
    assert decode_access_token(token) == "user-123"


def test_jwt_invalid_token_returns_none():
    assert decode_access_token("not-a-jwt") is None
