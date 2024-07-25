# racing-arena

A simple multiplayer racing game using with TCP sockets via Python asyncio.

Detailed report on protocol, scrreenshots, video demo, storyline etc. in [/report.pdf](https://github.com/sxweetlollipop2912/racing-arena/blob/main/report.pdf).

## Running the game

To run the server, execute the following command:

```bash
make ser
```

To run the client, execute the following command:

```bash
make cli
```

## Build the game binary

Require `pyinstaller` to build the binary.

```bash
make build-cli # to build the client
make build-ser # to build the server
```
