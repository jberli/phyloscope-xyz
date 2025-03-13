import io
import os

import numpy as np
from fastapi import FastAPI, Response
from starlette.responses import FileResponse
from shapely.geometry import Polygon
import xarray as xr
import rioxarray as riox
import rasterio as rio
from PIL import Image
import uvicorn

# Initiate the fastAPI application
app = FastAPI()

# Load the raster file and reproject it
ds = xr.open_dataset('data/ne.nc', decode_coords="all")
ds = ds.rio.reproject('EPSG:3857')
# ds = ds.band_data
ds = ds.astype(np.int32)

height, width = ds.values[0].shape
ds = ds.rio.write_nodata(-9999, inplace=True)

min_value = int(ds.min())
max_value = int(ds.max())

bounds = (-20037508.342789244, -20037508.342789244, 20037508.342789244, 20037508.342789244)
margin = 0

def ST_TileEnvelope(z, x, y, bounds, margin=0):
    """
    Calculate the extent of the tiles.
    """
    worldTileSize = 2 ** min(z, 31)
 
    # Extract bounding box coordinates
    xmin, ymin, xmax, ymax = bounds
 
    # Calculate width and height of the bounding box
    boundsWidth = xmax - xmin
    boundsHeight = ymax - ymin
 
    if boundsWidth <= 0 or boundsHeight <= 0:
        raise ValueError("Geometric bounds are too small")
 
    if z < 0 or z >= 32:
        raise ValueError("Invalid tile zoom value")
 
    if x < 0 or x >= worldTileSize:
        raise ValueError("Invalid tile x value")
 
    if y < 0 or y >= worldTileSize:
        raise ValueError("Invalid tile y value")
 
    # Calculate tile geographic size
    tileGeoSizeX = boundsWidth / worldTileSize
    tileGeoSizeY = boundsHeight / worldTileSize
 
    # Calculate margins
    if margin < -0.5:
        raise ValueError("Margin must not be less than -50%")
    margin = max(-0.5, margin)
    margin = min(0.5, margin)
 
    # Calculate tile bounds
    x1 = xmin + tileGeoSizeX * (x - margin)
    x2 = xmin + tileGeoSizeX * (x + 1 + margin)
    y1 = ymax - tileGeoSizeY * (y + 1 + margin)
    y2 = ymax - tileGeoSizeY * (y - margin)
 
    # Clip y-axis to the given bounds
    y1 = max(y1, ymin)
    y2 = min(y2, ymax)
 
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]

def normalize_array(arr, min_value, max_value):
    return ((arr - min_value) / (max_value - min_value) * 255)

def convert_black_to_transparent(image):
    """
    Convert black pixels to transparent in a Pillow image.
    """
    img_array = np.array(image)

    # Identify black pixels
    black_pixels = (img_array[:, :, 0] == 0) & (
        img_array[:, :, 1] == 0) & (img_array[:, :, 2] == 0)

    # Set alpha channel to 0 for black pixels
    img_array[black_pixels, 3] = 0

    # Create new image with transparency
    transparent_image = Image.fromarray(img_array)

    return transparent_image

def generate_tile(zoom, x, y, bounds, margin, min_value, max_value):
    tile_envelope = ST_TileEnvelope(zoom, x, y, bounds, margin)

    xmin, ymin = tile_envelope[0]
    xmax, ymax = tile_envelope[2]

    try:
        data = ds.rio.clip_box(minx=xmin, miny=ymin, maxx=xmax, maxy=ymax, auto_expand=True)
        data = data.rio.reproject(data.rio.crs, shape=(256, 256))
        data = data.rio.pad_box(xmin, ymin, xmax, ymax, 0)
    except riox.exceptions.NoDataInBounds:
        # Return empty tile if no data found in bounds
        return None

    print(data.values[0])
    arr = normalize_array(data.values[0], min_value, max_value)
    print(arr)
    arr = arr.astype(np.int32)
    img = Image.fromarray(arr)

    # img = img.resize((256, 256))
    img = img.convert('RGBA')    

    img = convert_black_to_transparent(img)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    return img_bytes.getvalue()

@app.get("/{layer}/{z}/{x}/{y}.png")
async def get_tile(layer:str, z: int, x: int, y: int, response: Response):
    response.headers["Content-Type"] = "image/png"

    tile_path = f"xyz/{layer}/{z}/{x}/{y}.png"

    if (os.path.exists(tile_path) is False):
        # Render tile if not available in cache, then store in cache directory
        os.makedirs(f"xyz/{layer}/{z}/{x}", exist_ok=True)
        with open(tile_path, "wb") as tile:
            # Generate tile
            tile_data = generate_tile(z, x, y, bounds, margin, min_value, max_value)
            if tile_data is not None:
                tile.write(tile_data)
            return Response(content=tile_data)
    else:
        # Return tile from cache
        return FileResponse(tile_path)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)