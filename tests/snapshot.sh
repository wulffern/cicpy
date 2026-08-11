#!/bin/zsh
#- Snapshot every artefact of the prototype cells, so a change that is
#- meant to be behaviour-preserving can be PROVEN so rather than argued.
#-
#-   tests/snapshot.sh save <tag>     rebuild, then record
#-   tests/snapshot.sh check <tag>    rebuild, then diff against the record
#-
#- Timestamps are stripped: magic writes one into every .mag and it is the
#- only thing that legitimately changes between two identical builds.
set -u
IP=${IP:-/Users/wulff/data/2023/aicex/ip/lelo_temp_sky130a}
CELLS=${CELLS:-"LELOTEMP_CMP LELOTEMP_CCMP LELOTEMP_OTAR LELOTEMP_BIAS_IBP LELO_TEMP"}
SNAP=${SNAP:-/tmp/cicpy_snapshots}
LIB=${LIB:-LELO_TEMP_SKY130A}
TECH=${TECH:-sky130A}

mode=${1:?usage: snapshot.sh save|check <tag>}
tag=${2:?usage: snapshot.sh save|check <tag>}
dir=$SNAP/$tag
lib=$IP/design/LELO_TEMP_SKY130A

build() {
  cd $IP/work || exit 1
  for c in ${=CELLS}; do
    printf "%-20s " $c
    local t0=$SECONDS
    if make mag CELL=$c >/tmp/snap_$c.log 2>&1; then
      printf "built %5.1fs  " $((SECONDS - t0))
    else
      printf "BUILD FAILED   "; tail -3 /tmp/snap_$c.log; continue
    fi
    make drc CELL=$c >/dev/null 2>&1
    #- gds cdl lvs, in that order and always: lvs on its own reads
    #- whatever was last extracted, which is not necessarily this build
    make gds cdl lvs CELL=$c >/tmp/snap_lvs_$c.log 2>&1
    printf "%-28s %-38s %s\n" \
      "$(tail -1 drc/${c}_drc.log 2>/dev/null)" \
      "$(grep -a 'Final result' /tmp/snap_lvs_$c.log | tail -1)" \
      "$(cicpy cost ../design/${LIB}/${c}.cic ../tech/cic/${TECH}.tech $c \
         2>/dev/null | tail -1)"
  done
}

record() {
  mkdir -p $dir && rm -f $dir/*(N)
  for f in $lib/*.mag; do
    grep -v '^timestamp' $f > $dir/$(basename $f)
  done
  for f in $lib/*.cic(N) $lib/*.sch(N) $lib/*.sym(N); do
    [[ -e $f ]] && cp $f $dir/$(basename $f)
  done
  echo "recorded $(ls $dir | wc -l | tr -d ' ') artefacts in $dir"
}

case $mode in
  save)  build; record ;;
  check)
    build
    [[ -d $dir ]] || { echo "no snapshot '$tag'"; exit 1 }
    bad=0
    for f in $lib/*.mag; do
      b=$(basename $f)
      [[ -e $dir/$b ]] || { echo "NEW      $b"; bad=1; continue }
      diff -q <(grep -v '^timestamp' $f) $dir/$b >/dev/null || { echo "CHANGED  $b"; bad=1 }
    done
    for f in $lib/*.cic(N) $lib/*.sch(N) $lib/*.sym(N); do
      b=$(basename $f)
      [[ -e $dir/$b ]] || { echo "NEW      $b"; bad=1; continue }
      cmp -s $f $dir/$b || { echo "CHANGED  $b"; bad=1 }
    done
    (( bad )) && { echo "SNAPSHOT DIFFERS"; exit 1 }
    echo "all $(ls $dir | wc -l | tr -d ' ') artefacts identical to '$tag'"
    ;;
  *) echo "usage: snapshot.sh save|check <tag>"; exit 1 ;;
esac
