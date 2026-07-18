from hearsay_api.config import Settings


def test_settings_derive_database_url_from_existing_env_shape() -> None:
    settings = Settings(
        HEARSAY_PERSISTENCE_BACKEND="cockroachdb",
        command_to_connect=(
            "cockroach sql --url "
            "'postgresql://ash:placeholder@example.test:26257/defaultdb"
            "?sslmode=verify-full'"
        ),
        username="ash",
        password="real password",
    )

    assert settings.database_url is not None
    assert settings.database_url.get_secret_value() == (
        "postgresql://ash:real%20password@example.test:26257/hearsay?sslmode=verify-full"
    )
