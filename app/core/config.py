from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    OLLAMA_URL: str
    OLLAMA_MODEL: str

    class Config:
        env_file = ".env"


settings = Settings()