all: build

build: build_wheel build_exe

build_wheel:
	poetry build --format=wheel

build_exe: wine_install_dependecies
	wine pyinstaller --onefile --upx-dir "C:/upx" \
	--add-binary "c:/windows/system32/bcrypt.dll;." \
	-c -n mtput mt_copy_tools/mtput/__main__.py

wine_install_dependecies:
	wine C:/Python34/python.exe -m pip install -r requirements-win.txt

wine_setup:
	wine C:/Python34/python.exe -m pip install pip==18.1

shell: start
	docker compose exec -ti dev bash

start:
	docker compose up -d

dist:
	mkdir -p dist
