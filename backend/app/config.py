from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "hausmanager"
    secret_key: str = "change_me"

    class Config:
        env_file = ".env"


settings = Settings()
