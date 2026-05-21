import os

import uvicorn

from simulated_factory.api import create_app


CONFIG_PATH = os.getenv("SIMULATOR_CONFIG_PATH", "presets.yml")
app = create_app(CONFIG_PATH)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("SIMULATOR_BIND", "0.0.0.0"),
        port=int(os.getenv("SIMULATOR_PORT", "8400")),
        reload=False,
    )