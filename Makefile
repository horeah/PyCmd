#
# Makefile for creating a PyCmd.zip binary and wheel distribution
# Requires:
#	* Python >= 3.10 (32-bit or 64-bit)
#	* MinGW (make, rm, cp etc) and python in the %PATH%
#	* zip
#	* patchelf (for Linux)
#	* cx_freeze python package
#   * 'setuptools_scm' python package for auto versioning
#   * 'build' python package for building a .whl
# 	* pywin32 and pefile python packages (for Windows)
#
# Author: Horea Haitonic
#
MV = mv
ZIP = zip

ifeq ($(OS),Windows_NT)
	SHELL = cmd
	PYTHONHOME_W32 = C:\Program Files (x86)\Python310-32
	PYTHONHOME_W64 = C:\Program Files\Python310
	PYTHON_W32 = (set "PYTHONHOME=$(PYTHONHOME_W32)") && "$(PYTHONHOME_W32)\python.exe"
	PYTHON = (set "PYTHONHOME=$(PYTHONHOME_W64)") && "$(PYTHONHOME_W64)\python.exe"
	CAT = type
	VENV_BIN = .venv/Scripts
else
	PYTHON = python3
	CAT = cat
	VENV_BIN = .venv/bin
endif

VERSION = $(shell $(PYTHON) -m setuptools_scm --strip-dev)

.PHONY: all
ifeq ($(OS),Windows_NT)
all:
	$(MAKE) dist_w32
	$(MAKE) dist_w32_chat
	$(MAKE) dist_w64
	$(MAKE) dist_w64_chat
	$(MAKE) dist_whl
else
all:
	$(MAKE) dist_linux64
	$(MAKE) dist_linux64_chat
endif

doc: src/pycmd/pycmd_public.py
	$(PYTHON) -c "import sys; sys.path.append('src');from pycmd import pycmd_public; import pydoc; pydoc.writedoc(pycmd_public)"
	$(MV) pycmd.pycmd_public.html src/pycmd/pycmd_public.html

dist_w32: clean doc
	$(PYTHON_W32) -m cx_Freeze build
	$(MV) build/exe.win32-3.10 PyCmd
	(echo Release $(VERSION) && $(CAT) NEWS.txt) > PyCmd\NEWS.txt
	$(ZIP) -r dist/PyCmd-$(VERSION)-w32.zip PyCmd

dist_w32_chat: clean doc
	$(PYTHON_W32) -m cx_Freeze build_exe --packages=chatlas,google
	$(MV) build/exe.win32-3.10 PyCmd
	(echo Release $(VERSION) && $(CAT) NEWS.txt) > PyCmd\NEWS.txt
	$(ZIP) -r dist/PyCmd-$(VERSION)[chat]-w32.zip PyCmd

dist_w64: clean doc
	$(PYTHON) -m cx_Freeze build
	$(MV) build/exe.win-amd64-3.10 PyCmd
	(echo Release $(VERSION) && $(CAT) NEWS.txt) > PyCmd\NEWS.txt
	$(ZIP) -r dist/PyCmd-$(VERSION)-w64.zip PyCmd

dist_w64_chat: clean doc
	$(PYTHON) -m cx_Freeze build_exe --packages=chatlas,google
	$(MV) build/exe.win-amd64-3.10 PyCmd
	(echo Release $(VERSION) && $(CAT) NEWS.txt) > PyCmd\NEWS.txt
	$(ZIP) -r dist/PyCmd-$(VERSION)[chat]-w64.zip PyCmd

dist_linux64: clean doc
	$(PYTHON) -m cx_Freeze build
	$(MV) build/exe.linux-x86_64-3.10/ PyCmd
	(echo Release $(VERSION) && $(CAT) NEWS.txt) > PyCmd/NEWS.txt
	$(ZIP) -r dist/PyCmd-$(VERSION)-linux64.zip PyCmd

dist_linux64_chat: clean doc
	$(PYTHON) -m cx_Freeze build_exe --packages=chatlas,google
	$(MV) build/exe.linux-x86_64-3.10/ PyCmd
	(echo Release $(VERSION) && $(CAT) NEWS.txt) > PyCmd/NEWS.txt
	$(ZIP) -r dist/PyCmd-$(VERSION)[chat]-linux64.zip PyCmd

dist_whl: clean doc
	(echo Release $(VERSION) && $(CAT) NEWS.txt) > src/pycmd/NEWS.txt
	$(PYTHON) -m build

test_whl:
	$(PYTHON) -m venv --clear .venv
	$(VENV_BIN)/pip install $(wildcard dist/*whl)[chat]
	$(VENV_BIN)/pycmd

.PHONY: clean
clean:
	git clean -xdf -e dist
