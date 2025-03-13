#!/usr/bin/env bash

cwd="$(dirname "$(realpath "$0")")"

gdal_translate -ot Byte -co COMPRESS=LZW -co BIGTIFF=YES $cwd/input.tif $cwd/output.tif
gdal2tiles --xyz -r "bilinear" -s "EPSG:3857" -z "0-6" --processes=8 $cwd/output.tif $cwd/xyz-tiles