import argparse
import contextlib
import os
import shelve
import shutil
import time
import re
from stat import S_IWUSR, S_IWGRP, S_IWOTH
from pathlib import Path
from tkinter import Tk, filedialog
from zipfile import ZipFile
from multiprocessing import Pool

import filetype
from PIL import Image, ImageFile
from tqdm import tqdm
from tqdm.contrib.concurrent import process_map
from unrar import rarfile

ImageFile.LOAD_TRUNCATED_IMAGES=True
my_parser = argparse.ArgumentParser(
    description='Find and convert comics from jpg to webp')

my_parser.add_argument('-b', '--backup', dest='backup',
                       help='Make backup of each cbz to a specified folder', action='store_true')
my_parser.add_argument('-s', '--small', dest='small',
                       help='Keep smaller file', action='store_true')
my_parser.add_argument('-m', '--maxsize', dest='maxsize',
                       help='Keep smaller file', action='store')
my_parser.add_argument('-nm', '--nomon', dest='nomon',
                       help='Use scripted with no monitor requirement.  Requires --path, --pathdone, and --pathbad during initial run.', action='store_true')
my_parser.add_argument('-p', '--path', 
                       help='Set absolute path for comics to be processed')
my_parser.add_argument('-pd', '--pathdone', 
                       help='Set path for where to store processed comics')
my_parser.add_argument('-pb', '--pathbad', 
                       help='Set path for where to store corrupt comics')
args = my_parser.parse_args()

args = my_parser.parse_args()
backup = args.backup
small = args.small
nomon = args.nomon
argslist = [args.path, args.pathdone, args.pathbad]

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

except KeyError:
    if args.nomon and not all(argslist):
        my_parser.error('The first use of --nomon requires you to set --path, --pathdone, and --pathbad')
    with shelve.open('cpaths', 'c') as shelf:
        if not args.nomon:
            print('Select folder to scan for eComics...')
            shelf["path"] = filedialog.askdirectory()
            print('Select folder to place converted eComics...')
            shelf["pathdone"] = filedialog.askdirectory()
            print('Select folder to place corrupted eComics...')
            shelf["pathbad"] = filedialog.askdirectory()
        if args.nomon:
            shelf["path"] = args.path
            shelf["pathdone"] = args.pathdone
            shelf["pathbad"] = args.pathbad
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
webp_list = []
badfiles = []


def winapi_path(dos_path):
    wpath = os.path.abspath(dos_path)
    if wpath.startswith("\\\\"):
        return f"\\\\?\\UNC\\{wpath[2:]}"
    return f"\\\\?\\{wpath}"


def remove_exif(image_name):
    im = Image.open(image_name)
    if not im.getexif():
        return
    data = list(im.getdata())
    image_without_exif = Image.new(im.mode, im.size)
    image_without_exif.putdata(data)
    image_without_exif.save(image_name)

def convert_image(image_path, image_type):
    try:
        im = Image.open(image_path)
        im = im.convert('RGB')
        if maxsize != '':
            im.thumbnail(maxsize)
        image_name = image_path.replace(image_type, 'webp')
        with contextlib.suppress(Exception):
            im.save(f"{image_name}", 'webp')
        return True
    except Exception:
        return False

def loop_images(images, arcname):
    for image in tqdm(images, desc='Converting Images', colour='yellow', leave=False, postfix=arcname):
        # remove_exif(image)
        if image.endswith('jpg'):
            state = convert_image(image, 'jpg')

        if image.endswith('jpeg'):
            state = convert_image(image, 'jpeg')

        if image.endswith('png'):
            state = convert_image(image, 'png')

        if image.endswith('webp'):
            state = convert_image(image, 'webp')
        if state == False:
            break
    return state

def isimg(zipcontents):
    ziplength = len(zipcontents) - 1
    extensions = ('.jpg', '.jpeg', '.png', '.JPG',
                  '.JPEG', '.PNG', '.webp', '.WEBP')
    return any(
        zipcontents[i].endswith(extensions)
        for i in range(ziplength)
    )


# Check Files for JPG, PNG, or WEBP images
def check_zip(jpl, bf, f):
    try:
        with ZipFile(f) as MyZip:
            zipcontents = MyZip.namelist()
        if isimg(zipcontents):
            jpl.append(f)
        else:
            bf.append(f)
    except Exception:
        bf.append(f)
    return jpl, bf, f


def check_rar(jpl, bf, f):
    try:
        with rarfile.RarFile(f) as MyRar:
            rarcontents = MyRar.namelist()
        if isimg(rarcontents):
            jpl.append(f)
        else:
            bf.append(f)
    except Exception:
        bf.append(f)
    return jpl, bf, f


def smaller(_arc, nZip):
    if os.path.getsize(nZip) < os.path.getsize(_arc):
        if _arc.endswith('cbr'):
            _arc = _arc.replace('.cbr', '.cbz')
        if _arc.endswith('rar'):
            _arc = _arc.replace('.rar', '.cbz')
        shutil.move(nZip, _arc)
    else:
        os.remove(nZip)
    return arc


def larger(_conv, _done, _arc, nZip):
    os.remove(_arc)
    if _arc.endswith('cbr'):
        _arc = _arc.replace('.cbr', '.cbz')
    if _arc.endswith('rar'):
        _arc = _arc.replace('.rar', '.cbz')
    _arc = _arc.replace(_conv, _done)
    shutil.move(nZip, _arc)


def imgs(tpath):
    jpgimages = [str(pp) for pp in Path(tpath).glob("**/*.jpg")]
    jpegimages = [str(pp) for pp in Path(tpath).glob("**/*.jpeg")]
    pngimages = [str(pp) for pp in Path(tpath).glob("**/*.png")]
    webpimages = [str(pp) for pp in Path(tpath).glob("**/*.webp")]
    return jpgimages + pngimages + jpegimages + webpimages


def paths(_arc):
    _splitpath = os.path.split(_arc)
    _temppath = winapi_path(os.path.join(_splitpath[0], 'temp'))
    return _splitpath, _temppath


def extract_zip(_arc, tpath):
    purgelist = ['zsou-nerd', 'zzz-innerdemons',
                 'zzz-mephisto', 'zzzzz', 'zwater', 'zzztol']
    MyArc = ZipFile(arc)
    nZip = (
        f'{_arc}.new'
        if _arc.endswith('cbz')
        else re.sub(r'.{4}$', '.cbz', _arc) + '.new'
    )
    with MyArc as zf:
        for member in tqdm(zf.namelist(), desc='Extracting', colour='blue', leave=False):
            with contextlib.suppress(Exception):
                if all(s not in member.lower() for s in purgelist):
                    zf.extract(member, tpath)
    return nZip


def extract_rar(_arc, spath, tpath):
    purgelist = ['zsou-nerd', 'zzz-innerdemons',
                 'zzz-mephisto', 'zzzzz', 'zwater', 'zzztol']
    MyNewRar = rarfile.RarFile(_arc)
    nZip = (
        f'{_arc}.new'
        if _arc.endswith('cbz')
        else re.sub(r'.{4}$', '.cbz', _arc) + '.new'
    )
    rarpath = os.path.join(spath[0], 'temp')
    os.mkdir(rarpath)
    with MyNewRar as zf:
        for member in tqdm(zf.namelist(), desc='Extracting', colour='blue', leave=False):
            with contextlib.suppress(Exception):
                if all(s not in member.lower() for s in purgelist):
                    zf.extract(member, path=tpath)
    return nZip


def lower(r, fs):
    for f in fs:
        if f.startswith('._'):
            os.remove(os.path.join(r, f))
        elif f.endswith('JPG') or f.endswith('JPEG'):
            os.rename(os.path.join(r, f), os.path.join(r, f.lower()))


def create_arc(tpath, _arc):
    for r, _, fs in os.walk(tpath):
        for f in tqdm(fs, desc='Compressing', colour='cyan', leave=False):
            f = os.path.join(r, f)
            _arc.write(f, os.path.relpath(f, tpath))

def corrupt(conv, bad, badfiles):
    if len(badfiles) > 0:
        print('Moving ', len(badfiles), ' bad archives to "Bad Files":\n')
        for zfile in badfiles:
            nfile = zfile.replace(conv, bad)
            shutil.move(zfile, nfile)
    badfiles = []

for file in tqdm(file_list, desc='Searching comics', colour='green'):
    ftype = (filetype.guess(file)).mime
    if ftype == 'application/zip':
        jpg_list, badfiles, file = check_zip(
            jpg_list, badfiles, file)
    if ftype == 'application/x-rar-compressed':
        jpg_list, badfiles, file = check_rar(
            jpg_list, badfiles, file)

corrupt(conv, bad, badfiles)

print(
    'Found ',
    len(jpg_list),
    ' comics with images out of ',
    len(file_list),
    ' total comics.',
)


# Process Archives in jpg_list
for arc in tqdm(jpg_list, desc='All Files', colour='green'):
    splitpath, temppath = paths(arc)
    ftype = (filetype.guess(arc)).mime
    if ftype == 'application/zip':
        NewZip = extract_zip(arc, temppath)
    if ftype == 'application/x-rar-compressed':
        NewZip = extract_rar(arc, splitpath, temppath)
    for root, directory, files in os.walk(temppath):
        lower(root, files)

    # convert to webp
    images = imgs(temppath)
    if not images:
        print('No images to convert')
        # shutil.rmtree(temppath)
        continue
    arcname = os.path.basename(arc).replace('.', ' ').split(" (", 1)[0]    
    state = loop_images(images, arcname)
    
    # delete original images
    ext = ('.jpg', '.jpeg', '.png', '.JPG',
           '.JPEG', '.PNG')
    for file in images:
        if file.endswith(ext):
            path_to_file = os.path.join(temppath, file)
            os.chmod(path_to_file, S_IWUSR|S_IWGRP|S_IWOTH)
            os.remove(path_to_file)

    if state:
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
    else:
        badfiles.append(arc)
        corrupt(conv, bad, badfiles)
    os.chmod(temppath, S_IWUSR|S_IWGRP|S_IWOTH)
    shutil.rmtree(temppath)
    time.sleep(3)
    # make out loop stay in a single tqdm line
    print("\033[A\033[K\033[A\033[K\033[A")
