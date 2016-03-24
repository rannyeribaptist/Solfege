#!/usr/bin/python
import sys
import urllib
import os
import zipfile
import glob
cachedir = "../pkg-cache"
srcdir = "../src-cache"


urls = {}

urls['svg-gdk-pixbuf-loader'] = {
    'bin': "ftp://ftp.gnome.org/pub/GNOME/binaries/win32/librsvg/2.26/svg-gdk-pixbuf-loader_2.26.2-1_win32.zip",
}
urls['svg-gtk-engine'] = {
    'bin': "ftp://ftp.gnome.org/pub/gnome/binaries/win32/librsvg/2.26/svg-gtk-engine_2.26.2-1_win32.zip",
}
urls['libiconv'] = {
    'bin': "http://downloads.sourceforge.net/project/gnuwin32/libiconv/1.9.2-1/libiconv-1.9.2-1-bin.zip?r=http%3A%2F%2Fgnuwin32.sourceforge.net%2Fpackages%2Flibiconv.htm&ts=1290714269&use_mirror=sunet"
}
urls['libxml2'] = {
    'bin': "ftp://ftp.zlatkovic.com/libxml/libxml2-2.7.7.win32.zip",
}
urls['libgsf'] = {
    'bin': "ftp://ftp.gnome.org/pub/gnome/binaries/win32/libgsf/1.14/libgsf_1.14.17-1_win32.zip",
}
urls['libcroco'] = {
    'bin': "ftp://ftp.gnome.org/pub/gnome/binaries/win32/libcroco/0.6/libcroco_0.6.2-1_win32.zip",
}
urls['librsvg'] = {
    'bin': "ftp://ftp.gnome.org/pub/gnome/binaries/win32/librsvg/2.26/librsvg_2.26.2-1_win32.zip",
}

gtk_bundle_url = "http://ftp.gnome.org/pub/gnome/binaries/win32/gtk+/2.22/gtk+-bundle_2.22.0-20101016_win32.zip"
gtk_bundle_fn = os.path.join(cachedir, gtk_bundle_url.split("/")[-1])

def get_files(key, savedir):
    if not os.path.exists(savedir):
        os.mkdir(savedir)
    for app in urls:
        if key not in urls[app]:
            continue
        url = urls[app][key]
        fn = os.path.join(savedir, url.split("?")[0].split("/")[-1])
        if not os.path.exists(fn):
            print "Downloading:", fn
            sys.stdout.flush()
            urllib.urlretrieve(url, fn)
        else:
            print "File already here:", fn

def unpack_file(fn):
        print "unzipping:", fn
        sys.stdout.flush()
        z = zipfile.ZipFile(fn)
        for n in z.namelist():
            if n.endswith("/"):
                continue
            if n.startswith("libxml2-"):
                out_fn = "/".join(n.split("/")[1:])
            else:
                out_fn = n
            dir = os.path.join("win32", os.path.dirname(out_fn))
            if not os.path.exists(dir):
                os.makedirs(dir)
            outfile = open(os.path.join("win32", out_fn), 'wb')
            outfile.write(z.read(n))
            outfile.close()

def unpack():
    for app in urls:
        f = os.path.join(cachedir, urls[app]['bin'].split("?")[0].split("/")[-1])
        unpack_file(f)

if sys.argv[1] == 'bin':
    get_files('bin', cachedir)
elif sys.argv[1] == 'src':
    get_files('src', scdir)
elif sys.argv[1] == 'unpack':
    unpack()
elif sys.argv[1] == 'get-bundle':
    if not os.path.exists(gtk_bundle_fn):
        print "Downloading:", gtk_bundle_fn
        sys.stdout.flush()
        urllib.urlretrieve(gtk_bundle_url, gtk_bundle_fn)
    else:
        print "File already here:", gtk_bundle_fn
elif sys.argv[1] == 'unpack-bundle':
    unpack_file(gtk_bundle_fn)

