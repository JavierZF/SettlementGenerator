import time # for timing
import heapq
from math import sqrt, tan, sin, cos, pi, ceil, floor, acos, atan, asin, degrees, radians, log, atan2, acos, asin
from random import *
from operator import itemgetter
from numpy import *
from pymclevel import alphaMaterials, MCSchematic, MCLevel, BoundingBox, TAG_Byte, TAG_Short, TAG_Int, TAG_Compound, TAG_List, TAG_String, TAG_Double, TAG_Float
from mcplatform import *
from collections import deque
from BiomeFinder import getBiome 


#add-on execution
def perform(level, box, options):		
	#Starts a timer to measure execution time
	startTime = time.time()
	#Informs user of selected map size
	print "Map of size :", box.maxx - box.minx, box.maxz - box.minz
	print "Starting execution"
	print "Calculating surface"
	#Creates a surface with the selection dimensions
	surface = Surface(box.minx, box.minz, box.maxx, box.maxz)
	print "Removing trees and bushes"
	#Measures height and deletes trees on the selection
	calculateHeightMap(level, surface)
	#Measures steepness for each block
	calculateSteepnessMap(level, surface)
	#Determines points filled with water
	calculateWaterBlocks(level,surface)
	#Creates a copy of the set of points of the map
	uncheckedPoints = calculateUncheckedPoints(level, surface)
	print "Map deforested", time.time() - startTime, " Seconds"
	#ID variable to identify sections
	ID = 0
	#Container of sections
	Sections = []
	print "Determinig sections"
	#While there is points unchecked
	while(uncheckedPoints):
		#Computes new section
		newSection = calculateSection(level,surface, 1, ID)
		#If an error is returned, nothing is done
		if calculateSection == -1:
			continue
		#If the section is not too small it is stored and the ID variable increased	
		if newSection.size > 60:
			ID += 1
			Sections.append(newSection)
		#Updates the list of points to check	
		uncheckedPoints = calculateUncheckedPoints(level, surface)   
	print "Sections determined at ", time.time() - startTime, " Seconds from the start" 
	print "Completing sections"
	#Completes the information each section lacks one by one
	for section in Sections:
		print "Section: ", section.id
		print "Size: ", section.size
		print "Removing Snow"
		#Removes ice and snow on the sections
		sectionDefrost(level, section, surface)
		print "Computing Average Height"
		#Camputes the average height
		calculateAverageSectionHeight(level, surface, section)
		print "Section Height: ", section.averageHeight
		#Obtains the center of the section
		calculateSectionMid(level, surface, section)
		print "Getting biome and changing materials"
	#Classifing sections
	print "Clasificando las secciones"	
	bigSections = []
	mediumSections = []
	smallSections = []
	#Stores sections by size on their respective list
	sectionClassifier(Sections, bigSections,  mediumSections, smallSections)	
	print bigSections,  mediumSections, smallSections
	#Starts building on big sections
	for section in bigSections:
		print "Building on big section: ", section.id
		print "Building Houses"	
		#Gets the biome and materials of the section
		getBiomeMaterials(level, surface, section)
		#Creates the buildings and returns the number of successfully built houses
		bigHouses = buildBigSectionCityCell(level, surface, section, surface.surfaceMap[section.xMid][section.zMid].height)	
		if bigHouses > 0:
			#Builds a fountain if there is at least one house
			buildLandmark(level, surface, section.xMid, section.zMid, surface.surfaceMap[section.xMid][section.zMid].height, "fountain", section.materials.water)
		elif checkZ(surface, section, section.xMid, section.zMid, 17, 17):
			#Builds a Hall with flat roof to differentiate it if the checking allows it
			buildHall(level, surface, section.xMid, section.zMid, getRandomDirection(), surface.surfaceMap[section.xMid][section.zMid].height, section.materials, True)

	print "On small sections:"	
	#Starts building on small sections
	for section in smallSections:
		#Gets the biome and materials of the section
		getBiomeMaterials(level, surface, section)
		#Builds a hut on the section if posible
		buildSmallSection(level, surface, section)

	print "On medium sections:"
	#Starts building on medium sections
	for section in mediumSections:
		print "Building on section: ", section.id
		#Gets the biome and materials of the section
		getBiomeMaterials(level, surface, section)
		#Builds four houses if posible
		houses = buildMediumSection(level, surface, section)
		#If it is posible to vuild on the center, it builds a corral, farm or fountain depending on the number of houses built
		if checkZ(surface, section, section.xMid, section.zMid, 5, 5):
			if houses == 0:
				buildCorral(level, surface, section, section.xMid, section.zMid, section.materials.animal, section.materials.fences)
			elif houses < 3 and houses > 0:
				buildLandmark(level, surface, section.xMid, section.zMid, surface.surfaceMap[section.xMid][section.zMid].height, "farm", section.materials.crops)
			else:	
				buildLandmark(level, surface, section.xMid, section.zMid, surface.surfaceMap[section.xMid][section.zMid].height, "fountain", section.materials.water)

	print "Obteniendo caminos entre ciudades"
	#Stores a list with the yet to be conencted sections
	unconectedSections = Sections
	for section in Sections:
		#If there is at least one section on the unconnected sections list, it connects to the nearest one of that list
		if len(unconectedSections) >= 1:
			section2 = getNearest(unconectedSections, section)
		#Else, it connects it to the nearest on the full list	
		else:
			section2 = getNearest(Sections, section)	
		path = getAStarPath(surface, section.xMid, section.zMid, section2.xMid, section2.zMid)
		if path:
			unconectedSections.remove(section)
			buildPath(level, surface, path)	
			
	print "Updating map values"
	calculateSteepnessMap(level, surface)

	
	print "Settlement Generated in ", time.time() - startTime, " Seconds"


#Clases
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

#Represents groups of adjacent blocks with similar height and where it is posible to built structures
class Section:

	def __init__(self, id):
		self.id = id
		self.points = []
		self.size = 0
		#Maximum layer depth. Helps with determining sections with weird areas where building is imposible 
		self.layerDepth = 0
		self.averageHeight = 0
		self.xMid = 0
		self.zMid = 0
		#List of materials to use on the section
		self.materials = Materials()

#Represents a point
class Point:

	def __init__(self, x, z):
		self.x = x
		self.z = z

#List of materials of a section
class Materials:
	#Default values
	def __init__(self):
		#Wood
		self.materialRoof = (17,0)
		#Wood
		self.materialFoundation = (17,0)
		#Double stone slab
		self.materialWall = (43,0)
		#Water
		self.water = (9,0)
		#Wheat
		self.crops = (59,0)
		#Grass
		self.garden = (2,0)
		#Double Stone Slab
		self.ground = (43,0)
		#Birch fences
		self.fences = (85,0)
		self.animal = "chicken"

#Used to identify centers of sections. Similar to surfaces but with layer identifiers on its points instead of positions
class SubSurface:

	def __init__(self, xStart, zStart, xEnd, zEnd):
		self.xStart = xStart
		self.zStart = zStart
		self.xEnd = xEnd
		self.zEnd = zEnd
		self.xLength = xEnd - xStart
		self.zLength = zEnd - zStart
		self.surfaceMap = self.getNewSurfaceMap()
	
	def getNewSurfaceMap(self):
		surfaceMap = []
		for _ in range(self.xLength):
			row = []
			for _ in range(self.zLength):
				row.append(PointInfo())
			surfaceMap.append(row)
		return surfaceMap

#Points of subSurface class
class PointInfo:

	def __init__(self):
		self.layer = -2 # -2 for unchecked, -1 for out of section bounds, n > 0 for layers of section
		self.checked = False
		self.isCheckedByLayer = -1 

#Represents a block
class Block:

	def __init__(self, x, y, z):
		self.x = x
		self.y = y
		self.z = z

#Nodes for A* search
class Node:

  def __init__(self, surface, x, z, targetNode):
    self.x = x
    self.y = surface.surfaceMap[x][z].height
    self.z = z
    self.gScore = sys.maxint
    self.fScore = sys.maxint
    self.cameFrom = None
    self.isOpen = False
    self.isClosed = False
    if targetNode == None:
      self.hScore = 0
    else:
      self.hScore = getSimpleHeuristicCostEstimate(surface, self, targetNode)
  
  def __eq__(self, node):
    if not node:
      return False
    return self.x == node.x and self.z == node.z

#Map completion functions

#List of ground blocks
aboveSurfaceBlocks = [0, 6, 17, 18, 31, 32, 37, 38, 39, 40, 59, 78, 81, 83, 99, 100, 103, 104, 105, 106, 111, 141, 142, 161, 162, 175]

#Obtains height of each point and stores it on the surface map while deleting tree blocks
def calculateHeightMap(level, surface):
	for x in range(surface.xLength):
		for z in range(surface.zLength):
			height = calculateSurfaceHeight(level, surface, x + surface.xStart, z + surface.zStart,True)
			surface.surfaceMap[x][z].height = height

#Updates the height of every point without deleting tree blocks (Doesnt remove roofs and vegetal materials)
def updateHeightMap(level, surface):
	for x in range(surface.xLength):
		for z in range(surface.zLength):
			height = calculateSurfaceHeight(level, surface, x + surface.xStart, z + surface.zStart, False)
			surface.surfaceMap[x][z].height = height

#Obtains height of a point while deleting trees
def calculateSurfaceHeight(level, surface, x, z, removeTrees):
	#Sets height to maximum value
	y = 128
	surfaceFound = False
	#While not on the surface, go down a block and modify y.
	while (y > 0 and not surfaceFound):
		for block in aboveSurfaceBlocks:
			if (level.blockAt(x, y, z) != 0):
				#If the block is of tree type and removeTrees is on, delete tree blocks
				if isTreeBlock(level, x, y, z):
					if removeTrees: 
						simpleRemoveTree(level, x, y ,z)	
				else:
					surfaceFound = True
		if not surfaceFound:
			y -= 1
	return y				

#Obtains the steepness of every block
def calculateSteepnessMap(level, surface):

	for x in range(surface.xLength):
		for z in range(surface.zLength):
			calculateSteepness(level,surface,x,z)

#Obtains the steepness of a block
def calculateSteepness(level,surface,x,z):
	north = 0
	east = 0
	west = 0
	south = 0
	#Obtain height differences between a block and its neighbours
	if surface.toRealX(x) > surface.xStart:
		west += surface.surfaceMap[x][z].height - surface.surfaceMap[x-1][z].height
	if surface.toRealZ(z) > surface.zStart:
		north += surface.surfaceMap[x][z].height - surface.surfaceMap[x][z-1].height			
	if surface.toRealX(x) < surface.xEnd-1:
		east += surface.surfaceMap[x][z].height - surface.surfaceMap[x+1][z].height
	if surface.toRealZ(z) < surface.zEnd-1:
		south += surface.surfaceMap[x][z].height - surface.surfaceMap[x][z+1].height 
	#Get maximum height and minimum height	
	maxSteep = max(west,south,east,north)
	minSteep = min(west,south,east,north)
	#Save difference
	surface.surfaceMap[x][z].steepness = maxSteep - minSteep	

#Determines if a block is filled with water (Type 9) for every block and stores it on the points variable
def calculateWaterBlocks(level,surface):
	
	for x in range(surface.xLength):
		for z in range(surface.zLength):
			y = surface.surfaceMap[x][z].height
			if level.blockAt(surface.toRealX(x),y,surface.toRealZ(z)) == 9:
				surface.surfaceMap[x][z].isWater =  True  

#Obtains a section
def calculateSection(level,surface, allowedSteepness, id):

	#Gets an unchecked point
	buffer =[getFirstUnchecked(level, surface)]
	if buffer[0] == -1:
		return -1
	#Creates empty section with id value	
	newSection = Section(id)
	#While there are points to check on the buffer
	while buffer:
		point = buffer.pop()
		#Change checked to on
		surface.surfaceMap[point.x][point.z].checked = True
		#Checks that the point is not near a big height difference or is water
		if surface.surfaceMap[point.x][point.z].steepness <= allowedSteepness and not surface.surfaceMap[point.x][point.z].isWater:
			#Checks out of bounds
			if surface.toRealX(point.x) < surface.xEnd-1:
				#If next neighbours are not checked add them to buffer
				if  surface.surfaceMap[point.x+1][point.z].checked == False:
					buffer.append(Point(point.x+1,point.z))
			if surface.toRealZ(point.z) < surface.zEnd-1:
				if  surface.surfaceMap[point.x][point.z+1].checked == False:
					buffer.append(Point(point.x,point.z+1))
			#Add point to section		
			newSection.points.append(point)
			#Uptade sectionId of point
			surface.surfaceMap[point.x][point.z].sectionId = newSection.id
			#Increase section size
			newSection.size += 1	
	#return the section		
	return newSection		

#Functions to obtain the center of a section

#Creates a subSurface for a section
def getSectionSurface(surface, section):

	xStart = section.points[0].x
	xEnd = section.points[0].x
	zStart = section.points[0].z
	zEnd = section.points[0].z
	#Check out of bounds
	for point in section.points:
		if point.x < xStart:
			xStart = point.x
		elif point.x > xEnd:
			xEnd = point.x
		if point.z < zStart:
			zStart = point.z
		elif point.z > zEnd:
			zEnd = point.z
	return SubSurface(xStart, zStart, xEnd + 1, zEnd + 1)

#Obtains section center
def calculateSectionMid(level, surface, section):

	print "getting section surface"
	sectionSurface = getSectionSurface(surface, section)

	#Identify the points outside of the section to exclude it of the search
	print "Excluding outside of section points"
	excludeOutside(surface, section, sectionSurface)

	print "Get border of section"
	getSectionBorderLayer(sectionSurface)
	#Find points of layer 0
	for x in range(1, sectionSurface.xLength - 1):
		for z in range(1, sectionSurface.zLength - 1):
			findLayer(sectionSurface, x, z, 0)

	#Pregressively finds points of layers each depper than the previous
	layer = 1
	finished = False
	while not finished:
		finished = True
		for x in range(0 + layer, sectionSurface.xLength - layer):
			for z in range(0 + layer, sectionSurface.zLength - layer):
				if isPartOfLayer(sectionSurface, x, z, layer):
					findLayer(sectionSurface, x, z, layer)
					finished = False
		layer += 1

	#Stores result and updates layer variable of the surface points
	setSectionMid(section, sectionSurface)
	updateSurfacePoints(surface, section, sectionSurface)

#Returns if point is part of layer
def isPartOfLayer(surfaceInfo, x, z, layer):
	return not surfaceInfo.surfaceMap[x][z].checked and surfaceInfo.surfaceMap[x + 1][z].layer == layer - 1

#Sets points layer outside of section to -1
def excludeOutside(surface, section, SubSurface):

	for x in range(SubSurface.xLength):
		for z in range(SubSurface.zLength):
			if section.id != surface.surfaceMap[x + SubSurface.xStart][z + SubSurface.zStart].sectionId:
				SubSurface.surfaceMap[x][z].layer = -1
				SubSurface.surfaceMap[x][z].checked = True

#Sets borders of section to layer 0
def getSectionBorderLayer(SubSurface):

	maxZ = SubSurface.zLength - 1
	for x in range(SubSurface.xLength):
		if not SubSurface.surfaceMap[x][0].checked:
			SubSurface.surfaceMap[x][0].checked = True
			SubSurface.surfaceMap[x][0].layer = 0
		if not SubSurface.surfaceMap[x][maxZ].checked:
			SubSurface.surfaceMap[x][maxZ].checked = True
			SubSurface.surfaceMap[x][maxZ].layer = 0

	maxX = SubSurface.xLength - 1
	for z in range(SubSurface.zLength):
		if not SubSurface.surfaceMap[0][z].checked:
			SubSurface.surfaceMap[0][z].checked = True
			SubSurface.surfaceMap[0][z].layer = 0	
		if not SubSurface.surfaceMap[maxX][z].checked:
			SubSurface.surfaceMap[maxX][z].checked = True
			SubSurface.surfaceMap[maxX][z].layer = 0		

#Identifies points of similar layer
def findLayer(SubSurface, x, z, layer):
	queue = deque()
	queue.append(Point(x, z))
	while queue:
		point = queue.popleft()
		#Checks neighbours for points of similar characteristics
		for xNeighbor in [x - 1, x, x + 1]:
			for zNeighbor in [z - 1, z, z + 1]:
				if xNeighbor == x and zNeighbor == z:
					continue
				#If the layer is equal to the current - 1, add it to current layer	
				if SubSurface.surfaceMap[xNeighbor][zNeighbor].layer == layer - 1:
					SubSurface.surfaceMap[x][z].layer = layer
					SubSurface.surfaceMap[x][z].checked = True
					if not SubSurface.surfaceMap[xNeighbor][zNeighbor].checked and SubSurface.surfaceMap[xNeighbor][zNeighbor].isCheckedByLayer != layer:
						SubSurface.surfaceMap[xNeighbor][zNeighbor].isCheckedByLayer = layer
						queue.append(Point(xNeighbor, zNeighbor))

#Stores the section middle point and layer attributes
def setSectionMid(section, SubSurface):
	xMid = 0
	zMid = 0
	layer = -2
	for x in range(SubSurface.xLength):
		for z in range(SubSurface.zLength):
			if layer < SubSurface.surfaceMap[x][z].layer:
				xMid = x
				zMid = z
				layer = SubSurface.surfaceMap[x][z].layer
	section.xMid = xMid + SubSurface.xStart
	section.zMid = zMid + SubSurface.zStart
	section.layerDepth = layer + 1

#Update layer value of section points
def updateSurfacePoints(surface, section, SubSurface):
	for x in range(SubSurface.xLength):
		for z in range(SubSurface.zLength):
			if section.id == surface.surfaceMap[SubSurface.xStart + x][SubSurface.zStart + z].sectionId:
				surface.surfaceMap[SubSurface.xStart + x][SubSurface.zStart + z].layer = SubSurface.surfaceMap[x][z].layer
				

#End of center identifying methods

#Section Classifier

#Classifies sections by size after validating them
def sectionClassifier(sections, bigSections,  mediumSections, smallSections):

	validateSections(sections)
	for section in sections:
		if section.size < 250:
			smallSections.append(section)
			continue
		if section.size < 1000:
			mediumSections.append(section)	
			continue	
		bigSections.append(section)

#Functions to easily get and update groups of unchecked points

#Gets the first unchecked point
def getFirstUnchecked(level, surface):
	for x in range(surface.xLength):
		for z in range(surface.zLength): 
			if surface.surfaceMap[x][z].checked == False:
				return Point(x,z)	
	return -1			

#Gets a list with all the unchecked points
def calculateUncheckedPoints(level, surface):
	uncheckedPoints = []
	for x in range(surface.xLength):
		for z in range(surface.zLength): 
			if surface.surfaceMap[x][z].checked == False:
				uncheckedPoints.append(surface.surfaceMap[x][z])
	return uncheckedPoints		

#To validate sections
def validateSections(sections):
	toRemove = []
	#Removes sections with layer depth less than 2 (too small/irregular)
	for section in sections:
		if section.layerDepth < 2:
			toRemove.append(section) 	
	while(toRemove):
		sections.remove(toRemove.pop())  		   
	return sections		

#Obtains a sections average height
def calculateAverageSectionHeight(level, surface, section):
	
	average = 0
	points = section.size
	for point in section.points:
		average += surface.surfaceMap[point.x][point.z].height 
	section.averageHeight = average/points


#Trees and bushes dictionary
treeBlocks = [17, 18, 31, 37, 38, 99, 100, 106, 161, 162, 175]
#Returns wheter a block is a tree or bush
def isTreeBlock(level, x, y, z):
		for block in treeBlocks:
			if (level.blockAt(x, y, z) == block):
				return True
		return False		

# Unused. Removes a tree block and checks neighbours till no more tree blocks are found.
#Too time consuming and low efficiency
def removeTree(level, x, y, z):
	blocks = [Block(x, y, z)]
	while blocks:
		nextBlock = blocks.pop()
		x = nextBlock.x
		y = nextBlock.y
		z = nextBlock.z

		if level.blockAt(x, y + 1, z) == 78:
			level.setBlockAt(x,y+1,z,0)
 			level.setBlockDataAt(x,y+1,z,0)

		if not isTreeBlock(level, x, y, z):
			continue

		level.setBlockAt(x,y,z,0)
		level.setBlockDataAt(x,y,z,0)
		#Removes snow layer


		# Adds neighbors to stack
		blocks.extend([Block(x + 1, y, z), Block(x - 1, y, z), Block(x, y + 1, z), Block(x, y - 1, z), Block(x, y, z + 1), Block(x, y, z - 1)])

#Removes a tree block
def simpleRemoveTree(level, x, y ,z):

	#Removes snow layer
	if level.blockAt(x, y + 1, z) == 78:
		level.setBlockAt(x,y+1,z,0)
 		level.setBlockDataAt(x,y+1,z,0)

	if isTreeBlock(level, x, y, z):
		level.setBlockAt(x,y,z,0)
		level.setBlockDataAt(x,y,z,0)


#City planning functions

#Gets middle point on a direction from the section center
def getMidPoint(surface, section, direction):

	midX = section.xMid
	midZ = section.zMid

	if direction == "East":
		midX = midX + midX/2 + 1
		return Point(midX,midZ)
	if direction == "West":
		midX = midX - midX/2 + 1
		return Point(midX,midZ)
	if direction == "North":
		midZ = midZ - midZ/2 + 1
		return Point(midX,midZ)
	if direction == "South":
		midZ = midZ + midZ/2 + 1
		return Point(midX,midZ)

#Levels all the terrain points to the height of the center
def levelTerrain(level, surface, point, terrainHeight):
	#Checks that the loop is not blocked
	bugcheck = 0
	#Checks out of bounds
	if surface.toRealX(point.x) < surface.xStart or surface.toRealX(point.x) > surface.xEnd or surface.toRealZ(point.z) < surface.zStart or surface.toRealZ(point.z) > surface.zEnd:
		return terrainHeight
	#Height of current point	
	pointHeight = surface.surfaceMap[point.x][point.z].height 
	#Level terrain
	while (level.blockAt(surface.toRealX(point.x),terrainHeight+1,surface.toRealZ(point.z)) != 0) and pointHeight != terrainHeight:
		#leveling down terrain
		#Terrain is already lower. Checking failed. Restarts method if it is the first iteration
		if pointHeight <= terrainHeight and bugcheck == 0:
			pointHeight = terrainHeight + 1
		level.setBlockAt(surface.toRealX(point.x),(pointHeight),surface.toRealZ(point.z), 0 )
		level.setBlockDataAt(surface.toRealX(point.x),(pointHeight),surface.toRealZ(point.z), 0)
		surface.surfaceMap[point.x][point.z].height -= 1
		bugcheck += 1
		#Leveling spent way too long
		if bugcheck > 50:	
			print "Error leveling Terrain"
			print terrainHeight, pointHeight, level.blockAt(surface.toRealX(point.x),terrainHeight+1,surface.toRealZ(point.z))
			levelTerrain(level, surface, point, terrainHeight)
			return terrainHeight
		pointHeight -= 1
	while (level.blockAt(surface.toRealX(point.x),pointHeight+1,surface.toRealZ(point.z)) == 0) and pointHeight != terrainHeight:
		#leveling up terrain
		#Terrain is already lower. Checking failed. Restarts method if it is the first iteration
		if pointHeight >= terrainHeight and bugcheck == 0:
			pointHeight = terrainHeight - 1
		groundBlock = level.blockAt(surface.toRealX(point.x), pointHeight - 1,surface.toRealZ(point.z))
		if groundBlock == 0:
			groundBlock = 2
		level.setBlockAt(surface.toRealX(point.x), pointHeight,surface.toRealZ(point.z), groundBlock)
		level.setBlockDataAt(surface.toRealX(point.x),pointHeight,surface.toRealZ(point.z),0)
		surface.surfaceMap[point.x][point.z].height += 1
		bugcheck += 1
		#Leveling spent way too long
		if bugcheck > 50:	
			print "Error leveling Terrain"
			print terrainHeight, pointHeight, level.blockAt(surface.toRealX(point.x),terrainHeight-1,surface.toRealZ(point.z))
			surface.surfaceMap[point.x][point.z].height = terrainHeight
			return terrainHeight
		pointHeight += 1
	#Cleans block inmediately over the current
	level.setBlockAt(surface.toRealX(point.x),(terrainHeight+1),surface.toRealZ(point.z), 0 )
	level.setBlockDataAt(surface.toRealX(point.x),(terrainHeight+1),surface.toRealZ(point.z), 0 )	
	level.setBlockDataAt(surface.toRealX(point.x),(terrainHeight),surface.toRealZ(point.z), 0 )

	return terrainHeight

#Removes snow on section
def sectionDefrost(level, section, surface):

	for point in section.points:

		if isSnow(level, surface, point):
			level.setBlockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z),0)
			level.setBlockDataAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z),0)
			surface.surfaceMap[point.x][point.z].height -= 1	

#Identifies ice and snoe
def isSnow(level, surface, point):

	if level.blockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z)) ==	78:
		return True
	if level.blockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z)) ==	79:
		return True
	if level.blockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z)) ==	80:
		return True
	return False			



#Structure terrain functions

#Check a row of points
def checkX(surface, section, X, Z, size):
	#Checks out of bound and occupied blocks
	for x in range(X - size/2, X + size/2 + 1):
		if surface.toRealX(x) < surface.xStart + 1 or surface.toRealX(x) > surface.xEnd - 1:
			print " X out of range: ", surface.toRealX(x), surface.xStart, surface.xEnd
			return False
		if surface.surfaceMap[x][Z].isWater or surface.surfaceMap[x][Z].isOccupied:
			print "Surface Occupied at ", x, Z
			return False	
	return True

#Check a column of points
def checkZ(surface, section, X, Z, sizeZ, sizeX):

	#Checks out of bound and occupied blocks
	for z in range(Z - sizeZ/2, Z + sizeZ/2 + 1):
		if surface.toRealZ(z) < surface.zStart + 1 or surface.toRealZ(z) > surface.zEnd - 1:
			print " Z out of range: ", surface.toRealZ(z), surface.zStart, surface.zEnd
			return False
		#Checks the row on that point of the column	
		if not checkX(surface, section, X, z, sizeX):
			return False
	if not checkHeightDiference(surface, X, Z, surface.surfaceMap[X][Z - sizeZ/2].height):
		print "Height check failed"
		return False	
	if not checkHeightDiference(surface, X, Z, surface.surfaceMap[X][Z + sizeZ/2].height):
		print "Height check failed"
		return False					
	return True		

#Gets position of building relative to the center
def getDirection(X,centerX, Z, centerZ):
	direction = None
	distanceZ = abs(Z - centerZ)
	distanceX = abs(X - centerX)
	if distanceX < distanceZ:
		if Z > centerZ:
			direction = "South"
		else:
			direction = "North"
	else:
		if X > centerX:
			direction = "East"
		else:
			direction = "West"
	return direction

#Return wheter the point is at the north or south of the center
def getDirectionNS( Z,  centerZ):
	direction = None
	if Z > centerZ:
		direction = "South"
	else:
		direction = "North"
	return direction

#Return wheter the point is at the west or east of the center
def getDirectionEW(X,centerX):
	direction = None
	if X > centerX:
		direction = "East"
	else:
		direction = "West"
	return direction

#Changes materials after getting section biome to its own materials
def getBiomeMaterials(level, surface, section):

	sectionPoints = []
	for point in section.points:
		sectionPoints.append(Point(surface.toRealX(point.x),surface.toRealZ(point.z)))
	biome = getBiome(level, surface, sectionPoints)
	#Aquatic, plains, swamp, riverBeach, taiga, savana, Badlands share default materials
	if biome == "desert":
		#SandStone
		section.materials.materialRoof = (24,0)
		#Stone
		section.materials.materialFoundation = (1,0)
		section.materials.materialWall = (24,0)
		section.materials.water = (9,0)
		#Potatoes
		section.materials.crops = (142,0)
		#Sand
		section.materials.garden = (12,0)
		#Sanstone Slab
		section.materials.ground = (43,1)
		#Nether Brick Fence
		section.materials.fences = (113,0)
		section.materials.animal = "cow"

	if biome == "mountains":
		#DoubleStoneSlab
		section.materials.materialRoof = (43,0)
		#DoubleStoneSlab
		section.materials.materialFoundation = (1,0)
		section.materials.materialWall = (43,0)
		section.materials.water = (9,0)
		#Pumpkin 
		section.materials.crops = (86,0)
		#Stone
		section.materials.garden = (1,0)
		#Satone Slab
		section.materials.ground = (43,0)
		#Fence
		section.materials.fences = (85,0)
		section.materials.animal = "sheep"

	if biome == "birchForest":
		#BirchWood
		section.materials.materialRoof = (17,2)
		#BirchWood
		section.materials.materialFoundation = (17,2)
		#BirchWood Slab
		section.materials.materialWall = (125, 2)
		section.materials.water = (9,0)
		#Grass
		section.materials.garden = (2,0)
		#Stone Slab
		section.materials.ground = (43,0)
		#Birch Fence
		section.materials.fences = (189,0)
		section.materials.animal = "chicken"

	if biome == "darkForest":
		#Oak
		section.materials.materialRoof = (17,1)
		#Oak
		section.materials.materialFoundation = (17,1)
		section.materials.materialWall = (125,0)
		section.materials.water = (9,0)
		#Grass
		section.materials.garden = (2,0)
		#Stone Slab
		section.materials.ground = (43,0)
		#WoodPlanks
		section.materials.fences = (5,0)
		section.materials.animal = "horse"

	if biome == "snowyIcy":
		#Diamond
		section.materials.materialRoof = (57,0)
		#Diamond
		section.materials.materialFoundation = (57,0)
		#Ice
		section.materials.materialWall = (79,0)
		#Ice
		section.materials.water = (79,0)
		#Potatoes
		section.materials.crops = (142,0)
		#Sand
		section.materials.garden = (12,0)
		#Stone Slab
		section.materials.ground = (43,0)
		#Ice
		section.materials.fences = (79,0)
		section.materials.animal = "sheep"

	if biome == "jungle":
		#Jungle Wood
		section.materials.materialRoof = (17,3)
		#Jungle Wood
		section.materials.materialFoundation = (17,3)
		#Jungle Slab 
		section.materials.materialWall = (125, 3)
		section.materials.water = (9,0)
		#Grass
		section.materials.garden = (2,0)
		#Stone Slab
		section.materials.ground = (43,0)
		#Jungle fences
		section.materials.fences = (190,0)
		section.materials.animal = "pig"

	if biome == "mushroom":
		#Red Mushroom 
		section.materials.materialRoof = (40,0)
		#Brown Mushroom 
		section.materials.materialFoundation = (39,0)
		section.materials.materialWall = (39, 0)
		section.materials.water = (9,0)
		#Grass
		section.materials.garden = (2,0)
		#Stone Slab
		section.materials.ground = (39,0)
		section.materials.fences = (5,0)
		section.materials.animal = "pig"


#Building functions

#Build a landmark
def buildLandmark(level, surface, X, Z, height, name, extraMaterial):

	xMax = X + 2
	xMin = X - 2
	zMax = Z + 2
	zMin = Z - 2
	
	if surface.toRealX(xMin) <= surface.xStart:
		print "Aborted construction of landmark at ", X, Z 
		return -1
	
	if surface.toRealX(xMax) >= surface.xEnd:
		print "Aborted construction of landmark at ", X, Z 
		return -1
	
	if surface.toRealZ(zMin) <= surface.zStart:
		print "Aborted construction of landmark at ", X, Z 
		return -1
	
	if surface.toRealZ(zMax) >= surface.zEnd:
		print "Aborted construction of landmark at ", X, Z 
		return -1
	
	#Builds a fountain
	if name == "fountain":
		print "Building Fountain at: ", X, ",", Z
		for x in range(xMin, xMax + 1):
			for z in range(zMin, zMax + 1):
				levelTerrain(level, surface, Point(x,z), height)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),43)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),0)
				surface.surfaceMap[x][z].isOccupied = True
				if x == xMin or x == xMax or z == zMin or z == zMax:
					level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),43)
					level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),0)
					surface.surfaceMap[x][z].height += 1
				elif x == X and z == Z:
					level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),43)
					level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),0)
					level.setBlockAt(surface.toRealX(x),height + 2,surface.toRealZ(z),43)
					level.setBlockDataAt(surface.toRealX(x),height + 2,surface.toRealZ(z),0)
					surface.surfaceMap[x][z].height += 2
				else:
					level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),extraMaterial[0])
					level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),extraMaterial[1])
					surface.surfaceMap[x][z].isWater = True
	#builds a small farm
	elif name == "farm":
		print "Building Farm at: ", X, ",", Z
		for x in range(xMin, xMax + 1):
			for z in range(zMin, zMax + 1):
				levelTerrain(level, surface, Point(x,z), height)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),43)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),0)
				surface.surfaceMap[x][z].isOccupied = True
				if x == xMin or x == xMax or z == zMin or z == zMax:
					level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),43)
					level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),0)
					surface.surfaceMap[x][z].height += 1
				elif x == X and z == Z:
					level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),9)
					level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),0)
					surface.surfaceMap[x][z].height += 1
				else:
					level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),60)
					level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),0)
					level.setBlockAt(surface.toRealX(x),height + 2,surface.toRealZ(z),extraMaterial[0])
					level.setBlockDataAt(surface.toRealX(x),height + 2,surface.toRealZ(z),extraMaterial[1])
					surface.surfaceMap[x][z].height += 2

#Builds a corral		
def buildCorral(level, surface, section, X, Z, animalName, fences):

	#Vertical corral
	if checkZ(surface, section, X, Z, 7, 9):
		xMax = X + 2
		xMin = X - 2
		zMax = Z + 3
		zMin = Z - 3

		height = surface.surfaceMap[X][Z].height
		#Sets blocks
		for x in range(xMin, xMax + 1):
			for z in range(zMin, zMax + 1):
				levelTerrain(level, surface, Point(x,z), height)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),60)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),0)
				surface.surfaceMap[x][z].isOccupied = True
				#Sets animal at center of corral
				if x == X and z == Z: 
					animal = TAG_Compound()
					animal["id"] = TAG_String(animalName)
					animal["Pos"] = TAG_List([TAG_Double(x + 0.5), TAG_Double(height), TAG_Double(z + 0.5)])
					chunk = level.getChunk(surface.toRealX(x) / 16, surface.toRealZ(z) / 16)
					chunk.Entities.append(animal)
					chunk.dirty = True
				if z == zMin or z == zMax:
					level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),fences[0])
					level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),fences[1])
					if x == X:
						level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),107)
						level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),0)

				if x == xMin or x == xMax:
					level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),fences[0])
					level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),fences[1])

	#Horizontal corral
	elif checkZ(surface, section, X, Z, 7, 9):
		xMax = X + 3
		xMin = X - 3
		zMax = Z + 2
		zMin = Z - 2

		height = surface.surfaceMap[X][Z].height

		for x in range(xMin, xMax + 1):
			for z in range(zMin, zMax + 1):
				levelTerrain(level, surface, Point(x,z), height)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),60)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),0)
				surface.surfaceMap[x][z].isOccupied = True
				if z == zMin or z == zMax:
					level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),fences[0])
					level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),fences[1])
					surface.surfaceMap[x][z].height += 25

				if x == xMin or x == xMax:
					level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),fences[0])
					level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),fences[1])
					surface.surfaceMap[x][z].height += 25
					if z == Z:
						level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),107)
						level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),0)
	
		level.setBlockAt(surface.toRealX(xMax-1),height+1,surface.toRealZ(zMax-1),118)
		level.setBlockDataAt(surface.toRealX(xMax-1),height+1,surface.toRealZ(zMax-1),0)						
	else:
		print "Couldn't build corral"

#Builds horizontally oriented house
def buildHouseEW(level, surface, X, Z, height, direction, materials):

	zMin = Z - 2
	zMax = Z + 2
	xMin = X - 3
	xMax = X + 3
	
	if surface.toRealX(xMin - 2) <= surface.xStart:
		print "Aborted construction of House at ", X, Z 
		return 0
	
	if surface.toRealX(xMax + 2) >= surface.xEnd:
		print "Aborted construction of House at ", X, Z 
		return 0
	
	if surface.toRealZ(zMin - 2) <= surface.zStart:
		print "Aborted construction of House at ", X, Z 
		return 0
	
	if surface.toRealZ(zMax + 2) >= surface.zEnd:
		print "Aborted construction of House at ", X, Z 
		return 0
	

	for x in range(xMin-2, xMax + 3):
		for z in range(zMin-2, zMax + 3):
			if x == xMax + 1 or x == xMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True
			if z == zMax + 1 or zMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True	
	
	for x in range(xMin - 2,xMax + 3):
		for z in range(zMin - 2,zMax + 3):
			levelTerrain(level, surface, Point(x,z), height)
			if x == xMax + 2 or x == xMin - 2 or z == zMin - 2 or z == zMax + 2:
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[1])
				level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),85)
				level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),0)
			else:
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[1])

	height += 1

	for x in range(xMin,xMax + 1):

			surface.surfaceMap[x][zMin].isOccupied = True
			surface.surfaceMap[x][zMax].isOccupied = True
			buildRoofRow(level, surface, x, zMin, zMax, Z, height + 4, materials.materialRoof)

			if direction == "East" and x == X:
				buildColumn(level, surface, x, zMax, height, materials.materialWall, True, False)
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMax + 2),0)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMax + 2),0)


			elif direction == "West" and x == X:	
				buildColumn(level, surface, x, zMin, height, materials.materialWall, True, False)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMin - 2),0)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMin - 2),0)

			elif x == xMin or x == xMax:
				buildColumn(level, surface, x, zMin, height, materials.materialFoundation, False, False)
				buildColumn(level, surface, x, zMax, height, materials.materialFoundation, False, False)

			elif x == X + 1 or x == X - 1:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
			else:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)
	

	for z in range(zMin + 1, zMax):

		surface.surfaceMap[xMin][z].isOccupied = True
		surface.surfaceMap[xMax][z].isOccupied = True
		if z == Z:
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)
			level.setBlockAt(surface.toRealX(xMin),height + 5,surface.toRealZ(z), materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(xMin),height + 5 ,surface.toRealZ(z),materials.materialWall[1])
			level.setBlockAt(surface.toRealX(xMax),height + 5,surface.toRealZ(z),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(xMax),height + 5 ,surface.toRealZ(z),materials.materialWall[1])
		else:
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)	

		level.setBlockAt(surface.toRealX(xMax),height + 4,surface.toRealZ(z),materials.materialWall[0])
		level.setBlockDataAt(surface.toRealX(xMax),height + 4 ,surface.toRealZ(z),materials.materialWall[1])
		level.setBlockAt(surface.toRealX(xMin),height + 4,surface.toRealZ(z),materials.materialWall[0])
		level.setBlockDataAt(surface.toRealX(xMin),height + 4 ,surface.toRealZ(z),materials.materialWall[1])


#Builds horizontally oriented hut
def buildHutEW(level, surface, X, Z, height, direction, materials):

	zMin = Z - 2
	zMax = Z + 2
	xMin = X - 2
	xMax = X + 2
	
	if surface.toRealX(xMin - 2) <= surface.xStart:
		print "Aborted construction of Hut at ", X, Z 
		return 0
	
	if surface.toRealX(xMax + 2) >= surface.xEnd:
		print "Aborted construction of Hut at ", X, Z 
		return 0
	
	if surface.toRealZ(zMin - 2) <= surface.zStart:
		print "Aborted construction of Hut at ", X, Z 
		return 0
	
	if surface.toRealZ(zMax + 2) >= surface.zEnd:
		print "Aborted construction of Hut at ", X, Z 
		return 0
	

	for x in range(xMin-2, xMax + 3):
		for z in range(zMin-2, zMax + 3):
			if x == xMax + 1 or x == xMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True
			if z == zMax + 1 or zMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True	
	
	for x in range(xMin - 2,xMax + 3):
		for z in range(zMin - 2,zMax + 3):
			levelTerrain(level, surface, Point(x,z), height)
			if x == xMax + 2 or x == xMin - 2 or z == zMin - 2 or z == zMax + 2:
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[1])
				level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),85)
				level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),0)
			else:
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[1])

	height += 1
	for x in range(xMin,xMax + 1):
			surface.surfaceMap[x][zMin].isOccupied = True
			surface.surfaceMap[x][zMax].isOccupied = True
			buildRoofRow(level, surface, x, zMin, zMax, Z, height + 4, materials.materialRoof)

			if direction == "East" and x == X:
				buildColumn(level, surface, x, zMax, height, materials.materialWall, True, False)
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMax + 2),0)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMax + 2),0)

			elif direction == "West" and x == X:	
				buildColumn(level, surface, x, zMin, height, materials.materialWall, True, False)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMin - 2),0)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMin - 2),0)

			elif x == xMin or x == xMax:
				buildColumn(level, surface, x, zMin, height, materials.materialFoundation, False, False)
				buildColumn(level, surface, x, zMax, height, materials.materialFoundation, False, False)

			elif x == X + 1 or x == X - 1:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
			else:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)
	

	for z in range(zMin + 1, zMax):

		levelTerrain(level, surface, Point(xMin,z), height)
		levelTerrain(level, surface, Point(xMax,z), height)
		surface.surfaceMap[xMin][z].isOccupied = True
		surface.surfaceMap[xMax][z].isOccupied = True
		if z == Z:
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)
			level.setBlockAt(surface.toRealX(xMin),height + 5,surface.toRealZ(z),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(xMin),height + 5 ,surface.toRealZ(z),materials.materialWall[1])
			level.setBlockAt(surface.toRealX(xMax),height + 5,surface.toRealZ(z),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(xMax),height + 5 ,surface.toRealZ(z),materials.materialWall[1])
		else:
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)	

		level.setBlockAt(surface.toRealX(xMax),height + 4,surface.toRealZ(z),materials.materialWall[0])
		level.setBlockDataAt(surface.toRealX(xMax),height + 4 ,surface.toRealZ(z),materials.materialWall[1])
		level.setBlockAt(surface.toRealX(xMin),height + 4,surface.toRealZ(z),materials.materialWall[0])
		level.setBlockDataAt(surface.toRealX(xMin),height + 4 ,surface.toRealZ(z),materials.materialWall[1])

#Builds vertically oriented house
def buildHouseNS(level, surface, X, Z, height, direction, materials):

	zMin = Z - 3
	zMax = Z + 3
	xMin = X - 2
	xMax = X + 2
	
	if surface.toRealX(xMin - 2) <= surface.xStart:
		print "Aborted construction of House at ", X, Z 
		return 0
	
	if surface.toRealX(xMax + 2) >= surface.xEnd:
		print "Aborted construction of House at ", X, Z 
		return 0
	
	if surface.toRealZ(zMin - 2) <= surface.zStart:
		print "Aborted construction of House at ", X, Z 
		return 0
	
	if surface.toRealZ(zMax + 2) >= surface.zEnd:
		print "Aborted construction of House at ", X, Z 
		return 0
	

	for x in range(xMin-2, xMax + 3):
		for z in range(zMin-2, zMax + 3):
			if x == xMax + 1 or x == xMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True
			if z == zMax + 1 or zMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True	
	
	for x in range(xMin - 2,xMax + 3):
		for z in range(zMin - 2,zMax + 3):
			levelTerrain(level, surface, Point(x,z), height)
			if x == xMax - 1 or x == xMin or z == zMin or z == zMax:
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[1])
				level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),85)
				level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),0)
			else:
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[1])

	height += 1
			
	for z in range(zMin,zMax + 1):

		levelTerrain(level, surface, Point(xMin,z), height)
		levelTerrain(level, surface, Point(xMax,z), height)
		surface.surfaceMap[xMin][z].isOccupied = True
		surface.surfaceMap[xMax][z].isOccupied = True
		buildRoofColumn(level, surface, z, xMin, xMax, X, height + 4, materials.materialRoof)

		if direction == "South" and z == Z:
			buildColumn(level, surface, xMax, z, height, materials.materialWall, True, False)
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)	
			level.setBlockAt(surface.toRealX(xMax + 2),height,surface.toRealZ(z),0)
			level.setBlockDataAt(surface.toRealX(xMax + 2),height,surface.toRealZ(z),0)

		elif direction == "North" and z == Z:	
			buildColumn(level, surface, xMin, z, height, materials.materialWall, True, False)
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)
			level.setBlockAt(surface.toRealX(xMin + 2),height,surface.toRealZ(z),0)
			level.setBlockDataAt(surface.toRealX(xMin + 2),height,surface.toRealZ(z),0)

		elif z == zMin or z == zMax:
			buildColumn(level, surface, xMin, z, height, materials.materialFoundation, False, False)
			buildColumn(level, surface, xMax, z, height, materials.materialFoundation, False, False)

		elif z == Z + 1 or z == Z - 1:
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)
		else:
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
	

	for x in range(xMin + 1, xMax):

		surface.surfaceMap[x][zMin].isOccupied = True
		surface.surfaceMap[x][zMax].isOccupied = True
		if x == X:
			buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
			buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)
			level.setBlockAt(surface.toRealX(x),height + 5,surface.toRealZ(zMin),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(x),height + 5 ,surface.toRealZ(zMin),materials.materialWall[1])
			level.setBlockAt(surface.toRealX(x),height + 5,surface.toRealZ(zMax),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(x),height + 5 ,surface.toRealZ(zMax),materials.materialWall[1])
		else:
			buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)
			buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)	

		level.setBlockAt(surface.toRealX(x),height + 4,surface.toRealZ(zMax),materials.materialWall[0])
		level.setBlockDataAt(surface.toRealX(x),height + 4 ,surface.toRealZ(zMax),materials.materialWall[1])
		level.setBlockAt(surface.toRealX(x),height + 4,surface.toRealZ(zMin),materials.materialWall[0])
		level.setBlockDataAt(surface.toRealX(x),height + 4 ,surface.toRealZ(zMin),materials.materialWall[1])

#Builds vertically oriented hohutuse
def buildHutNS(level, surface, X, Z, height, direction, materials):

	zMin = Z - 2
	zMax = Z + 2
	xMin = X - 2
	xMax = X + 2
	
	if surface.toRealX(xMin - 2) <= surface.xStart:
		print "Aborted construction of Hut at ", X, Z 
		return 0
	
	if surface.toRealX(xMax + 2) >= surface.xEnd:
		print "Aborted construction of Hut at ", X, Z 
		return 0
	
	if surface.toRealZ(zMin - 2) <= surface.zStart:
		print "Aborted construction of Hut at ", X, Z 
		return 0
	
	if surface.toRealZ(zMax + 2) >= surface.zEnd:
		print "Aborted construction of Hut at ", X, Z 
		return 0

	for x in range(xMin-2, xMax + 3):
		for z in range(zMin-2, zMax + 3):
			if x == xMax + 1 or x == xMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True
			if z == zMax + 1 or zMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True	
	
	for x in range(xMin - 2,xMax + 3):
		for z in range(zMin - 2,zMax + 3):
			levelTerrain(level, surface, Point(x,z), height)
			if x == xMax - 1 or x == xMin or z == zMin or z == zMax:
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),materials.garden[1])
				level.setBlockAt(surface.toRealX(x),height + 1,surface.toRealZ(z),85)
				level.setBlockDataAt(surface.toRealX(x),height + 1,surface.toRealZ(z),0)		

	height += 1

	for z in range(zMin,zMax + 1):

		surface.surfaceMap[xMin][z].isOccupied = True
		surface.surfaceMap[xMax][z].isOccupied = True
		buildRoofColumn(level, surface, z, xMin, xMax, X, height + 4, materials.materialRoof)

		if direction == "South" and z == Z:
			buildColumn(level, surface, xMax, z, height, materials.materialWall, True, False)
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)			
			level.setBlockAt(surface.toRealX(xMax + 2),height,surface.toRealZ(z),0)
			level.setBlockDataAt(surface.toRealX(xMax + 2),height,surface.toRealZ(z),0)

		elif direction == "North" and z == Z:	
			buildColumn(level, surface, xMin, z, height, materials.materialWall, True, False)
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)
			level.setBlockAt(surface.toRealX(xMin - 2),height,surface.toRealZ(z),0)
			level.setBlockDataAt(surface.toRealX(xMin - 2),height,surface.toRealZ(z),0)

		elif z == zMin or z == zMax:
			buildColumn(level, surface, xMin, z, height, materials.materialFoundation, False, False)
			buildColumn(level, surface, xMax, z, height, materials.materialFoundation, False, False)

		elif z == Z + 1 or z == Z - 1:
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)
		else:
			buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)
			buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
	

	for x in range(xMin + 1, xMax):

		surface.surfaceMap[x][zMin].isOccupied = True
		surface.surfaceMap[x][zMax].isOccupied = True
		if x == X:
			buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
			buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)
			level.setBlockAt(surface.toRealX(x),height + 5,surface.toRealZ(zMin), materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(x),height + 5 ,surface.toRealZ(zMin),materials.materialWall[1])
			level.setBlockAt(surface.toRealX(x),height + 5,surface.toRealZ(zMax),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(x),height + 5 ,surface.toRealZ(zMax),materials.materialWall[1])
		else:
			buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)
			buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)	

		level.setBlockAt(surface.toRealX(x),height + 4,surface.toRealZ(zMax), materials.materialWall[0])
		level.setBlockDataAt(surface.toRealX(x),height + 4 ,surface.toRealZ(zMax),materials.materialWall[1])
		level.setBlockAt(surface.toRealX(x),height + 4,surface.toRealZ(zMin),materials.materialWall[0])
		level.setBlockDataAt(surface.toRealX(x),height + 4 ,surface.toRealZ(zMin),materials.materialWall[1])


#Builds a column of blocks of height 4
def buildColumn(level, surface, X, Z, height, material, door, window):

	surface.surfaceMap[X][Z].isOccupied = True

	for y in range(4):
		if y < 2 and door:
			level.setBlockAt(surface.toRealX(X),height + y,surface.toRealZ(Z),64)
			level.setBlockDataAt(surface.toRealX(X),height + y,surface.toRealZ(Z),0)
		elif y == 2 and window:	
			level.setBlockAt(surface.toRealX(X),height + y,surface.toRealZ(Z),20)
			level.setBlockDataAt(surface.toRealX(X),height + y,surface.toRealZ(Z),0)
		else:
			level.setBlockAt(surface.toRealX(X),height + y,surface.toRealZ(Z),material[0])
			level.setBlockDataAt(surface.toRealX(X),height + y,surface.toRealZ(Z),material[1])

#Build a row of the roof. Triangular form. East to West		
def buildRoofRow(level, surface, X, zMin, zMax, zMid, height, material):

	counter = 0

	for z in range(zMin, zMid):

		level.setBlockAt(surface.toRealX(X),height + counter,surface.toRealZ(z),material[0])
		level.setBlockDataAt(surface.toRealX(X),height + counter,surface.toRealZ(z),material[1])
		surface.surfaceMap[X][z].isOccupied = True
		surface.surfaceMap[X][z].height = height + counter
		counter += 1	


	level.setBlockAt(surface.toRealX(X),height + counter,surface.toRealZ(zMid),material[0])
	level.setBlockDataAt(surface.toRealX(X),height + counter,surface.toRealZ(zMid),material[1])
	surface.surfaceMap[X][zMid].isOccupied = True
	surface.surfaceMap[X][zMid].height = height + counter
	counter -=1

	for z in range(zMid + 1, zMax+1):

		level.setBlockAt(surface.toRealX(X),height + counter,surface.toRealZ(z),material[0])
		level.setBlockDataAt(surface.toRealX(X),height + counter,surface.toRealZ(z),material[1])
		surface.surfaceMap[X][z].isOccupied = True
		surface.surfaceMap[X][z].height = height + counter
		counter -= 1	

#Build a row of the roof. Triangular form. South to North
def buildRoofColumn(level, surface, Z, xMin, xMax, xMid, height, material):

	counter = 0

	for x in range(xMin, xMid):

		level.setBlockAt(surface.toRealX(x),height + counter,surface.toRealZ(Z),material[0])
		level.setBlockDataAt(surface.toRealX(x),height + counter,surface.toRealZ(Z),material[1])
		surface.surfaceMap[x][Z].isOccupied = True
		counter += 1	


	level.setBlockAt(surface.toRealX(xMid),height + counter,surface.toRealZ(Z),material[0])
	level.setBlockDataAt(surface.toRealX(xMid),height + counter,surface.toRealZ(Z),material[1])
	surface.surfaceMap[xMid][Z].isOccupied = True
	counter -=1

	for x in range(xMid + 1, xMax+1):

		level.setBlockAt(surface.toRealX(x),height + counter,surface.toRealZ(Z),material[0])
		level.setBlockDataAt(surface.toRealX(x),height + counter,surface.toRealZ(Z),material[1])
		surface.surfaceMap[x][Z].isOccupied = True
		counter -= 1			

#Checks for big height jumps (>5)
def checkHeightDiference(surface, x, z, height):

	difference = abs(height - surface.surfaceMap[x][z].height)
	if difference > 5:
		return False
	return True	
	
#Tries to build 4 houseson a section. Returns built houses	
def buildMediumSection(level, surface, section):
	houses = 0
	xMid = section.xMid
	zMid = section.zMid
	if checkZ(surface, section, xMid + xMid/2, zMid +  zMid/2, 9, 11):
		houses += 1
		buildHouseEW(level, surface, xMid + xMid/2, zMid +  zMid/2, surface.surfaceMap[xMid + xMid/2][zMid + zMid/2].height, "West",  section.materials)
		path = getAStarPath(surface, xMid+3, zMid+3, xMid + xMid/2, zMid +  zMid/2 - 3)
		if path:
			buildPath(level, surface, path)
	if checkZ(surface, section, xMid + xMid/2, zMid -  zMid/2, 9, 11):
		houses += 1
		buildHouseEW(level, surface, xMid + xMid/2, zMid -  zMid/2, surface.surfaceMap[xMid + xMid/2][zMid -  zMid/2].height, "East",  section.materials)
		path = getAStarPath(surface, xMid+3, zMid-3, xMid + xMid/2, zMid -  zMid/2 + 3)
		if path:
			buildPath(level, surface, path)
	if checkZ(surface, section, xMid - xMid/2, zMid -  zMid/2, 9, 11):
		houses += 1
		buildHouseEW(level, surface, xMid - xMid/2,zMid -  zMid/2, surface.surfaceMap[xMid - xMid/2][zMid -  zMid/2].height, "East",  section.materials)
		path = getAStarPath(surface, xMid-3, zMid-3, xMid - xMid/2, zMid -  zMid/2 + 3)
		if path:
			buildPath(level, surface, path)
	if checkZ(surface, section, xMid - xMid/2, zMid +  zMid/2, 9, 11):
		houses += 1
		buildHouseEW(level, surface, xMid - xMid/2, zMid +  zMid/2, surface.surfaceMap[xMid - xMid/2][zMid +  zMid/2].height, "West",  section.materials)		
		path = getAStarPath(surface, xMid-3, zMid+3, xMid - xMid/2, zMid +  zMid/2 - 3)
		if path:
			buildPath(level, surface, path)
	print houses, " houses built"		
	return houses

#Searchs a point on a section from where to build a hut
def buildSmallSection(level, surface, section):
	built = False
	print "Trying to build on section ", section.id
	#Tries building at center
	if checkZ(surface, section,section.xMid, section.zMid, 9, 9):
		print "House built at ", section.xMid, section.zMid
		height = surface.surfaceMap[ section.xMid][section.zMid].height
		if height < surface.surfaceMap[section.xMid][section.zMid].height:
			height = surface.surfaceMap[section.xMid][section.zMid].height
		direction = getDirection(section.xMid + 2,  section.xMid, section.zMid, section.zMid)
		if direction == "West":
			if level.blockAt(section.xMid-3, height, section.zMid) != 0 or level.blockAt(section.xMid-3, height + 1, section.zMid) != 0:
				direction = "East"
				section.xMid = section.xMid + 4
				section.zMid = section.zMid 
			else:	
				section.xMid = section.xMid - 4
				section.zMid = section.zMid 
			buildHutEW(level, surface, section.xMid, section.zMid, height, direction,  section.materials)
			built = True

		elif direction == "East":
			if level.blockAt(section.xMid+3, height, section.zMid) != 0 or level.blockAt(section.xMid+3, height + 1, section.zMid) != 0:
				direction = "West"
				section.xMid = section.xMid - 4
				section.zMid = section.zMid 
			else:
				section.xMid = section.xMid + 4
				section.zMid = section.zMid 
			buildHutEW(level, surface, section.xMid, section.zMid, height, direction, section.materials)
			built = True

		elif direction == "North":
			if level.blockAt(section.xMid, height, section.zMid-3) != 0 or level.blockAt(section.xMid, height + 1, section.zMid-3) != 0:
				direction = "South"
				section.xMid = section.xMid 
				section.zMid = section.zMid + 4
			else:
				section.xMid = section.xMid
				section.zMid = section.zMid - 4
			buildHutNS(level, surface, section.xMid, section.zMid, height, direction,  section.materials)
			built = True	
		else:
			if level.blockAt(section.xMid, height, section.zMid+3) != 0 or level.blockAt(section.xMid, height + 1, section.zMid+3) != 0:
				direction = "North"
				section.xMid = section.xMid
				section.zMid = section.zMid - 4
			else:	
				section.xMid = section.xMid 
				section.zMid = section.zMid + 4
			buildHutNS(level, surface, section.xMid, section.zMid, height, direction,  section.materials)
			built = True		
	#Tries everywhere else on the section
	else:
		for point in section.points:
			if built:
				continue
			if checkZ(surface, section, point.x, point.z, 9, 9):
				height = surface.surfaceMap[ point.x][point.z].height
				if height < surface.surfaceMap[section.xMid][section.zMid].height:
					height = surface.surfaceMap[section.xMid][section.zMid].height
				direction = getDirectionEW( point.x,  section.xMid)
				if direction == "West":
					if level.blockAt(point.x-3, height, point.z) != 0 and level.blockAt(point.x-3, height+1, point.z) != 0 or level.blockAt(point.x - 4, height, point.z) != 0:
						direction == "East"
						section.xMid = point.x + 4
						section.zMid = point.z 
					else:
						section.xMid = point.x - 4
						section.zMid = point.z 
					buildHutEW(level, surface, point.x, point.z, height, direction,  section.materials)
					print "House built at ", point.x, point.z
					built = True
				elif direction == "East":
					while level.blockAt(point.x+3, height, point.z) != 0 and level.blockAt(point.x+3, height+1, point.z) != 0 or level.blockAt(point.x + 4, height, point.z) != 0:
						direction = "West"
						section.xMid = point.x - 4
						section.zMid = point.z 
					else:
						section.xMid = point.x + 4
						section.zMid = point.z 
					buildHutEW(level, surface, point.x, point.z, height, direction,  section.materials)
					print "House built at ", point.x, point.z
					built = True
				elif direction == "North":
					while level.blockAt(point.x, height, point.z-3) != 0 and level.blockAt(point.x, height+1, point.z-3) != 0 or level.blockAt(point.x, height, point.z-3) != 0:
						height += 1
					section.xMid = point.x
					section.zMid = point.z - 4
				else:
					buildHutNS(level, surface,point.x, point.z, height, direction, 43, 17, 17)
					print "House built at ", point.x, point.z
					built = True
					while level.blockAt(point.x, height, point.z+3) != 0 and level.blockAt(point.x, height + 1, point.z+3) != 0 or level.blockAt(point.x, height, point.z+3) != 0:
						height += 1
					section.xMid = point.x
					section.zMid = point.z + 4
					buildHutNS(level, surface,point.x, point.z, height, direction, section.materials)
					print "House built at ", point.x, point.z
					built = True
				
#Fills path blocks with path material and its neighbour blocks				
def buildPath(level, surface, path):
	height = 0
	previousPoint = None	
	for point in path:	
		if not surface.surfaceMap[point.x][point.z].isOccupied:	
			height = surface.surfaceMap[point.x][point.z].height
			if previousPoint:
				if surface.surfaceMap[previousPoint.x][previousPoint.z].height > height + 1:
					level.setBlockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height + 1,surface.toRealZ(point.z),level.blockAt((surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z))))
					level.setBlockDataAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height + 1,surface.toRealZ(point.z),0)
					height += 1
					surface.surfaceMap[point.x][point.z].height = height
			
			level.setBlockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z),44)
			level.setBlockDataAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z),0)
			surface.surfaceMap[point.x][point.z].isOccupied = True
		else:
			if level.blockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height + 1,surface.toRealZ(point.z)) == 85:
				level.setBlockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height + 1,surface.toRealZ(point.z),0)
				level.setBlockDataAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height + 1,surface.toRealZ(point.z),0)


		if surface.toRealX(point.x + 1) > surface.xEnd - 1:
			print "Path out of range on ", point.x+1, point.z
		elif surface.surfaceMap[point.x][point.z].isWater or level.blockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z)) == 111:
			buildBridgeSection(level, surface, point)	
		elif level.blockAt(surface.toRealX(point.x + 1), surface.surfaceMap[point.x + 1][point.z].height, surface.toRealZ(point.z)) != 44 and not surface.surfaceMap[point.x+1][point.z].isOccupied:
			if height == 0:
				height = surface.surfaceMap[point.x+1][point.z].height
			levelTerrain(level, surface, Point(surface.toRealX(point.x + 1),surface.toRealZ(point.z)), height)
			level.setBlockAt(surface.toRealX(point.x + 1),surface.surfaceMap[point.x + 1][point.z].height,surface.toRealZ(point.z),44)
			level.setBlockDataAt(surface.toRealX(point.x + 1),surface.surfaceMap[point.x + 1][point.z].height,surface.toRealZ(point.z),0)
			surface.surfaceMap[point.x + 1][point.z].isOccupied = True
		if surface.toRealX(point.x - 1) < surface.xStart + 1:
			print "Path out of range on ", point.x-1, point.z
		elif surface.surfaceMap[point.x][point.z].isWater or level.blockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z)) == 111:
			buildBridgeSection(level, surface, point)	
		elif level.blockAt(surface.toRealX(point.x - 1), surface.surfaceMap[point.x - 1][point.z].height, surface.toRealZ(point.z)) != 44 and not surface.surfaceMap[point.x - 1][point.z].isOccupied:
			if height == 0:
				height = surface.surfaceMap[point.x-1][point.z].height
			level.setBlockAt(surface.toRealX(point.x - 1),surface.surfaceMap[point.x - 1][point.z].height,surface.toRealZ(point.z),44)
			level.setBlockDataAt(surface.toRealX(point.x - 1),surface.surfaceMap[point.x - 1][point.z].height,surface.toRealZ(point.z),0)
			surface.surfaceMap[point.x - 1][point.z].isOccupied = True
		
		if surface.toRealZ(point.z + 1) > surface.zEnd - 1:
			print "Path out of range on ", point.x, point.z+1
		elif surface.surfaceMap[point.x][point.z].isWater or level.blockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z)) == 111:
			buildBridgeSection(level, surface, point)	
		elif level.blockAt(surface.toRealX(point.x), surface.surfaceMap[point.x][point.z+ 1].height, surface.toRealZ(point.z + 1)) != 44 and not surface.surfaceMap[point.x][point.z + 1].isOccupied:
			if height == 0:
				height = surface.surfaceMap[point.x][point.z+1].height
			level.setBlockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z + 1].height,surface.toRealZ(point.z + 1),44)
			level.setBlockDataAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z + 1].height,surface.toRealZ(point.z + 1),0)
			surface.surfaceMap[point.x][point.z + 1].isOccupied = True

		if surface.toRealZ(point.z - 1) < surface.zStart + 1:
			print "Path out of range on ", point.x, point.z-1
		elif surface.surfaceMap[point.x][point.z].isWater or level.blockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z].height,surface.toRealZ(point.z)) == 111:
			buildBridgeSection(level, surface, point)	
		elif level.blockAt(surface.toRealX(point.x), surface.surfaceMap[point.x][point.z - 1].height, surface.toRealZ(point.z - 1)) != 44 and not surface.surfaceMap[point.x][point.z - 1].isOccupied:
			if height == 0:
				height = surface.surfaceMap[point.x][point.z-1].height			
			level.setBlockAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z - 1].height,surface.toRealZ(point.z - 1),44)
			level.setBlockDataAt(surface.toRealX(point.x),surface.surfaceMap[point.x][point.z - 1].height,surface.toRealZ(point.z - 1),0)
			surface.surfaceMap[point.x][point.z - 1].isOccupied = True
		previousPoint = point	

#Buiilds a bridge square on a path
def buildBridgeSection(level, surface, point):

	for x in range(point.x - 1, point.x +2):
		for z in range (point.z - 1, point.z + 2):
			if level.blockAt(surface.toRealX(x),surface.surfaceMap[x][z].height,surface.toRealZ(z)) == 9:
				level.setBlockAt(surface.toRealX(x),surface.surfaceMap[x][z].height + 1,surface.toRealZ(z),126)
				level.setBlockDataAt(surface.toRealX(x),surface.surfaceMap[x][z].height + 1,surface.toRealZ(z),0)
			elif level.blockAt(surface.toRealX(x),surface.surfaceMap[x][z].height,surface.toRealZ(z)) == 111:
				level.setBlockAt(surface.toRealX(x),surface.surfaceMap[x][z].height,surface.toRealZ(z),126)
				level.setBlockDataAt(surface.toRealX(x),surface.surfaceMap[x][z].height,surface.toRealZ(z),0)
			elif level.blockAt(surface.toRealX(x),surface.surfaceMap[x][z].height,surface.toRealZ(z)) == 126:
				level.setBlockAt(surface.toRealX(x),surface.surfaceMap[x][z].height + 1,surface.toRealZ(z),126)
				level.setBlockDataAt(surface.toRealX(x),surface.surfaceMap[x][z].height + 1,surface.toRealZ(z),0)	
				if countPlanks(level, surface, Point(x,z)) < 4:
					level.setBlockAt(surface.toRealX(x),surface.surfaceMap[x][z].height + 2,surface.toRealZ(z),50)
					level.setBlockDataAt(surface.toRealX(x),surface.surfaceMap[x][z].height + 2,surface.toRealZ(z),0)

#Return number of bridge blocks surrounding a point
def countPlanks(level, surface, point):
	planks = 0
	for x in range(point.x - 1, point.x +2):
		for z in range (point.z - 1, point.z + 2):
			if level.blockAt(surface.toRealX(x),surface.surfaceMap[x][z].height,surface.toRealZ(z)) == 125 and (x != point.x and z != point.z):
				planks += 1
	return planks

#Returns direction with the most free points left
def getBiggestSubzone(surface, section):

	directions = [[0,"East"],[0,"West"],[0,"South"],[0,"North"]]

	for point in section.points:

		if point.x > section.xMid and not surface.surfaceMap[point.x][point.z].isOccupied:
			directions[0][0] += 1
		if point.x < section.xMid and not surface.surfaceMap[point.x][point.z].isOccupied:
			directions[1][0] += 1
		if point.z > section.zMid and not surface.surfaceMap[point.x][point.z].isOccupied:
			directions[2][0] += 1
		if point.z < section.zMid and not surface.surfaceMap[point.x][point.z].isOccupied:
			directions[3][0] += 1
	print directions
	biggestSubzone = max(directions, key=itemgetter(0))[1]
	return biggestSubzone

#Returns a random direction
def getRandomDirection():

	return random.choice(["East","South","West","North"])

#Builds a church made of wall materials, glass and a golden cross			
def buildChurch(level, surface, X, Z, direction, height, materials):
	
	if direction == "East" or "West":
		zMin = Z - 4
		zMax = Z + 4
		xMin = X - 6
		xMax = X + 6
	else:
		zMin = Z - 6
		zMax = Z + 6
		xMin = X - 4
		xMax = X + 4

	if surface.toRealX(xMin - 2) <= surface.xStart:
		print "Aborted construction of Big Building at ", X, Z 
		return 0
	
	if surface.toRealX(xMax + 2) >= surface.xEnd:
		print "Aborted construction of Big Building at ", X, Z 
		return 0
	
	if surface.toRealZ(zMin - 2) <= surface.zStart:
		print "Aborted construction of Big Building at ", X, Z 
		return 0
	
	if surface.toRealZ(zMax + 2) >= surface.zEnd:
		print "Aborted construction of Big Building at ", X, Z 
		return 0

	for x in range(xMin-2, xMax + 3):
		for z in range(zMin-2, zMax + 3):
			if x == xMax + 1 or x == xMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True
			if z == zMax + 1 or zMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True	
	
	for x in range(xMin - 2,xMax + 3):
		for z in range(zMin - 2,zMax + 3):
			levelTerrain(level, surface, Point(x,z), height)
			level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),materials.ground[0])
			level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),materials.ground[1])

	height += 1

	if direction == "East" or direction == "West":
		for z in range(zMin,zMax + 1):

			surface.surfaceMap[xMin][z].isOccupied = True
			surface.surfaceMap[xMax][z].isOccupied = True

			if direction == "West" and z == Z:
				buildColumn(level, surface, xMax, z, height, materials.materialWall, True, False)
				buildRoofRow(level, surface, xMax, zMin, zMax, Z, height + 3, materials.materialWall)
				buildRoofRow(level, surface, xMax, zMin, zMax, Z, height + 2, materials.materialWall)
				buildRoofRow(level, surface, xMax, zMin, zMax, Z, height + 1, materials.materialWall)
				level.setBlockAt(surface.toRealX(xMax),height + 4,surface.toRealZ(Z),20)
				level.setBlockDataAt(surface.toRealX(xMax),height + 4 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMax),height + 5,surface.toRealZ(Z),20)
				level.setBlockDataAt(surface.toRealX(xMax),height + 5 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMax),height + 6,surface.toRealZ(Z),20)
				level.setBlockDataAt(surface.toRealX(xMax),height + 6 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMax),height + 7,surface.toRealZ(Z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 7 ,surface.toRealZ(Z),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(xMax),height + 4,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 4 ,surface.toRealZ(Z + 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMax),height + 5,surface.toRealZ(Z + 1),20)
				level.setBlockDataAt(surface.toRealX(xMax),height + 5 ,surface.toRealZ(Z + 1),0)
				level.setBlockAt(surface.toRealX(xMax),height + 6,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 6 ,surface.toRealZ(Z + 1),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(xMax),height + 4,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 4 ,surface.toRealZ(Z - 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMax),height + 5,surface.toRealZ(Z - 1),20)
				level.setBlockDataAt(surface.toRealX(xMax),height + 5 ,surface.toRealZ(Z - 1),0)
				level.setBlockAt(surface.toRealX(xMax),height + 6,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 6 ,surface.toRealZ(Z - 1),materials.materialWall[1])

				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)

				buildRoofRow(level, surface, xMin, zMin, zMax, Z, height + 3, materials.materialWall)
				buildRoofRow(level, surface, xMin, zMin, zMax, Z, height + 2, materials.materialWall)
				buildRoofRow(level, surface, xMin, zMin, zMax, Z, height + 1, materials.materialWall)
				level.setBlockAt(surface.toRealX(xMin),height + 4,surface.toRealZ(Z),41)
				level.setBlockDataAt(surface.toRealX(xMin),height + 4 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMin),height + 5,surface.toRealZ(Z),41)
				level.setBlockDataAt(surface.toRealX(xMin),height + 5 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMin),height + 6,surface.toRealZ(Z),41)
				level.setBlockDataAt(surface.toRealX(xMin),height + 6 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMin),height + 7,surface.toRealZ(Z),41)
				level.setBlockDataAt(surface.toRealX(xMin),height + 7 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMin),height + 8,surface.toRealZ(Z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 8 ,surface.toRealZ(Z),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin),height + 9,surface.toRealZ(Z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 9 ,surface.toRealZ(Z),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(xMin),height + 4,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 4 ,surface.toRealZ(Z + 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin),height + 5,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 5 ,surface.toRealZ(Z + 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin),height + 6,surface.toRealZ(Z + 1),41)
				level.setBlockDataAt(surface.toRealX(xMin),height + 6 ,surface.toRealZ(Z + 1),0)
				level.setBlockAt(surface.toRealX(xMin),height + 7,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 7 ,surface.toRealZ(Z + 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin),height + 8,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 8 ,surface.toRealZ(Z + 1),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(xMin),height + 4,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 4 ,surface.toRealZ(Z - 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin ),height + 5,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 5 ,surface.toRealZ(Z - 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin),height + 6,surface.toRealZ(Z - 1),41)
				level.setBlockDataAt(surface.toRealX(xMin),height + 6 ,surface.toRealZ(Z - 1),0)
				level.setBlockAt(surface.toRealX(xMin),height + 7,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 7 ,surface.toRealZ(Z - 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin),height + 8,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 8 ,surface.toRealZ(Z - 1),materials.materialWall[1])

			elif direction == "East" and z == Z:	
				buildColumn(level, surface, xMin, z, height, materials.materialWall, True, False)
				buildRoofRow(level, surface, xMin, zMin, zMax, Z, height + 3, materials.materialWall)
				buildRoofRow(level, surface, xMin, zMin, zMax, Z, height + 2, materials.materialWall)
				buildRoofRow(level, surface, xMin, zMin, zMax, Z, height + 1, materials.materialWall)
				level.setBlockAt(surface.toRealX(xMin),height + 3,surface.toRealZ(Z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 3 ,surface.toRealZ(Z),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin),height + 4,surface.toRealZ(Z),20)
				level.setBlockDataAt(surface.toRealX(xMin),height + 4 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMin),height + 5,surface.toRealZ(Z),20)
				level.setBlockDataAt(surface.toRealX(xMin),height + 5 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMin),height + 6,surface.toRealZ(Z),20)
				level.setBlockDataAt(surface.toRealX(xMin),height + 6 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMin),height + 7,surface.toRealZ(Z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 7 ,surface.toRealZ(Z),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(xMin),height + 4,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 4 ,surface.toRealZ(Z + 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin),height + 5,surface.toRealZ(Z + 1),20)
				level.setBlockDataAt(surface.toRealX(xMin),height + 5 ,surface.toRealZ(Z + 1),0)
				level.setBlockAt(surface.toRealX(xMin),height + 6,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 6 ,surface.toRealZ(Z + 1),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(xMin),height + 4,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 4 ,surface.toRealZ(Z - 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMin),height + 5,surface.toRealZ(Z - 1),20)
				level.setBlockDataAt(surface.toRealX(xMin),height + 5 ,surface.toRealZ(Z - 1),0)
				level.setBlockAt(surface.toRealX(xMin),height + 6,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 6 ,surface.toRealZ(Z - 1),materials.materialWall[1])

				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)

				buildRoofRow(level, surface, xMax, zMin, zMax, Z, height + 3, materials.materialWall)
				buildRoofRow(level, surface, xMax, zMin, zMax, Z, height + 2, materials.materialWall)
				buildRoofRow(level, surface, xMax, zMin, zMax, Z, height + 1, materials.materialWall)
				level.setBlockAt(surface.toRealX(xMax),height + 4,surface.toRealZ(Z),41)
				level.setBlockDataAt(surface.toRealX(xMax),height + 4 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMax),height + 5,surface.toRealZ(Z),41)
				level.setBlockDataAt(surface.toRealX(xMax),height + 5 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMax),height + 6,surface.toRealZ(Z),41)
				level.setBlockDataAt(surface.toRealX(xMax),height + 6 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMax),height + 7,surface.toRealZ(Z),41)
				level.setBlockDataAt(surface.toRealX(xMax),height + 7 ,surface.toRealZ(Z),0)
				level.setBlockAt(surface.toRealX(xMax),height + 8,surface.toRealZ(Z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 8 ,surface.toRealZ(Z),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(xMax),height + 4,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 4 ,surface.toRealZ(Z + 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMax),height + 5,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 5 ,surface.toRealZ(Z + 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMax),height + 6,surface.toRealZ(Z + 1),41)
				level.setBlockDataAt(surface.toRealX(xMax),height + 6 ,surface.toRealZ(Z + 1),0)
				level.setBlockAt(surface.toRealX(xMax),height + 7,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 7 ,surface.toRealZ(Z + 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMax),height + 8,surface.toRealZ(Z + 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 8 ,surface.toRealZ(Z + 1),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(xMax),height + 4,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 4 ,surface.toRealZ(Z - 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMax),height + 5,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 5 ,surface.toRealZ(Z - 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMax),height + 6,surface.toRealZ(Z - 1),41)
				level.setBlockDataAt(surface.toRealX(xMax),height + 6 ,surface.toRealZ(Z - 1),0)
				level.setBlockAt(surface.toRealX(xMax),height + 7,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 7 ,surface.toRealZ(Z - 1),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMax),height + 8,surface.toRealZ(Z - 1),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 8 ,surface.toRealZ(Z - 1),materials.materialWall[1])

			elif z == zMin or z == zMax:
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)

			elif z == Z + 1 or z == Z - 1:
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)
			else:
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
	

		for x in range(xMin + 1, xMax):

			surface.surfaceMap[x][zMin].isOccupied = True
			surface.surfaceMap[x][zMax].isOccupied = True
			buildRoofRow(level, surface, x, zMin, zMax, Z, height + 4, materials.materialWall)
			if x == X:
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)
				level.setBlockAt(surface.toRealX(x),height + 5,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height + 5 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(x),height + 5,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height + 5 ,surface.toRealZ(zMax),materials.materialWall[1])
			else:
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)	

			level.setBlockAt(surface.toRealX(x),height + 4,surface.toRealZ(zMax),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(x),height + 4 ,surface.toRealZ(zMax),materials.materialWall[1])
			level.setBlockAt(surface.toRealX(x),height + 4,surface.toRealZ(zMin),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(x),height + 4 ,surface.toRealZ(zMin),materials.materialWall[1])

	else:
		for x in range(xMin,xMax + 1):
			surface.surfaceMap[x][zMin].isOccupied = True
			surface.surfaceMap[x][zMax].isOccupied = True

			if direction == "North" and x == X:
				buildColumn(level, surface, x, zMax, height, materials.materialWall, True, False)
				buildRoofColumn(level, surface, zMax, xMin, xMax, X, height + 3, materials.materialWall)
				buildRoofColumn(level, surface, zMax, xMin, xMax, X, height + 2, materials.materialWall)
				buildRoofColumn(level, surface, zMax, xMin, xMax, X, height + 1, materials.materialWall)
				level.setBlockAt(surface.toRealX(X),height + 4,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 4 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X),height + 5,surface.toRealZ(zMax),20)
				level.setBlockDataAt(surface.toRealX(X),height + 5 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X),height + 6,surface.toRealZ(zMax),20)
				level.setBlockDataAt(surface.toRealX(X),height + 6 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X),height + 7,surface.toRealZ(zMax),20)
				level.setBlockDataAt(surface.toRealX(X),height + 7 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X),height + 8,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 8 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X),height + 9,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 9 ,surface.toRealZ(zMax),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(X + 1),height + 4,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 4 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 5,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 5 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 6,surface.toRealZ(zMax),20)
				level.setBlockDataAt(surface.toRealX(X + 1),height + 6 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X + 1),height + 7,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 7 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 8,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 8 ,surface.toRealZ(zMax),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(X - 1),height + 4,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 4 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 5,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 5 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 6,surface.toRealZ(zMax),20)
				level.setBlockDataAt(surface.toRealX(X - 1),height + 6 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X - 1),height + 7,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 7 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 8,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 8 ,surface.toRealZ(zMax),materials.materialWall[1])

				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)

				buildRoofColumn(level, surface, zMin, xMin, xMax, X, height + 3, materials.materialWall)
				buildRoofColumn(level, surface, zMin, xMin, xMax, X, height + 2, materials.materialWall)
				buildRoofColumn(level, surface, zMin, xMin, xMax, X, height + 1, materials.materialWall)
				level.setBlockAt(surface.toRealX(X),height + 4,surface.toRealZ(zMin),41)
				level.setBlockDataAt(surface.toRealX(X),height + 4 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X),height + 5,surface.toRealZ(zMin),41)
				level.setBlockDataAt(surface.toRealX(X),height + 5 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X),height + 6,surface.toRealZ(zMin),41)
				level.setBlockDataAt(surface.toRealX(X),height + 6 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X),height + 7,surface.toRealZ(zMin),41)
				level.setBlockDataAt(surface.toRealX(X),height + 7 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X),height + 8,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 8 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X),height + 9,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 9 ,surface.toRealZ(zMin),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(X + 1),height + 4,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 4 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 5,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 5 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 6,surface.toRealZ(zMin),41)
				level.setBlockDataAt(surface.toRealX(X + 1),height + 6 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X + 1),height + 7,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 7 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 8,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 8 ,surface.toRealZ(zMin),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(X - 1),height + 4,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 4 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 5,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 5 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 6,surface.toRealZ(zMin),41)
				level.setBlockDataAt(surface.toRealX(X - 1),height + 6 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X - 1),height + 7,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 7 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 8,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 8 ,surface.toRealZ(zMin),materials.materialWall[1])

			elif direction == "South" and x == X:	
				buildColumn(level, surface, x, zMin, height, materials.materialWall, True, False)
				buildRoofColumn(level, surface, zMin, xMin, xMax, X, height + 3, materials.materialWall)
				buildRoofColumn(level, surface, zMin, xMin, xMax, X, height + 2, materials.materialWall)
				level.setBlockAt(surface.toRealX(X),height + 4,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 4 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X),height + 5,surface.toRealZ(zMin),20)
				level.setBlockDataAt(surface.toRealX(X),height + 5 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X),height + 6,surface.toRealZ(zMin),20)
				level.setBlockDataAt(surface.toRealX(X),height + 6 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X),height + 7,surface.toRealZ(zMin),20)
				level.setBlockDataAt(surface.toRealX(X),height + 7 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X),height + 8,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 8 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X),height + 9,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 9 ,surface.toRealZ(zMin),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(X + 1),height + 4,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 4 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 5,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 5 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 6,surface.toRealZ(zMin),20)
				level.setBlockDataAt(surface.toRealX(X + 1),height + 6 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X + 1),height + 7,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 7 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 8,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 8 ,surface.toRealZ(zMin),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(X - 1),height + 4,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 4 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 5,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 5 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 6,surface.toRealZ(zMin),20)
				level.setBlockDataAt(surface.toRealX(X - 1),height + 6 ,surface.toRealZ(zMin),0)
				level.setBlockAt(surface.toRealX(X - 1),height + 7,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 7 ,surface.toRealZ(zMin),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 8,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 8 ,surface.toRealZ(zMin),materials.materialWall[1])

				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
				buildRoofColumn(level, surface, zMax, xMin, xMax, X, height + 3, materials.materialWall)
				buildRoofColumn(level, surface, zMax, xMin, xMax, X, height + 2, materials.materialWall)
				buildRoofColumn(level, surface, zMax, xMin, xMax, X, height + 1, materials.materialWall)
				level.setBlockAt(surface.toRealX(X),height + 4,surface.toRealZ(zMax),41)
				level.setBlockDataAt(surface.toRealX(X),height + 4 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X),height + 5,surface.toRealZ(zMax),41)
				level.setBlockDataAt(surface.toRealX(X),height + 5 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X),height + 6,surface.toRealZ(zMax),41)
				level.setBlockDataAt(surface.toRealX(X),height + 6 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X),height + 7,surface.toRealZ(zMax),41)
				level.setBlockDataAt(surface.toRealX(X),height + 7 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X),height + 8,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 8 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X),height + 9,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X),height + 9 ,surface.toRealZ(zMax),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(X + 1),height + 4,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 4 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 5,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 5 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 6,surface.toRealZ(zMax),41)
				level.setBlockDataAt(surface.toRealX(X + 1),height + 6 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X + 1),height + 7,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 7 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X + 1),height + 8,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X + 1),height + 8 ,surface.toRealZ(zMax),materials.materialWall[1])

				level.setBlockAt(surface.toRealX(X - 1),height + 4,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 4 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 5,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 5 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 6,surface.toRealZ(zMax),41)
				level.setBlockDataAt(surface.toRealX(X - 1),height + 6 ,surface.toRealZ(zMax),0)
				level.setBlockAt(surface.toRealX(X - 1),height + 7,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 7 ,surface.toRealZ(zMax),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(X - 1),height + 8,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(X - 1),height + 8 ,surface.toRealZ(zMax),materials.materialWall[1])

			elif x == xMin or x == xMax:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)

			elif x == X + 1 or x == X - 1:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
			else:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)
	

		for z in range(zMin + 1, zMax):

			levelTerrain(level, surface, Point(xMin,z), height)
			levelTerrain(level, surface, Point(xMax,z), height)
			surface.surfaceMap[xMin][z].isOccupied = True
			surface.surfaceMap[xMax][z].isOccupied = True
			buildRoofColumn(level, surface, z, xMin, xMax, X, height + 4, materials.materialWall)
			if z == Z:
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)
				level.setBlockAt(surface.toRealX(xMin),height + 5,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height + 5 ,surface.toRealZ(z),materials.materialWall[1])
				level.setBlockAt(surface.toRealX(xMax),height + 5,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height + 5 ,surface.toRealZ(z),materials.materialWall[1])
			else:
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)	

			level.setBlockAt(surface.toRealX(xMax),height + 4,surface.toRealZ(z),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(xMax),height + 4 ,surface.toRealZ(z),materials.materialWall[1])
			level.setBlockAt(surface.toRealX(xMin),height + 4,surface.toRealZ(z),materials.materialWall[0])
			level.setBlockDataAt(surface.toRealX(xMin),height + 4 ,surface.toRealZ(z),materials.materialWall[1])
	
#Builds a hall with style similar to the houses and diferent roofs depending on True or False on plainRoof field
def buildHall(level, surface, X, Z, direction, height, materials, plainRoof):

	xMin = X - 6
	xMax = X + 6
	zMin = Z - 6
	zMax = Z + 6

	if surface.toRealX(xMin - 2) <= surface.xStart:
		print "Aborted construction of Big Building at ", X, Z 
		return 0
	
	if surface.toRealX(xMax + 2) >= surface.xEnd:
		print "Aborted construction of Big Building at ", X, Z 
		return 0
	
	if surface.toRealZ(zMin - 2) <= surface.zStart:
		print "Aborted construction of Big Building at ", X, Z 
		return 0
	
	if surface.toRealZ(zMax + 2) >= surface.zEnd:
		print "Aborted construction of Big Building at ", X, Z 
		return 0

	for x in range(xMin-2, xMax + 3):
		for z in range(zMin-2, zMax + 3):
			if x == xMax + 1 or x == xMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True
			if z == zMax + 1 or zMin - 1:
				levelTerrain(level, surface, Point(x,z), height)
				surface.surfaceMap[x][z].isOccupied = True	
	
	for x in range(xMin - 2,xMax + 3):
		for z in range(zMin - 2,zMax + 3):
			levelTerrain(level, surface, Point(x,z), height)
			level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z), materials.ground[0])
			level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z), materials.ground[1])

	height += 1

	if direction == "South":
		for x in range(xMin, xMax + 1):
			if x == xMax or x == xMin:
				buildColumn(level, surface, x, zMax, height, materials.materialFoundation, False, False)
				buildColumn(level, surface, x, zMin, height, materials.materialFoundation, False, False)
			elif x == X:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, True, False)
				surface.surfaceMap[x][zMax].isOccupied = True
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMax),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(x),height + y,surface.toRealZ(zMax),materials.materialFoundation[0])
					level.setBlockDataAt(surface.toRealX(x),height + y,surface.toRealZ(zMax),materials.materialFoundation[1])
			elif x == X + 1 or x == X - 1:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)
				surface.surfaceMap[x][zMax].isOccupied = True
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMax),materials.materialFoundation[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(x),height + y,surface.toRealZ(zMax),20)
					level.setBlockDataAt(surface.toRealX(x),height + y,surface.toRealZ(zMax),0)
			elif x == X + 3 or x == X - 3:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, True)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)
			else:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)


	if direction == "North":
		for x in range(xMin, xMax + 1):
			if x == xMax or x == xMin:
				buildColumn(level, surface, x, zMax, height, materials.materialFoundation, False, False)
				buildColumn(level, surface, x, zMin, height, materials.materialFoundation, False, False)
			elif x == X:
				buildColumn(level, surface, x, zMax, height, materials.materialWall, True, False)
				surface.surfaceMap[x][zMin].isOccupied = True
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMin),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(x),height + y,surface.toRealZ(zMin),materials.materialFoundation[0])
					level.setBlockDataAt(surface.toRealX(x),height + y,surface.toRealZ(zMin),materials.materialFoundation[1])
			elif x == X + 1 or x == X - 1:
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)
				surface.surfaceMap[x][zMin].isOccupied = True
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMin),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(x),height + y,surface.toRealZ(zMin),20)
					level.setBlockDataAt(surface.toRealX(x),height + y,surface.toRealZ(zMin),0)
			elif x == X + 3 or x == X - 3:
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, True)
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)
			else:
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)

	if direction == "North" or direction == "South":

		for z in range(zMin + 1,zMax):
			if z == Z:
				surface.surfaceMap[xMin][z].isOccupied = True
				level.setBlockAt(surface.toRealX(xMin),height,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height,surface.toRealZ(z),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(xMin),height + y,surface.toRealZ(z),materials.materialFoundation[0])
					level.setBlockDataAt(surface.toRealX(xMin),height + y,surface.toRealZ(z),materials.materialFoundation[1])

				surface.surfaceMap[xMax][z].isOccupied = True
				level.setBlockAt(surface.toRealX(xMax),height,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height,surface.toRealZ(z),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(xMax),height + y,surface.toRealZ(z),materials.materialFoundation[0])
					level.setBlockDataAt(surface.toRealX(xMax),height + y,surface.toRealZ(z),materials.materialFoundation[1])

			if z == Z + 1 or z == Z - 1:

				surface.surfaceMap[xMin][z].isOccupied = True
				level.setBlockAt(surface.toRealX(xMin),height,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height,surface.toRealZ(z),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(xMin),height + y,surface.toRealZ(z),20)
					level.setBlockDataAt(surface.toRealX(xMin),height + y,surface.toRealZ(z),0)

				surface.surfaceMap[xMax][z].isOccupied = True
				level.setBlockAt(surface.toRealX(xMax),height,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height,surface.toRealZ(z),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(xMax),height + y,surface.toRealZ(z),20)
					level.setBlockDataAt(surface.toRealX(xMax),height + y,surface.toRealZ(z),0)
			
			else:
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)		

	

	if direction == "East":
		for z in range(zMin, zMax + 1):
			if z == zMax or z == zMin:
				buildColumn(level, surface, xMax, z, height, materials.materialFoundation, False, False)
				buildColumn(level, surface, xMin, z, height, materials.materialFoundation, False, False)
			elif z == Z:
				buildColumn(level, surface, xMin, z, height, materials.materialWall, True, False)
				surface.surfaceMap[xMax][z].isOccupied = True
				level.setBlockAt(surface.toRealX(xMax),height,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height,surface.toRealZ(z),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(xMax),height + y,surface.toRealZ(z),materials.materialFoundation[0])
					level.setBlockDataAt(surface.toRealX(xMax),height + y,surface.toRealZ(z),materials.materialFoundation[1])
			elif z == Z + 1 or z == Z - 1:
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)
				surface.surfaceMap[xMax][z].isOccupied = True
				level.setBlockAt(surface.toRealX(xMax),height,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMax),height,surface.toRealZ(z),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(xMax),height + y,surface.toRealZ(z),20)
					level.setBlockDataAt(surface.toRealX(xMax),height + y,surface.toRealZ(z),0)
			elif z == Z + 3 or z == Z - 3:
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, True)
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
			else:
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)

	if direction == "West":
		for z in range(zMin, zMax + 1):
			if z == zMax or z == zMin:
				buildColumn(level, surface, xMax, z, height, materials.materialFoundation, False, False)
				buildColumn(level, surface, xMin, z, height, materials.materialFoundation, False, False)
			elif z == Z:
				buildColumn(level, surface, xMax, z, height, materials.materialWall, True, False)
				surface.surfaceMap[xMin][z].isOccupied = True
				level.setBlockAt(surface.toRealX(xMin),height,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height,surface.toRealZ(z),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(xMin),height + y,surface.toRealZ(z),materials.materialFoundation[0])
					level.setBlockDataAt(surface.toRealX(xMin),height + y,surface.toRealZ(z),materials.materialFoundation[1])
			elif z == Z + 1 or z == Z - 1:
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
				surface.surfaceMap[xMin][z].isOccupied = True
				level.setBlockAt(surface.toRealX(xMin),height,surface.toRealZ(z),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(xMin),height,surface.toRealZ(z),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(xMin),height + y,surface.toRealZ(z),20)
					level.setBlockDataAt(surface.toRealX(xMin),height + y,surface.toRealZ(z),0)
			elif z == Z + 3 or z == Z - 3:
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, True)
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)
			else:
				buildColumn(level, surface, xMax, z, height, materials.materialWall, False, False)
				buildColumn(level, surface, xMin, z, height, materials.materialWall, False, False)

	if direction == "East" or direction == "West":

		for x in range(xMin + 1,xMax):
			if x == X:
				surface.surfaceMap[x][zMin].isOccupied = True
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMin),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(x),height + y,surface.toRealZ(zMin),materials.materialFoundation[0])
					level.setBlockDataAt(surface.toRealX(x),height + y,surface.toRealZ(zMin),materials.materialFoundation[1])

				surface.surfaceMap[x][zMax].isOccupied = True
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMax),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(x),height + y,surface.toRealZ(zMax),materials.materialFoundation[0])
					level.setBlockDataAt(surface.toRealX(x),height + y,surface.toRealZ(zMax),materials.materialFoundation[1])

			elif x == X + 1 or x == X - 1:

				surface.surfaceMap[x][zMin].isOccupied = True
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMin),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMin),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(x),height + y,surface.toRealZ(zMin),20)
					level.setBlockDataAt(surface.toRealX(x),height + y,surface.toRealZ(zMin),0)

				surface.surfaceMap[x][zMax].isOccupied = True
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMax),materials.materialWall[0])
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMax),materials.materialWall[1])
				for y in range(1,4):
					level.setBlockAt(surface.toRealX(x),height + y,surface.toRealZ(zMax),20)
					level.setBlockDataAt(surface.toRealX(x),height + y,surface.toRealZ(zMax),0)
			else:
				buildColumn(level, surface, x, zMax, height, materials.materialWall, False, False)
				buildColumn(level, surface, x, zMin, height, materials.materialWall, False, False)


	if plainRoof:
		for x in range(xMin, xMax + 1):
			for z in range(zMin, zMax + 1):
				level.setBlockAt(surface.toRealX(x),height + 4,surface.toRealZ(z),materials.materialRoof[0])
				level.setBlockDataAt(surface.toRealX(x),height + 4,surface.toRealZ(z),materials.materialRoof[1])
				if x == xMin or x == xMax or z == zMin or z == zMax:
					if z % 3 == 0 or x % 3 == 0:
						level.setBlockAt(surface.toRealX(x),height + 5,surface.toRealZ(z),materials.materialRoof[0])
						level.setBlockDataAt(surface.toRealX(x),height + 5,surface.toRealZ(z),materials.materialRoof[1])
	else:
		counter = 0
		for x in range(xMin, X + 1):
			buildSquareRoof(level, surface, x, xMax - counter, zMin + counter, zMax - counter, height + counter + 4, materials.materialRoof)
			counter += 1
						

	return 1

#Builds a plain roof
def buildSquareRoof(level, surface, xMin, xMax, zMin, zMax, height, material):

	for x in range(xMin, xMax + 1):
		level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMax),material[0])
		level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMax),material[1])
		level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(zMin),material[0])
		level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(zMin),material[1])
		
	for z in range(zMin + 1, zMax):
		level.setBlockAt(surface.toRealX(xMax),height,surface.toRealZ(z),material[0])
		level.setBlockDataAt(surface.toRealX(xMax),height,surface.toRealZ(z),material[1])
		level.setBlockAt(surface.toRealX(xMin),height,surface.toRealZ(z),material[0])
		level.setBlockDataAt(surface.toRealX(xMin),height,surface.toRealZ(z),material[1])

#Builds a corral with a field near it
def buildBigFarm(level, surface, section, X, Z, direction, height, materials):

	buildCorral(level, surface, section, X, Z, materials.animal, section.materials.fences)

	if checkZ(surface, section, X + 7, Z, 9, 7):
		xMax = X + 11
		xMin = X + 7
		zMax = Z + 3
		zMin = Z - 3

		height = surface.surfaceMap[X][Z].height

		for x in range(xMin, xMax + 1):
			for z in range(zMin, zMax + 1):
				levelTerrain(level, surface, Point(x,z), height)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),60)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),0)
				surface.surfaceMap[x][z].isOccupied = True
				if z == zMin or z == zMax:
					level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z), materials.fences[0])
					level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z), materials.fences[1])
					if x == X:
						level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),107)
						level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),0)

				if x == xMin or x == xMax:
					level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z), materials.fences[0])
					level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z), materials.fences[1])
		level.setBlockAt(surface.toRealX(xMax-1),height+1,surface.toRealZ(zMax-1),118)
		level.setBlockDataAt(surface.toRealX(xMax-1),height+1,surface.toRealZ(zMax-1),0)

	elif checkZ(surface, section, X - 7, Z, 9, 7):
		xMax = X 
		xMin = X - 7
		zMax = Z + 2
		zMin = Z - 2

		height = surface.surfaceMap[X][Z].height

		for x in range(xMin, xMax + 1):
			for z in range(zMin, zMax + 1):
				levelTerrain(level, surface, Point(x,z), height)
				level.setBlockAt(surface.toRealX(x),height,surface.toRealZ(z),60)
				level.setBlockDataAt(surface.toRealX(x),height,surface.toRealZ(z),0)
				surface.surfaceMap[x][z].isOccupied = True
				if z == zMin or z == zMax:
					level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),materials.fences[0])
					level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),materials.fences[1])
					surface.surfaceMap[x][z].height += 25

				if x == xMin or x == xMax:
					level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),materials.fences[0])
					level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),materials.fences[1])
					surface.surfaceMap[x][z].height += 25
					if z == Z:
						level.setBlockAt(surface.toRealX(x),height+1,surface.toRealZ(z),107)
						level.setBlockDataAt(surface.toRealX(x),height+1,surface.toRealZ(z),0)
	
		level.setBlockAt(surface.toRealX(xMax-1),height+1,surface.toRealZ(zMax-1),118)
		level.setBlockDataAt(surface.toRealX(xMax-1),height+1,surface.toRealZ(zMax-1),0)						
	else:
		print "Couldn't build Farm"

#Tries to build on a big section a church, hall, landmark and big farm.
def buildBigSectionCityCell(level, surface, section, height):

	houses = 0
	biggestSubzone = getBiggestSubzone(surface, section)
	churchZone = biggestSubzone
	section.materials.ground = (43,0)
	print "Biggest Subzone: ", biggestSubzone
	if biggestSubzone == "North":
		churchPoint = getMidPoint(surface, section, "South")
		churchZone = "South"
		sizeXChurch = 13
		sizeZChurch = 17
		farmDirection = "East"
		farmPoint = getMidPoint(surface, section, "East")
		hallPoint = getMidPoint(surface, section, "North")
	elif biggestSubzone == "South":
		churchPoint = getMidPoint(surface, section, "North")
		churchZone = "North"
		sizeXChurch = 13
		sizeZChurch = 17
		farmDirection = "East"
		farmPoint = getMidPoint(surface, section, "East")
		hallPoint = getMidPoint(surface, section, "South")
	elif biggestSubzone == "East":
		churchPoint = getMidPoint(surface, section, "West")
		churchZone = "West"
		sizeXChurch = 17
		sizeZChurch = 13
		farmDirection = "North"
		farmPoint = getMidPoint(surface, section, "North")
		hallPoint = getMidPoint(surface, section, "East")
	elif biggestSubzone == "West":
		churchPoint = getMidPoint(surface, section, "East")
		churchZone = "East"
		sizeXChurch = 17
		sizeZChurch = 13
		farmDirection = "North"
		farmPoint = getMidPoint(surface, section, "North")
		hallPoint = getMidPoint(surface, section, "West")	

	if checkZ(surface, section, churchPoint.x, churchPoint.z, sizeXChurch, sizeZChurch):
		buildChurch(level, surface, churchPoint.x, churchPoint.z, churchZone, surface.surfaceMap[churchPoint.x][ churchPoint.z].height, section.materials)
		path = getAStarPath(surface, section.xMid, section.zMid, churchPoint.x,churchPoint.z)
		if path:
			buildPath(level, surface, path)
		houses += 1	
	else:
		print "No Church Builded"

	if checkZ(surface, section, hallPoint.x, hallPoint.z, 17, 17):
		buildHall(level, surface, hallPoint.x, hallPoint.z, biggestSubzone, surface.surfaceMap[hallPoint.x][hallPoint.z].height, section.materials,False)
		path = getAStarPath(surface, section.xMid, section.zMid, hallPoint.x, hallPoint.z)
		if path:
			buildPath(level, surface, path)	
		houses += 1	
	else:
		print "No Hall Builded"		

	if checkZ(surface, section,  farmPoint.x, farmPoint.z, 17, 17):
		buildBigFarm(level, surface, section, farmPoint.x, farmPoint.z, farmDirection, surface.surfaceMap[farmPoint.x][farmPoint.z].height, section.materials)		
	else:
		print "No Farmland built"
	return houses		


#Path functions. Taken from julos version of the  program

#A* algorithm
def getAStarPath(surface, xSource, zSource, xTarget, zTarget):
  openSet = []
  nodes = []
  for _ in range(surface.xLength):
    row = []
    for _ in range(surface.zLength):
      row.append(None)
    nodes.append(row)
  if surface.toRealX(xTarget) < surface.xStart:
      xTarget = 0
  if surface.toRealX(xTarget) > surface.xEnd:
      xTarget = surface.xLength -  1
  if surface.toRealZ(zTarget) < surface.zStart:
      zTarget = 0
  if surface.toRealZ(zTarget) > surface.zEnd:
      zTarget = surface.zEnd - 1

  targetNode = Node(surface, xTarget, zTarget, None)

  sourceNode = Node(surface, xSource, zSource, targetNode)
  sourceNode.gScore = 0
  sourceNode.fScore = sourceNode.hScore

  nodes[sourceNode.x][sourceNode.z] = sourceNode
  nodes[targetNode.x][targetNode.z] = targetNode

  heapq.heappush(openSet, (getPriorityScore(sourceNode.fScore, sourceNode.hScore), sourceNode))

  while openSet:
    currentNode = heapq.heappop(openSet)[1]
    currentNode.isOpen = False
    currentNode.isClosed = True

    if currentNode == targetNode:
      return reconstructPath(currentNode)

    for neighbourNode in getNeighbourNodes(surface, currentNode, nodes, targetNode):
      if neighbourNode.isClosed:
        continue
      tentativeGSCore = currentNode.gScore + getStepCost(surface, currentNode, neighbourNode)
      if (tentativeGSCore >= neighbourNode.gScore):
        continue
      neighbourNode.gScore = tentativeGSCore
      neighbourNode.fScore = tentativeGSCore + neighbourNode.hScore
      neighbourNode.cameFrom = currentNode
      if not neighbourNode.isOpen:
        neighbourNode.isOpen = True
        heapq.heappush(openSet, (getPriorityScore(neighbourNode.fScore, neighbourNode.hScore), neighbourNode))
      else:
        neighbourNodeIndex = getIndex(openSet, neighbourNode)
        openSet[neighbourNodeIndex] = (getPriorityScore(neighbourNode.fScore, neighbourNode.hScore), neighbourNode)
        heapq.heapify(openSet)
  return []

#Obtain indesx of neighbour node on open set
def getIndex(openSet, neighbourNode):
  for i, element in enumerate(openSet):
    if element[1] == neighbourNode:
      return i

#Gets the g Score of a point
def getPriorityScore(fScore, hScore):
  return fScore + hScore / float(10000)

#Gets neighbour nodes to a node
def getNeighbourNodes(surface, node, nodes, targetNode):
  neighbourNodes = []
  for x in range(node.x - 1, node.x + 2):
    if x < 0 or x >= surface.xLength:
      continue
    for z in range(node.z - 1, node.z + 2):
      if z < 0 or z >= surface.zLength:
        continue
      if x == node.x and z == node.z:
        continue
      if nodes[x][z] == None:
        nodes[x][z] = Node(surface, x, z, targetNode)
      neighbourNodes.append(nodes[x][z])
  return neighbourNodes

#Remakes a path from the instances traversed to reach the goal.
def reconstructPath(node):
  path = []
  currentNode = node
  path.append(Point(currentNode.x, currentNode.z))
  while currentNode.cameFrom != None:
    currentNode = currentNode.cameFrom
    path.append(Point(currentNode.x, currentNode.z))
  path.reverse()
  return path

#Heuristic function. Values avoiding changes on height and water
def getSimpleHeuristicCostEstimate(surface, node, targetNode):
  heightCost = 20
  xLength = abs(targetNode.x - node.x)
  zLength = abs(targetNode.z - node.z)
  yLength = abs(targetNode.y - node.y)
  longHorizontalLength = max(xLength, zLength)
  shortHorizontalLength = min(xLength, zLength)
  minimumDistance = shortHorizontalLength * 14 + (longHorizontalLength - shortHorizontalLength) * 10
  cost = minimumDistance + yLength * heightCost
  return cost

#Action cost. Differentiates diagonal and horizontal steps
def getStepCost(surface, node, neighbourNode):
  heightCost = 20
  waterCost = 40
  isWater = 0
  if surface.surfaceMap[neighbourNode.x][neighbourNode.z].isWater:
    isWater = 1
  xLength = abs(neighbourNode.x - node.x)
  zLength = abs(neighbourNode.z - node.z)
  yLength = abs(neighbourNode.y - node.y)
  if xLength + zLength == 2:
    return 14 + yLength * yLength * heightCost * 2 + isWater * waterCost # Diagonal step
  return 10 + yLength * yLength * heightCost + isWater * waterCost # Normal step

#Gets nearest section to a section different to itself
def getNearest(sections, section):

	nearest = 999999
	nearestSection = section
	for section2 in sections:
		if section != section2:
			xDistance = abs(section.xMid - section2.xMid)
			zDistance = abs(section.zMid - section2.zMid)
			yDistance = abs(section.averageHeight - section2.averageHeight)
			horizontalDist = sqrt(xDistance * xDistance + zDistance * zDistance)
			verticalDist = sqrt(horizontalDist * horizontalDist + yDistance * yDistance)
			if verticalDist < nearest:
				nearest = verticalDist
				nearestSection = section2
	return nearestSection
