from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_TELEGRAM_ID: int | None = None


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings() # type: ignore
print(settings)