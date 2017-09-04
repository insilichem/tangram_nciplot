#!/usr/bin/env bash

cd "${SRC_DIR}/cuNCI-1.0/source"

# Compile nciplot with nvcc
make

NCIPLOT_HOME="${PREFIX}/nciplot"
# Create NCIPLOT_HOME dirs
mkdir -p "${NCIPLOT_HOME}/bin"
# Move binary to NCIPLOT_HOME/bin 
mv "${SRC_DIR}/cuNCI-1.0/source/cuda_nci" "${NCIPLOT_HOME}/bin/cuda_nci"
# Softlink binary to ENV/bin
ln -s "${NCIPLOT_HOME}/bin/cuda_nci" "${PREFIX}/bin/cuda_nci"
# Clean
rm -r "${SRC_DIR}"