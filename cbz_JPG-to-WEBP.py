import argparse
import contextlib
import glob
import os
import shutil
import time
import shelve
import sys
from pathlib import Path
from tkinter import Tk, filedialog
from zipfile import ZipFile

from PIL import Image
from tqdm import tqdm
from unrar import rarfile

my_parser = argparse.ArgumentParser(
    description='Find and convert comics from jpg to webp')

my_parser.add_argument('-b', '--backup', dest='backup',
                       help='Make backup of each cbz to a specified folder', action='store_true')
my_parser.add_argument('-s', '--small', dest='small',
                       help='Keep smaller file', action='store_true')
my_parser.add_argument('-m', '--maxsize', dest='maxsize',
                       help='Keep smaller file', action='store')                       

args = my_parser.parse_args()
backup = args.backup
small = args.small
maxsize = ''
with contextlib.suppress(Exception):
    maxsize = (int(args.maxsize), int(args.maxsize))
Image.MAX_IMAGE_PIXELS = None
root = Tk()
root.withdraw()

try:
    with shelve.open('cpaths', 'c') as shelf:
        path = shelf["path"]
        pathdone = shelf["pathdone"]
        pathbad = shelf["pathbad"]

except Exception:
    with shelve.open('cpaths', 'c') as shelf:
        print('Select folder to scan for eComics...')
        shelf["path"] = filedialog.askdirectory()
        print('Select folder to place converted eComics...')
        shelf["pathdone"] = filedialog.askdirectory()
        print('Select folder to place corrupted eComics...')
        shelf["pathbad"] = filedialog.askdirectory()
        path = shelf["path"]
        pathdone = shelf["pathdone"]
        pathbad = shelf["pathbad"]

path = Path(path)
pathdone = Path(pathdone)
pathbad = Path(pathbad)
conv = os.path.basename(os.path.normpath(path))
done = os.path.basename(os.path.normpath(pathdone))
bad = os.path.basename(os.path.normpath(pathbad))

if backup:
    print('Select folder to store backups...')
    bupath = Path(filedialog.askdirectory())
print('Creating list of comics to search.')
cbz_list = [str(pp) for pp in path.glob("**/*.cbz")]
cbr_list = [str(pp) for pp in path.glob("**/*.cbr")]
rar_list = [str(pp) for pp in path.glob("**/*.rar")]
zip_list = [str(pp) for pp in path.glob("**/*.zip")]
file_list = cbr_list + cbz_list + rar_list + zip_list
jpg_list = []
badfiles = []
nojpg = []


def Contents():
    return [winapi_path(os.path.join(temppath, f)) for f in os.listdir(temppath)]


def winapi_path(dos_path, encoding=None):
    path = os.path.abspath(dos_path)
    if path.startswith(u"\\\\"):
        return f"\\\\?\\UNC\\{path[2:]}"
    return f"\\\\?\\{path}"

def convert_image(image_path, image_type):

    try:
        im = Image.open(image_path)
        im = im.convert('RGB')
    except Exception:
        return

    image_name = image_path.replace(image_type, 'webp')
    
    if image_type in ['jpg', 'png', 'jpeg']:
        try:
            if maxsize != '':
                im.thumbnail(maxsize)
            im.save(f"{image_name}", 'webp')
        except Exception:
            return
    else:
        print('Images are not of type jpg or png.')
    
def isjpg(zipcontents):
    ziplength = len(zipcontents) - 1
    extensions = ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')
    return any(
        zipcontents[i].endswith(extensions)
        for i in range(ziplength)
    )

#Check Files for JPG or PNG images
def check_zip(jpg_list, badfiles, nojpg, isjpg, file):
    try:
        with ZipFile(file) as MyZip:
            zipcontents = MyZip.namelist()
            if isjpg(zipcontents):
                jpg_list.append(file)
            else:
                nojpg.append(file)
    except Exception:
        try:
            with rarfile.RarFile(file) as MyRar:
                rarcontents = MyRar.namelist()
                if isjpg(rarcontents):
                    renfile = file.replace(".cbz", ".cbr")
                    jpg_list.append(renfile)
                    shutil.move(file, renfile)
                else:
                    nojpg.append(file)
        except (rarfile.BadRarFile):
            badfiles.append(file)
        except Exception:
            pass
    

def check_rar(jpg_list, badfiles, nojpg, isjpg, file):
    try:
        with rarfile.RarFile(file) as MyRar:
            rarcontents = MyRar.namelist()
            if isjpg(rarcontents):
                jpg_list.append(file)
            else:
                nojpg.append(file)
    except (rarfile.BadRarFile):
        badfiles.append(file)
    except Exception:
        pass

def smaller(arc, NewZip):
    if os.path.getsize(NewZip) < os.path.getsize(arc):
        if arc.endswith('cbr'):
            arc = arc.replace('.cbr', '.cbz')
        if arc.endswith('rar'):
            arc = arc.replace('.rar', '.cbz')
        shutil.move(NewZip, arc)
    else:
        os.remove(NewZip)
    return arc

def larger(conv, done, arc, NewZip):
    os.remove(arc)
    if arc.endswith('cbr'):
        arc = arc.replace('.cbr', '.cbz')
    if arc.endswith('rar'):
        arc = arc.replace('.rar', '.cbz')
    arc = arc.replace(conv, done)
    shutil.move(NewZip, arc)

def imgs(temppath):
    jpgimages = [str(pp) for pp in Path(temppath).glob("**/*.jpg")]
    jpegimages = [str(pp) for pp in Path(temppath).glob("**/*.jpeg")]
    pngimages = [str(pp) for pp in Path(temppath).glob("**/*.png")]
    return jpgimages + pngimages + jpegimages

def paths(winapi_path, arc):
    splitpath = os.path.split(arc)
    temppath = winapi_path(os.path.join(splitpath[0], 'temp'))
    return splitpath,temppath

def extract_zip(arc, temppath):
    MyArc = ZipFile(arc)
    NewZip = f'{arc}.new'
    with MyArc as zf:
        for member in tqdm(zf.namelist(), desc='Extracting', colour='blue', leave=False):
            with contextlib.suppress(Exception):
                zf.extract(member, temppath)
    return NewZip

def extract_rar(arc, splitpath, temppath):
    MyNewRar = rarfile.RarFile(arc)
    if arc.endswith('cbr'):
        NewZip = arc.replace('.cbr', '.cbz') + '.new'
    if arc.endswith('rar'):
        NewZip = arc.replace('.rar', '.cbz') + '.new'
    rarpath = os.path.join(splitpath[0], 'temp')
    os.mkdir(rarpath)
    with MyNewRar as zf:
        for member in tqdm(zf.namelist(), desc='Extracting', colour='blue', leave=False):
            with contextlib.suppress(Exception):
                zf.extract(member, path=temppath)
    return NewZip

def lower(root, files):
    for file in files:
        if file.startswith('._'):
            os.remove(os.path.join(root, file))
        elif file.endswith('JPG') or file.endswith('JPEG'):
            os.rename(os.path.join(root, file), os.path.join(root, file.lower()))

def create_arc(temppath, archive):
    for root, _, files in os.walk(temppath):
        for file in tqdm(files, desc='Compressing', colour='cyan', leave=False):
            f = os.path.join(root, file)
            archive.write(f, os.path.relpath(f, temppath))

for file in tqdm(file_list, desc='Searching comics', colour='green'):
    if ('.cbz' in file) or ('.zip' in file):
        check_zip(jpg_list, badfiles, nojpg, isjpg, file)

    if ('.cbr' in file) or ('.rar' in file):
        check_rar(jpg_list, badfiles, nojpg, isjpg, file)


if len(badfiles) > 0:
    print('Moving ', len(badfiles), ' bad archives to "Bad Files":\n')
    for zfile in badfiles:
        nfile = zfile.replace(conv, bad)
        shutil.move(zfile, nfile)
badfiles = []

if len(nojpg) > 0:
    print('Moving ', len(nojpg), ' comics to complete folder.')
    for zfile in nojpg:
        nfile = zfile.replace(conv, done)
        shutil.move(zfile, nfile)

print(
    'Found ',
    len(jpg_list),
    ' out of ',
    len(file_list),
    ' comics with jpg images.',
)


#Process Archives in jpg_list
for arc in tqdm(jpg_list, desc='All Files', colour='green'):
    splitpath, temppath = paths(winapi_path, arc)
    if arc.endswith('cbz') or arc.endswith('zip'):
        NewZip = extract_zip(arc, temppath)
    if arc.endswith('cbr') or arc.endswith('rar'):
        NewZip = extract_rar(arc, splitpath, temppath)
    for root, directory, files in os.walk(temppath):
        lower(root, files)

    # convert to webp
    images = imgs(temppath)
    if not images:
        print('No images to convert')
        #shutil.rmtree(temppath)
        continue
    for image in tqdm(images, desc='Converting Images', colour='yellow', leave=False):
        if image.endswith('jpg'):
            convert_image(image, 'jpg')

        if image.endswith('jpeg'):
            convert_image(image, 'jpeg')

        if image.endswith('png'):
            convert_image(image, 'png')

    # delete original images
    for file in images:
        path_to_file = os.path.join(temppath, file)
        os.remove(path_to_file)

    #contents = Contents()
    with ZipFile(NewZip, 'w') as archive:
        create_arc(temppath, archive)

    print('\nCleaning up...')
    if backup:
        print('Saving backup of ', splitpath[1])
        shutil.copy2(arc, os.path.join(bupath, splitpath[1]))

    if small:
        arc = smaller(arc, NewZip)
    else:
        larger(conv, done, arc, NewZip)

    shutil.rmtree(temppath)
    time.sleep(3)
    print("\033[A\033[K\033[A\033[K\033[A") #make out loop stay in a single tqdm line