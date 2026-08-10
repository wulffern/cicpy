######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

from .panzoom_view import PAN_STEP, PanZoomView, ZOOM_FACTOR  # noqa: F401
#- PAN_STEP / ZOOM_FACTOR re-exported for callers that tuned them here


class LayoutView(PanZoomView):
    """Layout view: PanZoomView with Y up, nothing else."""

    Y_UP = True
