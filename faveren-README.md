# PTA Server — Protocolo de Transferência de Arquivos 

## Project Description

This project implements a TCP-based file transfer server in Python, following the PTA (Protocolo de Transferência de Arquivos) specification provided in pta.pdf.

The server supports:

*a.* Client authentication (CUMP)

*b.* Listing available files (LIST)

*c.* File retrieval (PEGA)

*d.* Connection termination (TERM)

*e.* Sequence-number validation

*f.* Error handling using NOK

*g.* Binary file transfer

*h.* Multiple simultaneous client connections

The implementation is located in the pta-server directory of the forked repository.

The users.txt file and files directory are provided and must remain unchanged.


## Requirements

- Python 3.10 or newer; standard library only (no pip installs).
- TCP port 11550 available on localhost.
- Windows, Linux, or macOS

The implementation uses Python's standard libraries, including socket, select, threading, and pathlib.

## Download the Repository

Open your forked GitHub repository: https://github.com/faveren/pta

Click Code → Download ZIP, then extract the ZIP file.

Alternatively, clone the repository using Git:

        git clone https://github.com/faveren/pta.git
        cd pta

## Running the PTA Server

Open a terminal in the repository's root directory, where pta-client.py is located.

Start the server: **python .\pta-server\faveren-server.py**

Expected output: **PTA listening on 127.0.0.1:11550**

The server listens on TCP port 11550 using the local loopback address **127.0.0.1**.

Keep this terminal open while testing.

## Troubleshooting: Server File Not Found

If the server does not start because Python cannot locate *faveren-server.py*, first verify that the file exists in the pta-server directory.

From the repository's root directory, run the following command in Windows PowerShell:

        Get-ChildItem .\pta-server\

Confirm that faveren-server.py, users.txt, and the files directory are present.

If *faveren-server.py* was accidentally placed in the repository's root directory instead of pta-server, move it using:

        Move-Item .\faveren-server.py .\pta-server\faveren-server.py

Then start the server again:    **python .\pta-server\faveren-server.py**

The server reads `pta-server/users.txt` at each authentication attempt (case-sensitive), and serves `pta-server/files/` without modifying the files. The file list contains representable regular filenames; PTA's comma/space separators cannot encode filenames containing commas or spaces.


## Running the PTA Client *(pta-client)*

Open a second terminal and navigate to the root directory of the downloaded repository.

For example, on Windows PowerShell: **cd C:\Users\YourName\Downloads\pta-master**

Ensure that this directory contains pta-client.py.

*Test with user1*

**python .\pta-client.py 127.0.0.1 11550 user1**

*Test with user2*

**python .\pta-client.py 127.0.0.1 11550 user2**

*Test with user3*

**python .\pta-client.py 127.0.0.1 11550 user3**

The authorized usernames are read directly from: **pta-server/users.txt**


## Protocol behavior

- CUMP authentication before all other commands; invalid credentials: NOK and close.
- LIST replies ARQS count filenames; PEGA replies ARQ size raw file bytes.
- TERM replies OK and closes.
- Each reply echoes the client's sequence number; sessions are independent.
- Invalid command in READY replies NOK without disconnecting.

## Known compatibility limitation

The original PTA PDF does not define a TCP request delimiter, and the supplied legacy client (pta-client.py) sends requests without a newline. To support that client and LF-delimited clients, this server uses a short quiet-gap heuristic for newline-free requests. Requests fragmented with delays longer than that interval may be misinterpreted. Reliable arbitrary-delay fragmentation requires an agreed framing rule on both ends.

The *pta-client.py* client may not decode binary files correctly; this server sends their exact bytes according to the specification. **Do not modify the supplied files to work around client limitations.** This client may therefore attempt to decode received file contents as UTF-8 text. If it randomly selects a PNG image, it may terminate with a UnicodeDecodeError.

This is a limitation of the demonstration client and does not necessarily indicate an error in the server.

The server's binary-transfer integrity was independently verified using SHA-256 comparison.

## Invalid Authentication

If an unauthorized username is supplied, the server responds with NOK and closes the connection.

For example, **User2** is rejected because only **user2** is listed in users.txt.

The demonstration client may attempt additional commands after authentication fails and display a connection error. This does not mean the server should keep the connection open.

## TCP Message Framing

The server supports newline-delimited requests and a compatibility mechanism for the pta-client.py client, which sends requests without newline delimiters.

Because the PTA specification does not define an explicit request-framing mechanism, deliberately delayed TCP fragments may expose a limitation in the compatibility mechanism.

## Stopping the Server

To stop the server, return to the terminal where it is running and press:   ** Ctrl + C **
