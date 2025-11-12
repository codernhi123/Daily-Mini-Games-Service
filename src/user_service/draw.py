# draw.py
# CMPT 276
# Nov. 29, 2022
# Version 2: Implementation of draw.py
# Other solutions are possible

import cmpt276image
import random

def recolor_image(img,color):
  '''
  Input parameters:
    img - 2d array of RGB values
    color -  represented as a list with three values [R,G,B]
       
  Returns: a new 2d array of RGB values
    with the colored image of img. Any non-white is colored
  '''
  height = len(img)   # Rows
  width = len(img[0]) # Columns
  
  result = cmpt276image.get_white_image(width, height)
  
  for row in range(0,height):
    for col in range(0,width):
      if img[row][col][0] < 230 or \
         img[row][col][1] < 230 or \
         img[row][col][2] < 230:   # V2: Test for non-white
        result[row][col] = color
  return result

def mirror(img):
  '''
  Input parameters:
    img - 2d array of RGB values
       
  Returns: a new 2d array of RGB values
    with the mirrored image of img     
  '''
  height = len(img)    # Rows
  width = len(img[0])  # Columns
   
  # Create a 3d array to store the result
  result = cmpt276image.get_white_image(width, height)
    
  for row in range(height):
      for col in range(width):
          result[row][col][0] = img[row][width-col-1][0]
          result[row][col][1] = img[row][width-col-1][1]
          result[row][col][2] = img[row][width-col-1][2]  
  return result

def minify(img):
  '''
  Input parameters: img - 2d array of RGB values
  Returns: a new 2d list of RGB values
        of the original image, half in both width and height
  '''
    
  width = len(img[0])
  height = len(img)
  resultWidth = width//2
  resultHeight = height//2
    
  # Create a 3d array to store the result
  result = cmpt276image.get_black_image(resultWidth, resultHeight)
    
  for row in range(0, height, 2):
    for col in range(0, width, 2):   
      # Each pixel in the result image use the the average
      # colour of the 2x2 pixels from the original image
      # (i.e. the pixel itself in row,col and pixels in
      # row,col+1  -- row+1,col -- row+1, col+1  
      sumR = 0
      sumG = 0
      sumB = 0
      for r in range(row, row+2):     # r will be row and row+1
        for c in range(col, col+2):   # c will be col and col+1
          sumR += img[r][c][0]
          sumG += img[r][c][1]
          sumB += img[r][c][2]
          # Set the RGB values in the result img
      result[row//2][col//2][0] = sumR//4
      result[row//2][col//2][1] = sumG//4
      result[row//2][col//2][2] = sumB//4
  return result

def draw_item(canvas,item,r,c):
  '''
  Input parameters:
    canvas - 2d array of RGB values
    item - 2d array of RGB values
    r - row value
    c - column value

    The (r,c) position is assumed to be within the
    canvas and so that the item image fits in the canvas
       
  Returns: 2d array of RGB values
    Including the non-white part of the item image
    in the original canvas, so that the top left corner of item
    is positioned at r,c within the canvas

    In this version, canvas is modified directly and also returned
  '''
  height_item = len(item) # Rows
  width_item = len(item[0]) # Columns
  
  for row in range(0,height_item):
    for col in range(0,width_item):
      if item[row][col][0] < 230 or \
         item[row][col][1] < 230 or \
         item[row][col][2] < 230:   # V2: Test for non-white
        canvas[r+row][c+col] = item[row][col]
  return canvas

def distribute_items(canvas,item,n):
  '''
  Input parameters:
    canvas - 2d array of RGB values
    item - 2d array of RGB values
    n - number of times the item image is to be "placed" in the canvas
       
  Returns: 2d array of RGB values
    Including n copies of the non-white part of the item image,
    each copy placed so that the top left corner of item
    is positioned in a random position within the canvas

    In this version, canvas is modified directly and also returned   
  '''
  # Get size of canvas
  height_canvas = len(canvas) 
  width_canvas = len(canvas[0])

  # Get size of item
  height_item = len(item)
  width_item = len(item[0])
  
  # The item is included n times
  for i in range(n):
    # Get n random positions
    r = random.randint(0,height_canvas-height_item)
    c = random.randint(0,width_canvas-width_item)
    
    # Draw the items
    canvas = draw_item(canvas,item,r,c)
  return canvas