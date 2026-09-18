import os


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-change-me",
    )

    DATABASE = os.environ.get(
        "DATABASE_PATH",
        "event_planner.db",
    )

    TESTING = False


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"