# -*- coding: utf-8 -*-
import sys
from common import *

if sys.argv[1] == 'insert_npvr':
    res = request('NPVRInsert', {'customerReferenceID': sys.argv[2], 'epgReferenceID': sys.argv[3]})
elif sys.argv[1] == 'delete_npvr':
    res = request('NPVRDelete', {'customerReferenceID': sys.argv[2], 'epgReferenceID': sys.argv[3]})
    xbmc.executebuiltin("Container.Refresh")
