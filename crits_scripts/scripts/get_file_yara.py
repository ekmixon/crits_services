import sys
import time
import tarfile
from io import BytesIO
from optparse import OptionParser

import bson
from crits.core.mongo_tools import *
from crits.core.basescript import CRITsBaseScript
import settings

class CRITsScript(CRITsBaseScript):

    def __init__(self, user=None):
        super(CRITsScript, self).__init__(user=user)

    def run(self, argv):
        parser = OptionParser()
        parser.add_option("-y", "--yara-hit", action="store", dest="yarahit",
                type="string", help="string of yarahit")
        parser.add_option("-o", "--output-file", action="store", dest="outfile",
                type="string", help="output archive file (no extension)")
        (opts, args) = parser.parse_args(argv)
        if opts.yarahit and opts.outfile:
            filename = f"{opts.outfile}.tar.bz2"
            try:
                tar = tarfile.open(filename, "w:bz2")
            except Exception as e:
                print(f"Error when attempting to open {filename} for writing: {e}")
                sys.exit(1)
            samples = mongo_connector(settings.COL_ANALYSIS_RESULTS)
            results = samples.find({'results.result': f'{opts.yarahit}'}, {'object_id': 1})
            count = results.count()
            if count <= 0:
                print ("No matching samples found!")
                sys.exit(1)
            for result in results:
                print(f"oid next in {settings.COL_SAMPLES} ")
                boid = result['object_id']
                print(f"oid: {str(boid)}")
                try:
                    fm = mongo_connector(settings.COL_SAMPLES)
                    f = fm.find_one({'_id': bson.ObjectId(oid=str(boid))}, {'filename':1 })['filename']
                    m = fm.find_one({ '_id' : bson.ObjectId(oid=str(boid))}, {'md5':1})['md5']
                    print(f"m: {str(m)}")
                except Exception as e:
                    print(f"Error : {e}")
                    return None
                s = get_file(m)
                info = tarfile.TarInfo(name=f"{f}")
                info.mtime = time.time()
                info.size = len(s) if s is not None else 0
                try:
                    tar.addfile(info, BytesIO(s))
                except Exception as e:
                    print(f"Error attempting to add {f} to the tarfile: {e}")
            tar.close()
            print(f"Generated {filename} containing {count} files.")
