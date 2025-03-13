#!/bin/bash

cwd=$(pwd)
gdal_translate -ot Byte -co COMPRESS=LZW -co BIGTIFF=YES input.tif output.tif
gdal2tiles ---xyz -r "bilinear" -s "EPSG:4326" -z "0-6" --processes=8 output.tif xyz-tiles