"""
from pyrevit.userconfig import PyRevitConfig
import os

this_folder = os.path.dirname(os.path.abspath(__file__))
init_file = os.path.join(this_folder, 'config.ini')

cfg = PyRevitConfig(init_file)

cfg.add_section('Settings')
cfg.Settings.font = 'Courier'

cfg.save_changes()
"""

from pyrevit import forms
import time

forms.select_titleblocks()