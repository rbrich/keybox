# memlock
# (disable swap for the process)
#

import ctypes
from ctypes.util import find_library
import os
import errno
import resource


def memlock():
    """Try to lock all current and future memory pages.

    Encountering error while locking memory is not considered fatal,
    no exception is raised.

    """
    # Set MEMLOCK soft limit to maximum
    limits = resource.getrlimit(resource.RLIMIT_MEMLOCK)
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (limits[1], limits[1]))
    # Call mlockall(MCL_CURRENT | MCL_FUTURE)
    try:
        libc = ctypes.CDLL(find_library("c"), use_errno=True)
        rc = libc.mlockall(0b11)
    except OSError as e:
        print("Warning: Unable to lock memory.", str(e))
        return
    if rc == -1:
        err = ctypes.get_errno()
        if err == errno.ENOMEM:
            limit = resource.getrlimit(resource.RLIMIT_MEMLOCK)[1]
            print("Warning: Unable to lock memory.",
                  "Consider raising MEMLOCK limit (current %d)." % limit)
        else:
            print("Error (mlockall):", errno.errorcode[err], os.strerror(err))
