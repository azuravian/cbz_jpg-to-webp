# cbz_jpg-to-webp
Convert cbz files that contain jpg or png images to webp images.

Dependencies:
Requires Python 3.

Requires installation of PILLOW, tqdm, unrar:  
Use the following to install:  
```
pip install pillow  
pip install tqdm
pip install unrar
```

This will search through whatever directory you select (and all subdirectories) for cbz, cbr, zip, or rar files.  It will check the contents of each file to determine if it contains any jpg or png files.  For all cbzs with jpg or png files, it will extract all data to a temp folder, convert the jpgs/pngs to webp images, and then create a new cbz file with the converted images.  Any other contents of the cbz (such as ComicInfo.xml) will be retained.  The final file will overwrite the existing file, so ensure you have a backup first.

usage: cbz_JPG-to-WEBP.py [-h] [-b] [-s] [-m]

Find and convert comics from jpg or png to webp

optional arguments:  
  -h, --help    show this help message and exit  
  -b, --backup  Make backup of each cbz to a specified folder  
  -s, --small   Keep smaller file  
  -m, --maxsize Set the maximum height of each image.  Script will resize while keeping the aspect ratio.
