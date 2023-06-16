#Importing necessary modules
import ee
import arcpy
import math

# Authentication from Google Earth Engine
ee.Initialize()


# Declaring the workspace
arcpy.env.workspace = r"C:\VUB\GIS_Programming\EXAM"

# Date range
init_date = '2022-06-01'
end_date = '2022-07-01'

# Load image collection from cloud and filter out based on the dates and bands
image = ee.ImageCollection('LANDSAT/LC08/C02/T1').filterDate(init_date, end_date).select(['B5', 'B6', 'B10'])

# Downloading the first image from the collection
First_image = image.first()
arcpy.CopyRaster_management(First_image, 'Landsat_8.tif')

# Calculate NDVI
Red_band = arcpy.Raster('Landsat_8.tif/B5')
NIR_band = arcpy.Raster('Landsat_8.tif/B6')

NDVI = arcpy.sa.Divide(arcpy.sa.Minus(NIR_band, Red_band), arcpy.sa.Plus(NIR_band, Red_band))
NDVI.save('NDVI.tif')

# Attach NDVI band to the composite Landsat Image
Merge_NDVI = arcpy.sa.CompositeBands([First_image, NDVI])
Merge_NDVI.save('Landsat_8_NDVI.tif')

#
# Part 1: Calculate the top of the atmosphere radiance
#

# Importing necessary data from metadata
Multi_factor = 0.0003342
Band_name = arcpy.Raster('Landsat_8_NDVI.tif/B10')
Additive_factor = 0.1

# Developing function to calculate atmosphere radiance
def atmosphere_radiance(Multi_factor, Band_name, Additive_factor):
    TOA_radiance = (Multi_factor * Band_name) + Additive_factor
    return TOA_radiance

# Running the function to calculate atmosphere radiance
TOA_radiance = atmosphere_radiance(Multi_factor, Band_name, Additive_factor)
TOA_radiance.save('TOA_radiance.tif')

#
# Part 2: TOA to brightness temperature conversion
#

Band_constant_K1 = 774.8853
Band_constant_K2 = 1321.0789

# Developing function to calculate BT
def calculate_BT(TOA_radiance, Band_constant_K1, Band_constant_K2):
    BT = (Band_constant_K2 / (math.log(Band_constant_K1 / TOA_radiance) + 1)) - 273.15
    return BT

# Running the function
BT = calculate_BT(TOA_radiance, Band_constant_K1, Band_constant_K2)
BT.save('BT.tif')

#
# Part 3: Calculate the proportion of vegetation
#
NDVI_min = arcpy.sa.ZonalStatistics(NDVI, "MINIMUM", "DATA")[0]
NDVI_max = arcpy.sa.ZonalStatistics(NDVI, "MAXIMUM", "DATA")[0]

# Developing function to calculate proportion of vegetation
def calculate_vegetation_proportion(NDVI, NDVI_min, NDVI_max):
    Pv = arcpy.sa.Power(arcpy.sa.Divide(arcpy.sa.Minus(NDVI, NDVI_min), arcpy.sa.Minus(NDVI_max, NDVI_min)), 2)
    return Pv

# Running the function
pv = calculate_vegetation_proportion(NDVI, NDVI_min, NDVI_max)
pv.save('vegetation_fraction.tif')

#
# Part 4: Calculate emissivity
#
def calculate_emissivity(input):
    emissivity = (0.004 * input) + 0.986
    return emissivity

emissivity = calculate_emissivity(BT)
emissivity.save('emissivity.tif')

#
# Part 5: Calculate the LST
#
def calculate_LST(BT, emissivity):
    LST = arcpy.sa.Divide(BT, arcpy.sa.Plus(1, arcpy.sa.Times(0.0015, arcpy.sa.Divide(BT, 1.4388)).Ln(), emissivity)))
    return LST

# Running the function
LST = calculate_LST(BT, emissivity)
LST.save('Landsat_8_raw_LST.tif')
