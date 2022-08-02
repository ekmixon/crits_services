import sys
import tarfile
import time
from io import BytesIO
from optparse import OptionParser

from crits.core.basescript import CRITsBaseScript
from crits.samples.sample import Sample

class CRITsScript(CRITsBaseScript):
    def __init__(self, username=None):
        self.username = username

    def run(self, argv):
        parser = OptionParser()
        parser.add_option('-b', '--bucket', action='store', dest='bucket', 
                          type='string', help='bucket list name')
        parser.add_option("-o", "--output-file", action="store", dest="outfile", 
                          type="string", help="output archive file (no extension)")
        (opts, args) = parser.parse_args(argv)

        samples = Sample.objects(bucket_list=opts.bucket)
        if opts.bucket and opts.outfile:
            filename = f"{opts.outfile}.tar.bz2"
            try:
                tar = tarfile.open(filename, "w:bz2")
            except Exception as e:
                print(f"Error when attempting to open {filename} for writing: {e}")
                sys.exit(1)
        count = len(samples)
        if count <= 0:
            print ("No matching bucket name found!")
            sys.exit(1)
        for sample in samples:
            m = sample.md5
            f = sample.filename
            s = sample.filedata.read()
            info = tarfile.TarInfo(name=f"{f}")
            info.mtime = time.time()
            info.size = len(s) if s is not None else 0
            try:
                tar.addfile(info, BytesIO(s))
            except Exception as e:
                print(f"Error attempting to add {f} to the tarfile: {e}")
        tar.close()
        print(f"Generated {filename} containing {count} files.")
            
            
