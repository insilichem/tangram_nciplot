:: go to source dir
cd %SRC_DIR%\src 

:: patch ln calls, because unxutils' ln does not support relative links
mv Makefile Makefile.bak
sed -e "s/\(@mkdir.*\)/# \1/" -e "s/\(ln.*\)/# \1/g" Makefile.bak > Makefile
if errorlevel 1 exit 1

:: compile with gfortran
make mrproper
if errorlevel 1 exit 1
make
if errorlevel 1 exit 1
make clean
if errorlevel 1 exit 1

:: create directories
set NCIPLOT_HOME=%PREFIX%\nciplot
mkdir %NCIPLOT_HOME% %NCIPLOT_HOME%\bin
if errorlevel 1 exit 1

:: move binaries and dat files
mv %SRC_DIR%\src\nciplot.exe %NCIPLOT_HOME%\bin\nciplot.exe
if errorlevel 1 exit 1
mv %SRC_DIR%\dat %NCIPLOT_HOME%\dat
if errorlevel 1 exit 1
cp %NCIPLOT_HOME%\bin\nciplot.exe %SCRIPTS%\nciplot.exe
if errorlevel 1 exit 1
