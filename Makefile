all: build

build: build_wheel build_exe

build_wheel:
	poetry build --format=wheel

build_exe: wine_install_dependecies
	wine C:/Python38/python.exe -m poetry run pyinstaller --onefile --upx-dir "C:/upx" \
	-c -n mtput mt_copy_tools/mtput/__main__.py

wine_install_dependecies:
	wine C:/Python38/python.exe -m poetry install
