#!/usr/bin/env python

import sys
import os
import json
import re
import tarfile, io

import anchore.anchore_utils

def get_retrieved_file(imgid, srcfile, dstdir):
    ret = list()

    extractall = False
    if srcfile == 'all':
        extractall = True

    stored_data_tarfile = anchore.anchore_utils.load_analysis_output(imgid, 'retrieve_files', 'file_cache')
    if stored_data_tarfile:
        tar = tarfile.open(fileobj=stored_data_tarfile, mode='r:gz', format=tarfile.PAX_FORMAT)
        for f in tar.getmembers():
            if re.match(".*stored_files.tar.gz", f.name):
                data = tar.extractfile(f)
                filetar = tarfile.open(fileobj=data, mode='r:gz', format=tarfile.PAX_FORMAT)
                for ff in filetar.getmembers():
                    patt = re.match("imageroot("+re.escape(srcfile)+")", ff.name)
                    if extractall or patt:
                        filetar.extract(ff, dstdir)
                        scrubbed_name = re.sub("imageroot", "", ff.name)
                        ret.append([scrubbed_name, os.path.join(dstdir, ff.name)])
                filetar.close()
        tar.close()
        stored_data_tarfile.close()
    return(ret)

gate_name = "FILEPARSE_PASSWD"

try:
    config = anchore.anchore_utils.init_gate_cmdline(sys.argv, "Gate Description")
except Exception as err:
    print str(err)
    sys.exit(1)

if not config:
    print "ERROR: could not set up environment for gate"
    sys.exit(1)

imgid = config['imgid']
imgdir = config['dirs']['imgdir']
analyzerdir = config['dirs']['analyzerdir']
outputdir = config['dirs']['outputdir']

try:
    params = config['params']
except:
    params = None

# do somthing
outlist = list()

# first, attempt to extract /etc/passwd
dstdir = os.path.join(outputdir, 'extract_tmp')
retlist = get_retrieved_file(config['imgid'], '/etc/passwd', dstdir)
if not retlist:
    outlist.append(["FILENOTSTORED", "Cannot locate /etc/passwd in image's stored files archive: check analyzer settings"])
else:
    users = {}
    with open(retlist[0][1], 'r') as FH:
        for l in FH.readlines():
            l = l.strip()
            try:
                pentry = l.split(":")
                users[pentry[0]] = pentry[1:]
            except:
                pass
    
    for pstr in params:
        try:
            (pkey, pvallist) = pstr.split("=")
            if pkey == 'USERNAMEBLACKLIST':
                for pval in pvallist.split(","):
                    try:
                        print pkey + " : " + pval
                        if pval in users:
                            pentry = str(':'.join([pval] + users[u]))
                            outlist.append(["USERNAMEMATCH", "Blacklisted user '"+pval+"' found in image's /etc/passwd: pentry="+pentry])
                    except:
                        pass
            elif pkey == 'USERIDBLACKLIST':
                for pval in pvallist.split(","):
                    try:
                        for u in users.keys():
                            uid = users[u][1]
                            if str(uid) == pval:
                                pentry = str(':'.join([u] + users[u]))
                                outlist.append(["USERIDMATCH", "Blacklisted uid '"+pval+"' found in image's /etc/passwd: pentry="+pentry])
                    except:
                        pass
            elif pkey == 'GROUPIDBLACKLIST':
                for pval in pvallist.split(","):
                    try:
                        for u in users.keys():
                            gid = users[u][2]
                            if str(gid) == pval:
                                pentry = str(':'.join([u] + users[u]))
                                outlist.append(["GROUPIDMATCH", "Blacklisted gid '"+pval+"' found in image's /etc/passwd: pentry="+pentry])
                    except:
                        pass
            elif pkey == 'SHELLBLACKLIST':
                for pval in pvallist.split(","):
                    try:
                        for u in users.keys():
                            shellstr = users[u][5]
                            if str(shellstr) == pval:
                                pentry = str(':'.join([u] + users[u]))
                                outlist.append(["SHELLMATCH", "Blacklisted shell '"+pval+"' found in image's /etc/passwd: pentry="+pentry])
                    except:
                        pass
            elif pkey == 'PENTRYBLACKLIST':
                for pval in pvallist.split(","):
                    try:
                        for u in users.keys():
                            pentry = str(':'.join([u] + users[u]))
                            print "MEH: " + pval + " | " + pentry
                            if pval == pentry:
                                outlist.append(["PENTRYMATCH", "Blacklisted pentry '"+pval+"' found in image's /etc/passwd: pentry="+pentry])
                    except:
                        pass
        except:
            pass

# write output
output = '/'.join([outputdir, gate_name])
anchore.anchore_utils.write_kvfile_fromlist(output, outlist)

sys.exit(0)
