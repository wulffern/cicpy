#!/usr/bin/env python3
"""Read a ciccreator object-definition .json.

ciccreator's Design::readJson is not a JSON parser with a comment
extension bolted on -- it is a LINE FILTER in front of a strict
parser. A line whose first non-space characters are `//` is dropped
whole; a `//` anywhere else is ordinary string content and survives.
The surviving lines are then joined WITHOUT newlines.

Both halves matter. Strip trailing comments too and a URL inside a
string loses its second slash. Keep the newlines and the error
offsets ciccreator reports stop lining up with the file. So do
exactly what the C++ does, and nothing more.
"""
import json
import re

#- ^\s*// -- the whole-line comment, and only that
COMMENT = re.compile(r"^\s*//")


def readJson(filename):
    """Parse an object file the way ciccreator does."""
    lines = []
    with open(filename, "r", encoding="utf-8") as fi:
        for line in fi:
            line = line.rstrip("\n").rstrip("\r")
            if COMMENT.match(line):
                continue
            lines.append(line)
    text = "".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        #- ciccreator walks the joined text back to a line number so the
        #- message names a place in the FILE, not an offset in a string
        #- nobody can see. Do the same or the error is useless.
        count = 0
        for i, line in enumerate(lines):
            count += len(line)
            if count >= e.pos:
                raise json.JSONDecodeError(
                    "%s (near line %d of %s: %s)" % (e.msg, i + 1, filename, line.strip()[:60]),
                    text, e.pos) from None
        raise
