import os
import sys

def asset_path(base_path: str) -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        baesdir = sys._MEIPASS # type: ignore
    else:
        basedir = os.path.join(os.path.split(__file__)[0], os.pardir, os.pardir)
    return os.path.join(basedir, 'assets', base_path)