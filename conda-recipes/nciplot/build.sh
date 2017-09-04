#!/usr/bin/env bash

cd "${SRC_DIR}/src"
# Patch in Mac
if [ "$(uname -s)" == "Darwin" ]; then
    mv Makefile Makefile.bak
    sed -e "s/\(@mkdir.*\)/# \1/" -e "s/\(ln.*\)/# \1/g" Makefile.bak > Makefile
fi
# Compile nciplot with gfortran
make mrproper
make
make clean

NCIPLOT_HOME="${PREFIX}/etc/nciplot"
# Create NCIPLOT_HOME dirs
mkdir -p "${NCIPLOT_HOME}"
# Move binary, libs and examples to NCIPLOT_HOME/bin 
mv "${SRC_DIR}/src/nciplot" "${PREFIX}/bin/nciplot"
mv "${SRC_DIR}/dat" "${NCIPLOT_HOME}/"

# Add NCIPLOT_HOME env var at env activation
mkdir -p "${PREFIX}/etc/conda/activate.d" "${PREFIX}/etc/conda/deactivate.d"
echo "#!/bin/sh
export NCIPLOT_HOME=${NCIPLOT_HOME}" > "${PREFIX}/etc/conda/activate.d/nciplot_envvars.sh"
echo "#!/bin/sh
unset NCIPLOT_HOME" > "${PREFIX}/etc/conda/deactivate.d/nciplot_envvars.sh"
# Also for fish
echo "#!/usr/bin/env fish
set -gx NCIPLOT_HOME ${NCIPLOT_HOME}" > "${PREFIX}/etc/conda/activate.d/nciplot_envvars.fish"
echo "#!/usr/bin/env fish
set -e NCIPLOT_HOME" > "${PREFIX}/etc/conda/deactivate.d/nciplot_envvars.fish"
# Clean
rm -r "${SRC_DIR}"