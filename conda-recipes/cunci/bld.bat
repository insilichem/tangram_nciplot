:: go to source dir

cd %SRC_DIR%\cuNCI-1.0\source 

:: compile with gfortran
make

:: move binaries and dat files
mv %SRC_DIR%\cuNCI-1.0\source\cuda_nci.exe %NCIPLOT_HOME%\bin\cuda_nci.exe
cp %NCIPLOT_HOME%\bin\cuda_nci.exe %SCRIPTS%\cuda_nci.exe

