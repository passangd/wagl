#!/usr/bin/env python

"""
Calculates the slope and aspect for a given elevation dataset.
"""

from __future__ import absolute_import, print_function
import numpy
import h5py

from wagl.data import as_array
from wagl.constants import DatasetName, GroupName
from wagl.margins import pixel_buffer
from wagl.satellite_solar_angles import setup_spheroid
from wagl.hdf5 import dataset_compression_kwargs
from wagl.hdf5 import attach_image_attributes
from wagl.__slope_aspect import slope_aspect


def _slope_aspect_arrays(acquisition, dsm_fname, buffer_distance, out_fname,
                         compression='lzf'):
    """
    A private wrapper for dealing with the internal custom workings of the
    NBAR workflow.
    """
    with h5py.File(dsm_fname, 'r') as dsm_fid,\
        h5py.File(out_fname, 'w') as fid:

        dsm_grp = dsm_fid[GroupName.elevation_group.value]
        slope_aspect_arrays(acquisition, dsm_grp, buffer_distance, fid,
                            compression)


def slope_aspect_arrays(acquisition, dsm_group, buffer_distance,
                        out_group=None, compression='lzf'):
    """
    Calculates slope and aspect.

    :param acquisition:
        An instance of an acquisition object.

    :param dsm_group:
        The root HDF5 `Group` that contains the Digital Surface Model
        data.
        The dataset pathname is given by:

        * DatasetName.dsm_smoothed

        The dataset must have the same dimensions as `acquisition`
        plus a margin of widths specified by margin.

    :param buffer_distance:
        A number representing the desired distance (in the same
        units as the acquisition) in which to calculate the extra
        number of pixels required to buffer an image.
        Default is 8000.

    :param out_group:
        If set to None (default) then the results will be returned
        as an in-memory hdf5 file, i.e. the `core` driver. Otherwise,
        a writeable HDF5 `Group` object.

        The dataset names will be given by the format string detailed
        by:

        * DatasetName.slope
        * DatasetName.aspect

    :param compression:
        The compression filter to use. Default is 'lzf'.
        Options include:

        * 'lzf' (Default)
        * 'lz4'
        * 'mafisc'
        * An integer [1-9] (Deflate/gzip)

    :return:
        An opened `h5py.File` object, that is either in-memory using the
        `core` driver, or on disk.
    """
    # Setup the geobox
    geobox = acquisition.gridded_geo_box()

    # Retrive the spheroid parameters
    # (used in calculating pixel size in metres per lat/lon)
    spheroid, _ = setup_spheroid(geobox.crs.ExportToWkt())

    # Are we in projected or geographic space
    is_utm = not geobox.crs.IsGeographic()

    # Define Top, Bottom, Left, Right pixel margins
    margins = pixel_buffer(acquisition, buffer_distance)

    # Get the x and y pixel sizes
    _, y_origin = geobox.origin
    x_res, y_res = geobox.pixelsize

    # Get acquisition dimensions and add 1 pixel top, bottom, left & right
    cols, rows = geobox.get_shape_xy()
    ncol = cols + 2
    nrow = rows + 2

    # TODO: check that the index is correct
    # Define the index to read the DEM subset
    ystart, ystop = (margins.top - 1, -(margins.bottom - 1))
    xstart, xstop = (margins.left - 1, -(margins.right - 1))
    idx = (slice(ystart, ystop), slice(xstart, xstop))

    # elevation dataset
    elevation = dsm_group[DatasetName.dsm_smoothed.value]
    subset = as_array(elevation[idx], dtype=numpy.float32, transpose=True)

    # Define an array of latitudes
    # This will be ignored if is_utm == True
    alat = numpy.array([y_origin - i * y_res for i in range(-1, nrow - 1)],
                       dtype=numpy.float64)  # yes, I did mean float64.

    # Output the reprojected result
    # Initialise the output files
    if out_group is None:
        fid = h5py.File('slope-aspect.h5', driver='core',
                        backing_store=False)
    else:
        fid = out_group

    if GroupName.slp_asp_group.value not in fid:
        fid.create_group(GroupName.slp_asp_group.value)

    group = fid[GroupName.slp_asp_group.value]

    # metadata for calculation
    param_group = group.create_group('PARAMETERS')
    param_group.attrs['dsm_index'] = ((ystart, ystop), (xstart, xstop))
    param_group.attrs['pixel_buffer'] = '1 pixel'

    kwargs = dataset_compression_kwargs(compression=compression,
                                        chunks=acquisition.tile_size)
    no_data = -999
    kwargs['fillvalue'] = no_data

    # Define the output arrays. These will be transposed upon input
    slope = numpy.zeros((rows, cols), dtype='float32')
    aspect = numpy.zeros((rows, cols), dtype='float32')

    slope_aspect(ncol, nrow, cols, rows, x_res, y_res, spheroid, alat, is_utm,
                 subset, slope.transpose(), aspect.transpose())

    # output datasets
    dname = DatasetName.slope.value
    slope_dset = group.create_dataset(dname, data=slope, **kwargs)
    dname = DatasetName.aspect.value
    aspect_dset = group.create_dataset(dname, data=aspect, **kwargs)

    # attach some attributes to the image datasets
    attrs = {'crs_wkt': geobox.crs.ExportToWkt(),
             'geotransform': geobox.transform.to_gdal(),
             'no_data_value': no_data}
    desc = "The slope derived from the input elevation model."
    attrs['description'] = desc
    attach_image_attributes(slope_dset, attrs)

    desc = "The aspect derived from the input elevation model."
    attrs['description'] = desc
    attach_image_attributes(aspect_dset, attrs)

    if out_group is None:
        return fid
