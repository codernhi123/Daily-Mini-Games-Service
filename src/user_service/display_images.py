import cmpt276image as cmpt
import draw
import sys
import json
import pygame
import time
cmpt.init()
import csv
import random

names = "images.csv"
word_list = []

# with open(names) as f:
#     csvreader = csv.reader(f)
#     for row in csvreader:
#         word = row[0]
#         word_list.append(word)
#         random.shuffle(word_list)
#         new_word = word_list[random.randint(0, 6)]

def display_level(level_data):
    width = 600
    height = 500
    canvas = cmpt.get_white_image(width, height)

    for process_img in level_data['images']:
        try:
            filename = process_img['filename']
            img = cmpt.get_image(f"images/{filename}")

            if process_img.get('recolor'):
                img = draw.recolor_image(img, process_img['recolor'])

            if process_img.get('mirror'):
                img = draw.mirror(img)

            if process_img.get('minify'):
                img = draw.minify(img)

            canvas = draw.distribute_items(canvas, img, 1)

        except Exception as e:
            print(f"Error loading image {process_img['filename']}: {e}")
            continue
    
    cmpt.show_image(canvas)
    print("Displaying image for 5 seconds...")
    time.sleep(5)

    pygame.quit()
    print("Display complete")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python display_images.py '<json_data>'")
        sys.exit(1)

    try:
        level_data_json = sys.argv[1]
        level_data = json.loads(level_data_json)
        display_level(level_data)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)



            



    