# settings.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    AZURE_SPEECH_KEY: str = "your-speech-key"
    AZURE_SERVICE_REGION: str = "your-region"
    GEMINI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
