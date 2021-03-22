import glob
import os
import shutil
from pathlib import Path
from tkinter import Tk, filedialog
from zipfile import ZipFile

from PIL import Image
from progressbar import ProgressBar

root = Tk()
root.withdraw()

path = Path(filedialog.askdirectory())
print('Creating list of comics to search.')
file_list = [str(pp) for pp in path.glob("**/*.cbz")]
jpg_list = []


def Contents():
    contents = [os.path.join(temppath, f) for f in os.listdir(temppath)]
    return contents


def convert_image(image_path, image_type):

    im = Image.open(image_path)
    im = im.convert('RGB')
    image_name = image.replace('.jpg', '.webp')

    if image_type == 'jpg' or image_type == 'png':
        im.save(f"{image_name}", 'webp')
    else:
        print('Images are not of type jpg or png.')


pbar = ProgressBar()
print('Searching folder and subfolders for comics with jpg images.')
for file in pbar(file_list):
    MyZip = ZipFile(file)
    zipcontents = ZipFile.namelist(MyZip)
    if any('.jpg' in s for s in zipcontents):
        jpg_list.append(file)

print('Found ', str(len(jpg_list)), ' out of ', str(
    len(file_list)), ' comics with jpg images.')

for cbz in jpg_list:
    splitpath = os.path.split(cbz)
    print('Converting ', splitpath[1])
    MyZip = ZipFile(cbz)
    NewZip = cbz + '.new'
    temppath = os.path.join(splitpath[0], 'temp')
    MyZip.extractall(path=temppath)

    # convert to webp
    images = [str(pp) for pp in Path(temppath).glob("**/*.jpg")]
    if len(images) == 0:
        print('No images to convert')
        continue
    print('Converting Images')
    pbar = ProgressBar()
    for image in pbar(images):
        if image.endswith('jpg') or image.endswith('jpeg'):
            convert_image(image, 'jpg')
    # delete original images
    for file in images:
        path_to_file = os.path.join(temppath, file)
        os.remove(path_to_file)

    contents = Contents()
    with ZipFile(NewZip, 'w') as archive:
        for file in contents:
            archive.write(file, os.path.basename(file))

    shutil.rmtree(temppath)
    shutil.move(NewZip, cbz)