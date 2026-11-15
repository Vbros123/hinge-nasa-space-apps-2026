import os, sys, copy
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import numpy as np, pandas as pd
from engine.crop_calendar import load_crop_library, load_yaml, generate_rotation_templates
from engine.io_utils import normalize_weather
from tools.make_synthetic_fixture import make_weather, MANIFEST

CFG = os.path.join(ROOT, "config")
P = load_yaml(os.path.join(CFG, "model_parameters.yaml"))
LIB = load_crop_library(os.path.join(CFG, "crops_nc.yaml"))
ROTS = generate_rotation_templates(LIB, os.path.join(CFG, "rotations_nc.yaml"))
MGMT = P["management_defaults"]
SOIL = {"scenarios": P["soil_storage_scenarios_mm"]}


def weather(start=1990, end=1996, **kw):
    return normalize_weather(make_weather(start, end, **kw), MANIFEST["units"])
