"""
Manages access methods to test data files
"""

from os.path import join as pjoin, abspath, dirname

DATA_DIR = pjoin(dirname(abspath(__file__)), 'data')
TLE_DIR = pjoin(dirname(abspath(__file__)), 'data')

LS5_SCENE1 = pjoin(DATA_DIR, 'LANDSAT5', 'LS5_TM_OTH_P51_GALPGS01-002_090_081_20090407')
LS7_SCENE1 = pjoin(DATA_DIR, 'LANDSAT7', 'LS7_ETM_OTH_P51_GALPGS01-002_090_081_20090415')
LS8_SCENE1 = pjoin(DATA_DIR, 'LANDSAT8', 'LS8_OLITIRS_OTH_P51_GALPGS01-032_090_084_20131011')
S2A_SCENE1 = pjoin(DATA_DIR, 'SENTINEL2', 'S2A_MSIL1C_20171207T002051_N0206_R116_T55JEJ_20171207T032513.zip')
S2B_SCENE1 = pjoin(DATA_DIR, 'SENTINEL2', 'S2B_MSIL1C_20170719T000219_N0205_R030_T56JKT_20170719T000218.zip')

LAND_SEA_RASTERS = pjoin(DATA_DIR, 'ancillary', 'Land_Sea_Rasters')
