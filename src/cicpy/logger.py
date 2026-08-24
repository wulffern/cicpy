######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
##
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
##
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
##
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##
######################################################################
"""Central logging and console for cicpy.

Every module logs through the standard :mod:`logging` machinery and the
CLI installs a rich handler on the root logger, so diagnostics come out
colored and consistently formatted. Data output -- reports, listings,
netlists the user asked for -- goes through :data:`console` instead of
bare ``print()``, which keeps it on stdout and rich-rendered without it
masquerading as a log record.
"""

import logging

from rich.console import Console
from rich.logging import RichHandler

#- Data output channel. Markup is off because layout reports carry
#- literal [brackets]; soft_wrap keeps report lines from folding at
#- the terminal width.
console = Console(markup=False, soft_wrap=True)


def getLogger(name):
    """The one place cicpy modules fetch their logger from."""
    return logging.getLogger(name)


def setupLogging(level=logging.INFO, stderr=False):
    """Install the rich handler on the root logger.

    Called once by each entry point. ``stderr=True`` is for servers
    (cicpy-mcp) whose stdout is a protocol channel.
    """
    handler = RichHandler(console=Console(stderr=stderr, markup=False),
                          show_time=False,
                          show_path=False,
                          rich_tracebacks=True)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
