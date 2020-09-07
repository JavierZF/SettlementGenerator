from numpy import *
from operator import *
from pymclevel import alphaMaterials, MCSchematic, MCLevel, BoundingBox
from mcplatform import *

#Biomes dictionary

biomes = {
    "plains": [1, 129],
    "forest": [4, 18, 132],
    "birchForest": [27, 28, 155, 156],
    "darkForest": [29, 157],
    "swamp": [6, 134],
    "jungle": [21, 22, 23, 149, 151],
    "riverBeach": [7, 11, 16, 25],
    "taiga": [5, 19, 133, 30, 31, 158, 32, 33, 160, 161],
    "snowyIcy": [12, 140, 26],
    "mountains": [3, 13, 34, 131, 162, 20],
    "mushroom": [14, 15],
    "desert": [2, 17, 130],
    "savanna": [35, 36, 163, 164],
    "badlands": [37, 38, 39, 165, 166, 167],
    "aquatic": [0, 10, 24, 44, 45, 46, 47, 48, 49, 50]
}


#add-on execution. Allows use independent of the Settlement Generatos function to check the biome previous to the execution
#and know the artistic style to espect 
def perform(level, box, options):    
    
    print "Starting execution"
    print "Calculating surface"
    surface = Surface(box.minx, box.minz, box.maxx, box.maxz)
    print "Biomes: "
    biomeDict = getBiomeDict()
    print biomeDict
    #Stores in a list the instances of biome obtained from the chunks
    biomeList = []
    for x in range(surface.xStart, surface.xEnd):
        for z in range(surface.zStart, surface.zEnd):
            chunk = level.getChunk(x / 16, z / 16)
            chunkBiomeData = chunk.root_tag["Level"]["Biomes"].value
            biome = translateBiome(level, chunkBiomeData, biomeDict)
            biomeList.append(biome)
    #Prints the most common biome        
    print "Biome of terrain: " , moda(biomeList)  

#Main function. Similar procedure to perform
def getBiome(level, surface, sectionPoints):

    print "Biomes: "
    biomeDict = getBiomeDict()
    #Stores instances of biomes of each point on a list
    biomeList = []
    for point in sectionPoints:
        chunk = level.getChunk(point.x / 16, point.z / 16)
        chunkBiomeData = chunk.root_tag["Level"]["Biomes"].value
        biome = translateBiome(level, chunkBiomeData, biomeDict)
        biomeList.append(biome)
    #Returns most repeated biome
    print "Biome of terrain: " , moda(biomeList)  
    return  moda(biomeList)  

#Returns biome name based on value
def translateBiome(level, chunkBiomeData, biomeDict):

    terrain = moda(chunkBiomeData)
    return biomeDict[terrain]

#Returns biome Dictionary
def getBiomeDict():
    biomeDict = {}
    for key, value in biomes.items():
        for i in value:
            biomeDict[i] = key
    
    return biomeDict

#Returns most common value
def moda(array):
    uniques, counts = unique(array, return_counts=True)
    count = dict(zip(uniques, counts))
    moda = max(count.iteritems(), key=itemgetter(1))[0]
    return moda        
                                       
#Represents the selected terrain of the map
class Surface:

    def __init__(self, xStart, zStart, xEnd, zEnd):
        self.xStart = xStart
        self.zStart = zStart
        self.xEnd = xEnd
        self.zEnd = zEnd
        self.xLength = xEnd - xStart
        self.zLength = zEnd - zStart
        self.surfaceMap = self.getNewSurfaceMap()

	#Computes de bidimensional matrix that acts as a map
    def getNewSurfaceMap(self):
        surfaceMap = []
        for x in range(self.xLength):
            row = []
            for z in range(self.zLength):
                row.append(SurfacePoint())
            surfaceMap.append(row)
        return surfaceMap

	#Functions to obtain the real value of X and Z coordinates
    def toRealX(self, x):
        return self.xStart + x

    def toRealZ(self, z):
        return self.zStart + z


class SurfacePoint:

	def __init__(self):
		#Height of the highest block on the point
		self.height = 0
		#Height difference between the block and its neighbours
		self.steepness = 0
		#Shows wheter the point is filled with water
		self.isWater = False
		#Identifies witch section contains the point
		self.sectionId = -1
		#Layer the point is inside the section
		self.layer = -1
		#Says wheter there is a structure built on that point
		self.isOccupied = False
		#Shows wether the point has been checked on the section determination phase
		self.checked = False