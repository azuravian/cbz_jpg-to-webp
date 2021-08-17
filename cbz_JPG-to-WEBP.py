import argparse
import glob
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
maxsize = (int(args.maxsize), int(args.maxsize))

Image.MAX_IMAGE_PIXELS = None
root = Tk()
root.withdraw()

try:
    with shelve.open('cpaths', 'c') as shelf:
        path = shelf["path"]
        pathdone = shelf["pathdone"]
        pathbad = shelf["pathbad"]
    
except:
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
        return u"\\\\?\\UNC\\" + path[2:]
    return u"\\\\?\\" + path

def convert_image(image_path, image_type):

    im = Image.open(image_path)
    im = im.convert('RGB')
    
    if image_type == 'jpg':
        image_name = image_path.replace('.jpg', '.webp')
    if image_type == 'jpeg':
        image_name = image_path.replace('.jpeg', '.webp')
    if image_type == 'png':
        image_name = image_path.replace('.png', '.webp')
    
    if image_type in ['jpg', 'png', 'jpeg']:
        if maxsize:
            im.thumbnail(maxsize)
        im.save(f"{image_name}", 'webp')
    else:
        print('Images are not of type jpg or png.')


#Check Files for JPG or PNG images
for file in tqdm(file_list, desc='Searching comics', colour='green'):
    if ('.cbz' in file) or ('.zip' in file):
        try:
            MyZip = ZipFile(file)
        
            zipcontents = MyZip.namelist()
            zipcontents = [x.lower() for x in zipcontents]
            if any('.jpg' in s for s in zipcontents) or any('.png' in s for s in zipcontents) or any('.jpeg' in s for s in zipcontents):
                jpg_list.append(file)
            else:
                nojpg.append(file)
            MyZip.close()
        except:
            badfiles.append(file)
        
        
    if ('.cbr' in file) or ('.rar' in file):
        try:
            with rarfile.RarFile(file) as MyRar:
                rarcontents = MyRar.namelist()
                rarcontents = [x.lower() for x in rarcontents]
                if any('.jpg' in s for s in rarcontents) or any('.png' in s for s in rarcontents) or any('.jpeg' in s for s in rarcontents):
                    jpg_list.append(file)
                else:
                    nojpg.append(file)
        except (rarfile.BadRarFile):
            badfiles.append(file)
        except:
            continue

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

print('Found ', str(len(jpg_list)), ' out of ', str(
    len(file_list)), ' comics with jpg images.')

#Process Archives in jpg_list
for arc in tqdm(jpg_list, desc='All Files', colour='green'):
    splitpath = os.path.split(arc)
    temppath = winapi_path(os.path.join(splitpath[0], 'temp'))
    if arc.endswith('cbz') or arc.endswith('zip'):
        MyArc = ZipFile(arc)
        NewZip = arc + '.new'
        #try:
            #MyArc.extractall(path=temppath)
        #except:
            #shutil.rmtree(temppath)
        with MyArc as zf:
            for member in tqdm(zf.namelist(), desc='Extracting', colour='blue'):
                try:
                    zf.extract(member, temppath)
                except MyArc.error as e:
                    pass
    if arc.endswith('cbr') or arc.endswith('rar'):
        MyNewRar = rarfile.RarFile(arc)
        if arc.endswith('cbr'):
            NewZip = arc.replace('.cbr', '.cbz') + '.new'
        if arc.endswith('rar'):
            NewZip = arc.replace('.rar', '.cbz') + '.new'
        rarpath = os.path.join(splitpath[0], 'temp')
        os.mkdir(rarpath)
        #patoolib.extract_archive(
        #    arc, outdir=rarpath, verbosity=-1)
        with MyNewRar as zf:
            for member in tqdm(zf.namelist(), desc='Extracting', colour='blue'):
                try:
                    zf.extract(member, path=temppath)
                except:
                    pass
    for root, directory, files in os.walk(temppath):
        for file in files:
            if file.startswith('._'):
                os.remove(os.path.join(root, file))
            elif file.endswith('JPG') or file.endswith('JPEG'):
                os.rename(os.path.join(root, file), os.path.join(root, file.lower()))

    # convert to webp
    jpgimages = [str(pp) for pp in Path(temppath).glob("**/*.jpg")]
    jpegimages = [str(pp) for pp in Path(temppath).glob("**/*.jpeg")]
    pngimages = [str(pp) for pp in Path(temppath).glob("**/*.png")]
    images = jpgimages + pngimages + jpegimages
    if not images:
        print('No images to convert')
        #shutil.rmtree(temppath)
        continue
    for image in tqdm(images, desc='Converting Images', colour='yellow'):
        if image.endswith('jpg'):
            try:
                convert_image(image, 'jpg')
            except:
                badfiles.append(arc)
        if image.endswith('jpeg'):
            try:
                convert_image(image, 'jpeg')
            except:
                badfiles.append(arc)
        if image.endswith('png'):
            try:
                convert_image(image, 'png')
            except:
                badfiles.append(arc)

    # delete original images
    for file in images:
        path_to_file = os.path.join(temppath, file)
        os.remove(path_to_file)

    #contents = Contents()
    with ZipFile(NewZip, 'w') as archive:
        for root, directory, files in os.walk(temppath):
            for file in tqdm(files, desc='Compressing', colour='cyan'):
                f = os.path.join(root, file)
                archive.write(f, os.path.relpath(f, temppath))

    print('Cleaning up...')
    if backup:
        print('Saving backup of ', splitpath[1])
        shutil.copy2(arc, os.path.join(bupath, splitpath[1]))

    if 'MyArc' in locals():
        MyArc.close()

        
    if small:
        if os.path.getsize(NewZip) < os.path.getsize(arc):
            if arc.endswith('cbr'):
                arc = arc.replace('.cbr', '.cbz')
            if arc.endswith('rar'):
                arc = arc.replace('.rar', '.cbz')
            shutil.move(NewZip, arc)
        else:
            os.remove(NewZip)
    else:
        os.remove(arc)
        if arc.endswith('cbr'):
            arc = arc.replace('.cbr', '.cbz')
        if arc.endswith('rar'):
            arc = arc.replace('.rar', '.cbz')
        arc = arc.replace(conv, done)
        shutil.move(NewZip, arc)

    shutil.rmtree(temppath)
    time.sleep(5)


