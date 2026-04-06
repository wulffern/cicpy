# place

`place` runs the transistor placer on a CSV fixture and writes both a placement table and SKILL output.

<!--run_output:
run: make test PYTHON=/opt/eda/python3/bin//python3 && ls -1 diffpair_place.csv horz_place.csv vert_place.csv diffpair.il horz.il vert.il
-->

The base fixture:

<!--cat:
file: diffpair.csv
language: csv
lines: 12
-->

Computed placement for the diffpair case:

<!--cat:
file: diffpair_place.csv
language: csv
lines: 16
-->

Horizontal placer output:

<!--cat:
file: horz_place.csv
language: csv
lines: 16
-->

Vertical placer output:

<!--cat:
file: vert_place.csv
language: csv
lines: 16
-->
