#
# Makefile for creating a PyCmd.zip binary distribution
# Requires:
#	* Python >= 3.10 (32-bit or 64-bit)
#	* MinGW (make, rm, cp etc) and python in the %PATH%
#	* zip
#	* patchelf (for Linux)
#	* cx_freeze python package
# 	* pywin32 and pefile python packages (for Windows)
#
# Author: Horea Haitonic
#
RM = rm -f
CP = cp
MV = mv
ZIP = zip

ifeq ($(OS),Windows_NT)
	SHELL = cmd
	BUILD_DATE = $(shell WMIC os GET LocalDateTime | grep -v Local | cut -c 1-8)
	PYTHONHOME_W32 = C:\Program Files (x86)\Python310-32
	PYTHONHOME_W64 = C:\Program Files\Python310
	PYTHON_W32 = (set "PYTHONHOME=$(PYTHONHOME_W32)") && "$(PYTHONHOME_W32)\python.exe"
	PYTHON_W64 = (set "PYTHONHOME=$(PYTHONHOME_W64)") && "$(PYTHONHOME_W64)\python.exe"
	PYTHON = $(PYTHON_W64)
else
	BUILD_DATE = $(shell date +"%Y%m%d")
	PYTHON = python3
endif

SRC = \
    src/pycmd/PyCmd.py \
	src/pycmd/InputState.py \
	src/pycmd/DirHistory.py \
	src/pycmd/common.py \
	src/pycmd/completion.py \
	src/pycmd/console/*.py \
	src/pycmd/fsm.py
SRC_TEST = common_tests.py


.PHONY: all
ifeq ($(OS),Windows_NT)
all:
	$(MAKE) clean
	$(MAKE) dist_w32 
	$(MAKE) clean
	$(MAKE) dist_w64
	$(MAKE) dist_whl
else
all:
	$(MAKE) clean
	$(MAKE) dist_linux64
endif

doc: src/pycmd/pycmd_public.py
	$(PYTHON) -c "import sys; sys.path.append('src');from pycmd import pycmd_public; import pydoc; pydoc.writedoc(pycmd_public)"
	$(MV) pycmd.pycmd_public.html src/pycmd/

dist_w32: clean $(SRC) doc
	echo build_date = '$(BUILD_DATE)' > src/pycmd/buildinfo.py
	cd freeze && $(PYTHON_W32) setup.py build
	$(MV) freeze/build/exe.win32-3.10 PyCmd
	$(CP) README.txt PyCmd
# cx_freeze fails to copy this
	$(CP) "$(PYTHONHOME_W32)\Lib\site-packages\pywin32_system32\pywintypes310.dll" PyCmd\lib
	(echo Release $(BUILD_DATE) && type NEWS.txt) > PyCmd\NEWS.txt
	$(ZIP) -r PyCmd-$(BUILD_DATE)-w32.zip PyCmd

dist_w64: clean $(SRC) doc
	echo build_date = '$(BUILD_DATE)' > src/pycmd/buildinfo.py
	cd freeze && $(PYTHON_W64) setup.py build
	$(MV) freeze/build/exe.win-amd64-3.10 PyCmd
	$(CP) README.txt PyCmd
# cx_freeze fails to copy this
	$(CP) "$(PYTHONHOME_W64)\Lib\site-packages\pywin32_system32\pywintypes310.dll" PyCmd\lib
	(echo Release $(BUILD_DATE) && type NEWS.txt) > PyCmd\NEWS.txt
	$(ZIP) -r PyCmd-$(BUILD_DATE)-w64.zip PyCmd

dist_linux64: clean $(SRC) doc
	echo build_date = \'$(BUILD_DATE)\' > src/pycmd/buildinfo.py
	cd freeze && python3 setup.py build
	$(MV) freeze/build/exe.linux-x86_64-3.10/ PyCmd
	$(CP) README.txt PyCmd
	(echo Release $(BUILD_DATE) && cat NEWS.txt) > PyCmd/NEWS.txt
	$(ZIP) -r PyCmd-$(BUILD_DATE)-linux64.zip PyCmd

dist_whl: clean $(SRC) doc
	echo build_date = '$(BUILD_DATE)' > src/pycmd/buildinfo.py
	$(PYTHON_W64) -m build

.PHONY: clean
clean:
	$(RM) src/pycmd/buildinfo.*
	$(RM) $(SRC:%.py=%.pyc)
	$(RM) pycmd.pycmd_public.html
	cd tests && $(RM) $(SRC_TEST:%.py=%.pyc) && $(RM) __init__.pyc
	$(RM) -r build PyCmd dist
