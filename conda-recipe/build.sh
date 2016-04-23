#!/bin/bash

cd "${SRC_DIR}/src"
# Compile nciplot with gfortran
make mrproper
make
make clean

NCIPLOT_HOME="${PREFIX}/nciplot"
# Create NCIPLOT_HOME dirs
mkdir "${NCIPLOT_HOME}" "${NCIPLOT_HOME}/bin"
# Move binary, libs and exampels to NCIPLOT_HOME/bin 
mv "${SRC_DIR}/src/nciplot" "${NCIPLOT_HOME}/bin/nciplot"
mv "${SRC_DIR}/dat" "${NCIPLOT_HOME}/"
# mv "${SRC_DIR}/test-cases" "${NCIPLOT_HOME}/"
# Softlink binary to ENV/bin
ln -s "${NCIPLOT_HOME}/bin/nciplot" "${PREFIX}/bin/nciplot"
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