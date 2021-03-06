# -*- coding: utf-8 -*-

"""Console script for src."""
import sys
import os
import click
import numpy as np
from contextlib import contextmanager
import rasterio
from rasterio import Affine, MemoryFile
from rasterio.enums import Resampling


def resampler(sourcefile, target_resolution, yes=False):

    click.echo(
        "This package will resample a GEOTIFF Raster file to a different resolution.")

    # read source file and collect metadata for display.
    dat = rasterio.open(sourcefile)
    targetfile = os.path.basename(sourcefile).split('.')[0] \
                + '_resampled_' \
                + str(target_resolution).replace(".", "_") \
                + str(dat.crs.linear_units) \
                + '.tif'

    # set projection to the source projection unless user specified otherwise.

    click.echo("Application Settings:\n")
    click.echo(f"source filename: {sourcefile}")
    click.echo(f"target filename: {targetfile}")
    click.echo(
        f"source file pixel resolution: {(round(dat.res[0], 3), round(dat.res[1], 3))} in {dat.crs.linear_units} units.")
    click.echo(
        f"target resolution: {target_resolution} in {dat.crs.linear_units} units.")

    # TODO assume file is a legitimate Geotiff file.

    click.echo(f'File Analysis:\n')
    click.echo(f"original file EPSG projection: {dat.crs}")
    click.echo(f'target EPSG projection: {dat.crs}\n')
    # click.echo(f"file transform: {dat.transform}")

    # Calculate scaling factor for resampling.

    scaling_factor = target_resolution / dat.res[0]

    click.echo(f'[INFO] computed pixel scaling factor: {round(scaling_factor, 3)}\n')
    dat.close()

    if not yes:
        click.confirm('File resampling takes a while.\nDo you want to continue?',
                 abort=True)

        click.echo('[INFO] Good time to get a cup of coffee.\n')

    with rasterio.open(sourcefile) as src:
        with resample_raster(src, out_path=targetfile, scale=scaling_factor) as resampled:
            click.echo('[INFO] Process complete.\n')
            click.echo(f'original image dimensions: {src.shape}')
            click.echo(f'new image dimensions: {resampled.shape}')
            click.echo(f'new image EPSG projection: {resampled.crs}')

    return targetfile

@contextmanager
def resample_raster(raster, out_path=None, scale=1):
    """ Resample a raster
        multiply the pixel size by the scale factor
        divide the dimensions by the scale factor
        i.e
        given a pixel size of 250m, dimensions of (1024, 1024) and a scale of 2,
        the resampled raster would have an output pixel size of 500m and dimensions of (512, 512)
        given a pixel size of 250m, dimensions of (1024, 1024) and a scale of 0.5,
        the resampled raster would have an output pixel size of 125m and dimensions of (2048, 2048)
        returns a DatasetReader instance from either a filesystem raster or MemoryFile (if out_path is None)

        Attribution: This code was adapted from XXX
    """
    t = raster.transform

    # rescale the metadata
    transform = Affine(t.a * scale, t.b, t.c, t.d, t.e * scale, t.f)
    height = int(raster.height / scale)
    width = int(raster.width / scale)

    profile = raster.profile
    profile.update(transform=transform, driver='GTiff', height=height,
                   width=width)

    data = raster.read(
        out_shape=(raster.count, height, width),
        resampling=Resampling.cubic)

    if out_path is None:
        with write_mem_raster(data, **profile) as dataset:
            del data
            yield dataset

    else:
        with write_raster(out_path, data, **profile) as dataset:
            del data
            yield dataset


@contextmanager
def write_mem_raster(data, **profile):
    """
    Attribution: This code was taken from XXX
    :param data:
    :type data:
    :param profile:
    :type profile:
    :return:
    :rtype:
    """
    with MemoryFile() as memfile:
        with memfile.open(**profile) as dataset:  # Open as DatasetWriter
            dataset.write(data)

        with memfile.open() as dataset:  # Reopen as DatasetReader
            yield dataset  # Note yield not return


@contextmanager
def write_raster(path, data, **profile):
    """
    Attribution: This code was taken from
    :param path:
    :type path:
    :param data:
    :type data:
    :param profile:
    :type profile:
    :return:
    :rtype:
    """
    with rasterio.open(path, 'w',
                       **profile) as dataset:  # Open as DatasetWriter
        dataset.write(data)

    with rasterio.open(path) as dataset:  # Reopen as DatasetReader
        yield dataset

