import argparse
import contextlib
import os
import shutil
import time
import shelve
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

except KeyError:
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


def winapi_path(dos_path):
    wpath = os.path.abspath(dos_path)
    if wpath.startswith("\\\\"):
        return f"\\\\?\\UNC\\{wpath[2:]}"
    return f"\\\\?\\{wpath}"

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
def check_zip(jpl, bf, noj, f):
    try:
        with ZipFile(f) as MyZip:
            zipcontents = MyZip.namelist()
        if isjpg(zipcontents):
            jpl.append(f)
        else:
            noj.append(f)
    except Exception:
        try:
            with rarfile.RarFile(f) as MyRar:
                rarcontents = MyRar.namelist()
            if isjpg(rarcontents):
                renfile = f.replace(".cbz", ".cbr")
                jpl.append(renfile)
                os.rename(f, renfile)
            else:
                noj.append(f)
        except rarfile.BadRarFile:
            bf.append(f)
        except Exception:
            pass
    return jpl, bf, noj, f

def check_rar(jpl, bf, noj, f):
    try:
        with rarfile.RarFile(f) as MyRar:
            rarcontents = MyRar.namelist()
        if isjpg(rarcontents):
            jpl.append(f)
        else:
            nojpg.append(f)
    except rarfile.BadRarFile:
        try:
            with ZipFile(f) as MyZip:
                zipcontents = MyZip.namelist()
            if isjpg(zipcontents):
                renfile = f.replace(".cbr", ".cbz")
                jpl.append(renfile)
                os.rename(f, renfile)
            else:
                noj.append(f)
        except Exception:
            badfiles.append(f)
    return jpl, bf, noj, f

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
    return jpgimages + pngimages + jpegimages

def paths(_arc):
    _splitpath = os.path.split(_arc)
    _temppath = winapi_path(os.path.join(_splitpath[0], 'temp'))
    return _splitpath,_temppath

def extract_zip(_arc, tpath):
    purgelist = ['zsou-nerd', 'zzz-innerdemons', 'zzz-mephisto', 'zzzzz', 'zwater', 'zzztol']
    MyArc = ZipFile(arc)
    nZip = f'{_arc}.new'
    with MyArc as zf:
        for member in tqdm(zf.namelist(), desc='Extracting', colour='blue', leave=False):
            with contextlib.suppress(Exception):
                if all(s not in member.lower() for s in purgelist):
                    zf.extract(member, tpath)
    return nZip

def extract_rar(_arc, spath, tpath):
    purgelist = ['zsou-nerd', 'zzz-innerdemons', 'zzz-mephisto', 'zzzzz', 'zwater', 'zzztol']
    MyNewRar = rarfile.RarFile(_arc)
    if _arc.endswith('cbr'):
        nZip = _arc.replace('.cbr', '.cbz') + '.new'
    if _arc.endswith('rar'):
        nZip = _arc.replace('.rar', '.cbz') + '.new'
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

for file in tqdm(file_list, desc='Searching comics', colour='green'):
    if ('.cbz' in file) or ('.zip' in file):
        jpg_list, badfiles, nojpg, file = check_zip(jpg_list, badfiles, nojpg, file)
    if ('.cbr' in file) or ('.rar' in file):
        jpg_list, badfiles, nojpg, file = check_rar(jpg_list, badfiles, nojpg, file)

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
    splitpath, temppath = paths(arc)
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
