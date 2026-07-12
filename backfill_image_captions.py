#!/usr/bin/env python3
"""Lanceur racine → scripts/backfill_image_captions.py"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).parent / "scripts" / "backfill_image_captions.py"), run_name="__main__")