# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
FastAPI application for the SRE Copilot Environment.
"""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required. Install with: uv sync or pip install openenv-core"
    ) from e

try:
    from ..models import SreAction, SreObservation
except ImportError:
    from models import SreAction, SreObservation

from sre_copilot_env_environment import SreCopilotEnvironment

# Create the app
app = create_app(
    SreCopilotEnvironment,      # Your environment class
    SreAction,                  # Your Action model
    SreObservation,             # Your Observation model
    env_name="sre-copilot-env",
    max_concurrent_envs=1,
)


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run("server.app:app", host=host, port=port)


if __name__ == "__main__":
    main()