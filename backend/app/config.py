from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "hausmanager"
    secret_key: str = "change_me_use_a_strong_random_secret_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours

    class Config:
        env_file = ".env"


settings = Settings()
settings = Settings()
