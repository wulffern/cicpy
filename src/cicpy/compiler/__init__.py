#!/usr/bin/env python3
"""Compile ciccreator object-definition files into a cicpy Design."""

from .reader import readJson
from .registry import cicclass, get, known, register
from .builder import Compiler
from . import cells  # noqa: F401  -- registers the cell classes
