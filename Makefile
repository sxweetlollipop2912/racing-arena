cli:
	python client/client.py
ser:
	python server/server.py

build-cli:
	mkdir -p dist/client
	cp -r client/assets dist/client/
	pyinstaller -F -p ./client/ --add-data ./client/assets/:client/assets/ client/client.py
build-ser:
	pyinstaller -F -p ./server/ server/server.py