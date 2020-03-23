# -*- coding: utf-8 -*-
"""
Created on Sun Mar 22 12:00:54 2020

@author: mary 
pour tester tous les zonages sur les departements 
"""


import numpy as np
import glob
import xarray as xr 
import matplotlib.pyplot as plt 
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import matplotlib
import pandas as pd
import time
import glob
import sys, os
import string
from pathlib import Path # pour windows 
sys.path.insert(0, os.path.abspath('./lib'))

from lib import read_xarray, find_neighbours, distance