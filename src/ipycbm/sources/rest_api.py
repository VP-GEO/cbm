#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file is part of CbM (https://github.com/ec-jrc/cbm).
# Author    : Guido Lemoine, Konstantinos Anastasakis
# Credits   : GTCAP Team
# Copyright : 2021 European Commission, Joint Research Centre
# License   : 3-Clause BSD


from src.ipycbm.utils import config
import requests


def ploc(area, year, lon, lat, geom=False):
    if area == 'es_ns':
        parcels = f'es{year}_nour_subset'
    else:
        parcels = f'{area}{year}'

    api_url, api_user, api_pass = config.credentials('api')
    requrl = """{}/query/parcelByLocation?parcels={}&lon={}&lat={}"""
    if geom is True:
        requrl = f"{requrl}&withGeometry=True"

    response = requests.get(requrl.format(api_url, parcels, lon, lat),
                            auth=(api_user, api_pass))
    return response.content


def pid(area, year, pid, geom=False):
    if area == 'es_ns':
        parcels = f'es{year}_nour_subset'
    else:
        parcels = f'{area}{year}'

    api_url, api_user, api_pass = config.credentials('api')
    requrl = """{}/query/parcelById?parcels={}&parcelid={}"""
    if geom is True:
        requrl = f"{requrl}&withGeometry=True"

    response = requests.get(requrl.format(api_url, parcels, pid),
                            auth=(api_user, api_pass))
    return response.content


def ppoly(area, year, polygon, geom=False, only_ids=True):
    if area == 'es_ns':
        parcels = f'es{year}_nour_subset'
    else:
        parcels = f'{area}{year}'

    api_url, api_user, api_pass = config.credentials('api')
    requrl = """{}/query/parcelsByPolygon?parcels={}&polygon={}"""
    if geom is True:
        requrl = f"{requrl}&withGeometry=True"
    if only_ids is True:
        requrl = f"{requrl}&only_ids=True"
    response = requests.get(requrl.format(api_url, parcels, polygon),
                            auth=(api_user, api_pass))
    return response.content


def pts(area, year, pid, tstype, band=''):
    if area == 'es_ns':
        area = f'es'

    api_url, api_user, api_pass = config.credentials('api')
    requrl = """{}/query/parcelTimeSeries?aoi={}&year={}&pid={}&tstype={}&band={}"""

    response = requests.get(requrl.format(api_url, area, year,
                                          pid, tstype, band),
                            auth=(api_user, api_pass))
    return response.content


def cbl(lon, lat, start_date, end_date, bands=None, lut=None, chipsize=None):
    api_url, api_user, api_pass = config.credentials('api')
    requrl = """{}/query/chipsByLocation?lon={}&lat={}&start_date={}&end_date={}"""
    band = '_'.join(bands)
    if band is not None:
        requrl = f"{requrl}&band={band}"
    if chipsize is not None:
        requrl = f"{requrl}&chipsize={chipsize}"
    if lut != '':
        requrl = f"{requrl}&lut={lut}"
    # print(requrl.format(api_url, lon, lat, start_date, end_date))
    response = requests.get(requrl.format(api_url, lon, lat,
                                          start_date, end_date),
                            auth=(api_user, api_pass))
    return response


def rcbl(parcel, start_date, end_date, bands, sat, chipsize, filespath):
    import os
    import pandas as pd
    from osgeo import osr, ogr
    import time
    start = time.time()
    api_url, api_user, api_pass = config.credentials('api')

    for band in bands:
        requrl = """{}/query/rawChipByLocation?lon={}&lat={}&start_date={}&end_date={}"""
        if band is not None:
            #         band = '_'.join(band)
            #         band = band.replace(' ', '')
            requrl = f"{requrl}&band={band}"
        if chipsize is not None:
            requrl = f"{requrl}&chipsize={chipsize}"

        # Create a valid geometry from the returned JSON withGeometry
        geom = ogr.CreateGeometryFromJson(parcel.get('geom')[0])
        source = osr.SpatialReference()
        source.ImportFromEPSG(parcel.get('srid')[0])

        # Assign this projection to the geometry
        geom.AssignSpatialReference(source)
        target = osr.SpatialReference()
        target.ImportFromEPSG(4326)
        transform = osr.CoordinateTransformation(source, target)

        # And get the lon, lat for its centroid, so that we can center the chips on
        # the parcel
        centroid = geom.Centroid()
        centroid.Transform(transform)

        # Use pid for next request
        pid = parcel['ogc_fid'][0]
        # cropname = parcel['cropname'][0]

        # Set up the rawChip request
        cen_x, cen_y = str(centroid.GetX()), str(centroid.GetY())

        response = requests.get(requrl.format(api_url, cen_y, cen_x, start_date,
                                              end_date, band, chipsize),
                                auth=(api_user, api_pass))

        # Directly create a pandas DataFrame from the json response
        df = pd.read_json(response.content)
        os.makedirs(os.path.dirname(filespath), exist_ok=True)
        df_file = f'{filespath}{pid}_images_list.{band}.csv'
        df.to_csv(df_file, index=True, header=True)
        # print(f"The response table is saved to: {df_file}")

        # Download the GeoTIFFs that were just created in the user cache
        for c in df.chips:
            url = f"{api_url}{c}"
            res = requests.get(url, stream=True)
            outf = f"{filespath}{c.split('/')[-1]}"
            # print(f"Downloading {c.split('/')[-1]}")
            with open(outf, "wb") as handle:
                for chunk in res.iter_content(chunk_size=512):
                    if chunk:  # filter out keep-alive new chunks
                        handle.write(chunk)
        print(f"Images for band '{band}', for the selected dates are downloaded.")

        # if len(df.index) != 0:
        #     print(f"All GeoTIFFs for band '{band}' are ",
        #           f"downloaded in the folder: '{filespath}'")
    print("\n------Total time------")
    print(f"Total time required for {len(bands)} bands: {time.time() - start} seconds.")


def clouds(geom):
    import glob
    import json
    import rasterio
    from osgeo import osr
    from rasterstats import zonal_stats
    # Check whether our parcel is cloud free

    # We should have a list of GeoTIFFs ending with .SCL.tif
    tiflist = glob.glob('*.SCL.tif')

    for t in tiflist:
        with rasterio.open(t) as src:
            affine = src.transform
            CRS = src.crs
            data = src.read(1)

        # Reproject the parcel geometry in the image crs
        imageCRS = int(str(CRS).split(':')[-1])

        # Cross check with the projection of the geometry
        # This needs to be done for each image, because the parcel could be in
        # a straddle between (UTM) zones
        geomCRS = int(geom.GetSpatialReference().GetAuthorityCode(None))

        if geomCRS != imageCRS:
            target = osr.SpatialReference()
            target.ImportFromEPSG(imageCRS)
            source = osr.SpatialReference()
            source.ImportFromEPSG(geomCRS)
            transform = osr.CoordinateTransformation(source, target)
            geom.Transform(transform)

        # Format as a feature collection (with only 1 feature)
        # and extract the histogram
        features = {"type": "FeatureCollection",
                    "features": [{"type": "feature",
                                  "geometry": json.loads(geom.ExportToJson()),
                                  "properties": {"pid": pid}}]}
        zs = zonal_stats(features, data, affine=affine, prefix="",
                         nodata=0, categorical=True, geojson_out=True)

        # This has only one record
        properties = zs[0].get('properties')

        # pid was used as a dummy key to make sure the histogram
        # values are in 'properties'
        del properties['pid']

        histogram = {int(float(k)): v for k, v in properties.items()}
        # print(t, histogram)
