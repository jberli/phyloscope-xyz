import os

from fastapi import FastAPI, Response
from starlette.responses import FileResponse
import uvicorn

# Initiate the fastAPI application
app = FastAPI()

# Handle GET request
@app.get("/{layer}/{z}/{x}/{y}.png")
async def get_tile(layer:str, z: int, x: int, y: int, response: Response):
    response.headers["Content-Type"] = "image/png"
    tile_path = f"xyz/{layer}/{z}/{x}/{y}.png"

    if (os.path.exists(tile_path) is False):
        # Return None content if the tile does not exist
        return Response(content=None)
    else:
        # Return tile
        return FileResponse(tile_path)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)