# updownserver

A lightweight HTTP server with unified upload/download interface.
Based on the excellent [uploadserver](https://github.com/Densaugeo/uploadserver) by Densaugeo.

[繁體中文說明 (Traditional Chinese)](README_zh-tw.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://mit-license.org/)

## Key Features

*   **Unified Interface**: Drag & drop uploads, file management, and downloads all in one page.
*   **File Management**: Create folders and delete files directly from the web UI.
*   **Mobile Friendly**: Generate a QR code in the terminal for easy mobile access.
*   **Security First**: Auto-shutdown timer (default 5 mins) and enforcing timeouts for unauthenticated sessions.
*   **Docker Support**: Ready-to-use Dockerfile for containerized deployment.
*   **Zero Dependency**: Core features run with standard Python libraries.

## Supported Platforms

| Platform | Supported? | Notes |
|---|---|---|
| Python 3.9+ | Yes | Tested on 3.9 through 3.14 every release. |
| Python 3.6-3.8 | No | Was supported by previous versions. |
| Python 3.5- | No | |
| Linux | Yes | Tested on Fedora and Ubuntu every release. |
| Windows | Yes | Occasional manual testing. Haven't noticed any obvious problems. |
| Mac | No idea | I don't have a Mac. Idk if it works or not. |

## Installation

~~~bash
python3 -m pip install --user updownserver
# Optional: Install query dependencies for QR code support
python3 -m pip install --user updownserver[qr]

# Or using uv (Recommended for speed)
uv pip install updownserver[qr]
~~~

## Docker Support

Build the image:
~~~bash
docker build -t updownserver .
~~~

Run sharing the current directory (mapped to `/data` in the container):
~~~bash
# Linux/Mac
docker run -p 8000:8000 -v $(pwd):/data updownserver

# Windows (PowerShell)
docker run -p 8000:8000 -v ${PWD}:/data updownserver
~~~

Run with custom arguments (e.g., auto-shutdown disabled):
~~~bash
docker run -p 8000:8000 -v $(pwd):/data updownserver --timeout 0 --basic-auth user:pass
~~~

## Usage

Start the server:
~~~bash
python3 -m updownserver
~~~

Show a QR code for mobile connection (requires `updownserver[qr]`):
~~~bash
python3 -m updownserver --qr
~~~

To prevent forgetting to close the server, it auto-shutdowns after 300 seconds (5 minutes) by default.
To run indefinitely (**authentication required** for security):
~~~bash
python3 -m updownserver --timeout 0 --basic-auth user:pass
~~~

After the server starts, the unified upload/download interface is at the root URL.
This main page allows you to:
- **Download files**: Click on any file in the list.
- **Upload files**: Drag and drop files into the upload zone or use the file selector.
- **Manage files**: Create new folders or delete files (trash icon) directly from the UI. (**Note**: For security, these operations are disabled if no authentication is configured.)

The POST endpoint `/upload` is still available for programmatic access (e.g. cURL).

Warning: This is an upload server, and running it will allow uploads.

Now supports uploading multiple files at once! Select multiple files in the web page's file selector, or upload with cURL:
~~~bash
curl -X POST http://127.0.0.1:8000/upload -F 'files=@multiple-example-1.txt' -F 'files=@multiple-example-2.txt'
~~~

## Basic Authentication (downloads and uploads)

~~~bash
python3 -m updownserver --basic-auth hello:world
~~~

Now you can upload with basic authentication. For example:
~~~bash
curl -X POST http://127.0.0.1:8000/upload -F 'files=@basicauth-example.txt' -u hello:world
~~~

All requests without authentication will be rejected. Note that basic authentication credentials can be stolen if sent over plain HTTP, so this option is best used with HTTPS.

## Basic Authentication (uploads only)

~~~bash
python3 -m updownserver --basic-auth-upload hello:world
~~~

The same as above, but authentication is only required for upload operations.

If both `--basic-auth` and `--basic-auth-upload` are specified, all requests will require one of the two credentials, but only the `--basic-auth-upload` credentials will be able to upload files.

## Theme Option

The upload page supports a dark mode for showing white text on black background. If no option is specified, the color scheme is chosen from the client’s browser’s preference (which typically matches their operating system’s setting, if light or dark mode is supported by the OS). To enforce the light or dark theme, the CLI parameter `--theme` can be used:
~~~bash
python3 -m updownserver --theme light
~~~
or
~~~bash
python3 -m updownserver --theme dark
~~~

## HTTPS Option

Run with HTTPS and without client authentication:
~~~bash
# Generate self-signed server certificate
openssl req -x509 -out server.pem -keyout server.pem -newkey rsa:2048 -nodes -sha256 -subj '/CN=server'

# The server root should not contain the certificate, for security reasons
cd server-root
python3 -m updownserver --server-certificate server.pem

# Connect as a client
curl -X POST https://localhost:8000/upload --insecure -F files=@simple-example.txt
~~~

Run with HTTPS and with client authentication:
~~~bash
# Generate self-signed server certificate
openssl req -x509 -out server.pem -keyout server.pem -newkey rsa:2048 -nodes -sha256 -subj '/CN=server'

# Generate self-signed client certificate
openssl req -x509 -out client.pem -keyout client.pem -newkey rsa:2048 -nodes -sha256 -subj '/CN=client'

# Extract public key from self-signed client certificate
openssl x509 -in client.pem -out client.crt

# The server root should not contain the certificates, for security reasons
cd server-root
python3 -m updownserver --server-certificate server.pem --client-certificate client.crt

# Connect as a client
curl -X POST https://localhost:8000/upload --insecure --cert client.pem -F files=@mtls-example.txt
~~~

Note: This uses a self-signed server certificate which clients such as web browser and cURL will warn about. Most browsers will allow you to proceed after adding an exception, and cURL will work if given the -k/--insecure option. Using your own certificate from a certificate authority will avoid these warnings.

## Available Options

```
usage: __main__.py [-h] [--cgi] [--allow-replace] [--bind ADDRESS]
                   [--directory DIRECTORY] [--theme {light,auto,dark}]
                   [--server-certificate SERVER_CERTIFICATE]
                   [--client-certificate CLIENT_CERTIFICATE]
                   [--basic-auth BASIC_AUTH]
                   [--basic-auth-upload BASIC_AUTH_UPLOAD] [--timeout TIMEOUT]
                   [--qr]
                   [port]

positional arguments:
  port                  Specify alternate port [default: 8000]

options:
  -h, --help            show this help message and exit
  --cgi                 Run as CGI Server
  --allow-replace       Replace existing file if uploaded file has the same
                        name. Auto rename by default.
  --bind, -b ADDRESS    Specify alternate bind address [default: all
                        interfaces]
  --directory, -d DIRECTORY
                        Specify alternative directory [default:current
                        directory]
  --theme {light,auto,dark}
                        Specify a light or dark theme for the upload page
                        [default: auto]
  --server-certificate, --certificate, -c SERVER_CERTIFICATE
                        Specify HTTPS server certificate to use [default:
                        none]
  --client-certificate CLIENT_CERTIFICATE
                        Specify HTTPS client certificate to accept for mutual
                        TLS [default: none]
  --basic-auth BASIC_AUTH
                        Specify user:pass for basic authentication (downloads
                        and uploads)
  --basic-auth-upload BASIC_AUTH_UPLOAD
                        Specify user:pass for basic authentication (uploads
                        only)
  --timeout TIMEOUT     Auto-shutdown server after N seconds (0 to disable)
                        [default: 300]
  --qr                  Show QR code at startup
```




## Acknowledgements

Special thanks to [Densaugeo](https://github.com/Densaugeo) and all contributors of the original [uploadserver](https://github.com/Densaugeo/uploadserver) project for providing the solid foundation for this tool.

