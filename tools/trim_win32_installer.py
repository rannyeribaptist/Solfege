
import glob
import os
import glob
import shutil
import solfege.languages

sol_po = glob.glob("po/*.po")
sol_po = [os.path.split(x)[1] for x in sol_po]
sol_po = [os.path.splitext(x)[0] for x in sol_po]

gtk_po = glob.glob(r"win32\share\locale\*")

for lang in gtk_po:
    if os.path.isdir(lang):
        if os.path.split(lang)[-1] not in sol_po:
            shutil.rmtree(lang)

for d in glob.glob("win32/bin/Lib/*/test"):
    shutil.rmtree(d)

shutil.rmtree("win32/src")
shutil.rmtree("win32/man")
shutil.rmtree("win32/manifest")
shutil.rmtree("win32/include")
shutil.rmtree("win32/bin/Lib/test/")
shutil.rmtree("win32/bin/Lib/lib-tk")
shutil.rmtree("win32/bin/Lib/idlelib")
shutil.rmtree("win32/bin/Lib/distutils")
shutil.rmtree("win32/share/aclocal")
shutil.rmtree("win32/share/doc")
shutil.rmtree("win32/share/gtk-2.0")
shutil.rmtree("win32/share/gtk-doc")
shutil.rmtree("win32/share/man")
shutil.rmtree("win32/lib/pkgconfig")
