from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    password = "secret-password"
    password_hash = hash_password(password)
    assert password_hash != password
    assert verify_password(password, password_hash)


def test_access_and_refresh_tokens_are_distinct() -> None:
    access = create_access_token("user-1")
    refresh = create_refresh_token("user-1")
    assert access != refresh
