cli:
	python client/client.py
ser:
	python server/server.py

build-cli:
	pyinstaller -n client-binary -i ./client/client.ico -w -F -p ./client/ --add-data ./dist/client/assets/:client/assets/ client/client.py
build-ser:
	pyinstaller -n server-binary -i ./server/server.ico -F -p ./server/ server/server.py

prepare:
	rm -rf dist
	mkdir -p dist/client
	cp -r client/assets dist/client

build: prepare build-cli build-ser
	