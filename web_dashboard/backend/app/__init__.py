from fastapi import FastAPI


def create_app() -> FastAPI:
    """
    Application factory for the Thermal Presence Dashboard backend.

    The actual FastAPI instance is created in main.py. This helper is here
    mainly to make testing and future extension easier.
    """
    from .main import app

    return app



