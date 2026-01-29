@ECHO OFF

set SPHINXBUILD=sphinx-build
set SOURCEDIR=.
set BUILDDIR=_build

if "%1"=="" (
  %SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR%
  goto end
)

if "%1"=="clean" (
  rmdir /S /Q %BUILDDIR%
  goto end
)

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR%

:end
