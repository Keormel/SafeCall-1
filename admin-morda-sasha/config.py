from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    admin_jwt_secret: str
    admin_jwt_algorithm: str = "HS256"
    admin_access_token_expire_minutes: int = 60

    mock_mode: bool = True

    main_api_base_url: str = "http://127.0.0.1:9000"
    main_api_token: str = "change-me"

    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
