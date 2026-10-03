"""Owner tools API: port 8081, role `cac_owner` (SCHEMA 8.6, OWNERSHIP seam 5)."""

from fastapi import FastAPI

from app.infra.common_shim import Settings, get_settings
from app.routes import health, owner_only, reads


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="CAC Owner tools API",
        version="0.1.0",
        description="The write side of the CAC graph. The agent uses OWNER_TOOLS_TOKEN; the "
                    "owner's inbox uses OWNER_INBOX_TOKEN. Every write is a change record.",
    )
    app.state.settings = settings or get_settings()
    app.include_router(health.router)
    app.include_router(owner_only.router)
    app.include_router(reads.router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8081)


if __name__ == "__main__":
    run()
