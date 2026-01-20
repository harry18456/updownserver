import http.server, http, pathlib, sys, argparse, ssl, os, builtins, tempfile, threading, shutil
import base64, binascii, functools, contextlib

# Does not seem to do be used, but leaving this import out causes updownserver
# to not receive IPv4 requests when started with default options under Windows
import socket

# The cgi module was deprecated in Python 3.13, so I saved a copy in this
# project
if sys.version_info.major == 3 and sys.version_info.minor < 13:
    import cgi
else:
    import updownserver.cgi

COLOR_SCHEME = {
    'light': 'light',
    'auto': 'light dark',
    'dark': 'dark',
}



def get_directory_head_injection(theme: str) -> bytes:
    return bytes('''<!-- Injected by updownserver -->
<meta name="viewport" content="width=device-width" />
<meta name="color-scheme" content="''' + COLOR_SCHEME.get(theme) + '''">
<style>
    :root {
        --bg-color: #ffffff;
        --text-color: #000000;
        --accent-color: #007bff;
        --border-color: #e9ecef;
        --zone-bg: #f8f9fa;
        --zone-hover: #e2e6ea;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-color: #121212;
            --text-color: #e0e0e0;
            --accent-color: #4da3ff;
            --border-color: #333;
            --zone-bg: #1e1e1e;
            --zone-hover: #2d2d2d;
        }
    }
    
    /* Breadcrumb navigation */
    .breadcrumb-nav {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        padding: 10px 15px;
        background-color: var(--zone-bg);
        border-radius: 8px;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }
    
    .breadcrumb-nav a {
        color: var(--accent-color);
        text-decoration: none;
    }
    
    .breadcrumb-nav a:hover {
        text-decoration: underline;
    }
    
    .breadcrumb-nav .separator {
        color: var(--text-color);
        opacity: 0.5;
    }
    
    .breadcrumb-nav .current {
        color: var(--text-color);
        font-weight: bold;
    }
    
    .back-btn {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 5px 10px;
        background-color: var(--accent-color);
        color: white;
        text-decoration: none;
        border-radius: 4px;
        font-size: 14px;
        margin-right: 10px;
    }
    
    .back-btn:hover {
        opacity: 0.9;
        text-decoration: none;
    }
    
    .upload-widget {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        border: 2px dashed var(--border-color);
        border-radius: 12px;
        background-color: var(--zone-bg);
        text-align: center;
        padding: 30px 20px;
        margin: 20px 0;
        transition: all 0.2s ease;
        position: relative;
        cursor: pointer;
    }
    
    .upload-widget:hover, .upload-widget.dragover {
        border-color: var(--accent-color);
        background-color: var(--zone-hover);
    }
    
    .upload-widget h3 {
        margin: 0 0 10px 0;
        color: var(--text-color);
        font-size: 1.2rem;
    }
    
    .upload-widget p {
        margin: 0;
        color: var(--text-color);
        opacity: 0.7;
    }
    
    .upload-progress {
        margin-top: 15px;
        font-weight: bold;
        color: var(--accent-color);
        min-height: 1.5em;
    }
    
    input[type="file"] {
        display: none;
    }
</style>
<!-- End injection by updownserver -->
''', 'utf-8')


DIRECTORY_BODY_INJECTION = b'''<!-- Injected by updownserver -->
<!-- Breadcrumb Navigation -->
<div class="breadcrumb-nav" id="breadcrumb-nav"></div>

<div class="upload-widget" id="drop-zone" onclick="document.getElementById('file-input').click()">
    <h3>Drag and drop files here to upload</h3>
    <p>or click to select components</p>
    <div id="upload-status" class="upload-progress"></div>
    <form id="upload-form" action="/upload" method="POST" enctype="multipart/form-data">
        <input type="file" id="file-input" name="files" multiple onchange="handleFiles(this.files)">
    </form>
</div>

<!-- New Folder Interface -->
<!-- New Folder Interface (Hidden if no auth) -->
<div id="mkdir-container" style="text-align: center; margin-bottom: 20px; display: none;">
    <form id="mkdir-form" onsubmit="event.preventDefault(); createFolder();" style="display: inline-block;">
        <input type="text" id="foldername" name="foldername" placeholder="New folder name" style="padding: 5px; border-radius: 4px; border: 1px solid #ccc;">
        <button type="submit" style="padding: 5px 10px; cursor: pointer; background-color: var(--accent-color); color: white; border: none; border-radius: 4px;">Create Folder</button>
    </form>
</div>

<script>
    // Generate breadcrumb navigation
    (function() {
        const nav = document.getElementById('breadcrumb-nav');
        const path = decodeURIComponent(window.location.pathname);
        const parts = path.split('/').filter(p => p);
        
        let html = '';
        
        // Home link
        html += '<a href="/">[Home]</a>';
        
        // Build path breadcrumbs
        let currentPath = '';
        for (let i = 0; i < parts.length; i++) {
            html += '<span class="separator">/</span>';
            currentPath += '/' + parts[i];
            if (i === parts.length - 1) {
                html += '<span class="current">' + parts[i] + '</span>';
            } else {
                html += '<a href="' + currentPath + '/">' + parts[i] + '</a>';
            }
        }
        
        nav.innerHTML = html;
    })();

    // Initialize UI based on Auth
    document.addEventListener('DOMContentLoaded', () => {
        if (typeof ENABLE_DELETE !== 'undefined' && ENABLE_DELETE) {
            const mkdirContainer = document.getElementById('mkdir-container');
            if (mkdirContainer) mkdirContainer.style.display = 'block';
        }
    });

    const dropZone = document.getElementById('drop-zone');
    const statusDiv = document.getElementById('upload-status');
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop zone
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    // Handle dropped files and folders
    dropZone.addEventListener('drop', async (e) => {
        const dt = e.dataTransfer;
        const items = dt.items;
        
        // Check if we have items (for folder support)
        if (items && items.length > 0) {
            const allFiles = [];
            const entries = [];
            
            // Collect all entries first
            for (let i = 0; i < items.length; i++) {
                const entry = items[i].webkitGetAsEntry && items[i].webkitGetAsEntry();
                if (entry) {
                    entries.push(entry);
                }
            }
            
            if (entries.length > 0) {
                statusDiv.textContent = 'Reading files...';
                
                // Process all entries (files and directories)
                for (const entry of entries) {
                    await traverseFileTree(entry, '', allFiles);
                }
                
                if (allFiles.length > 0) {
                    uploadFilesWithPaths(allFiles);
                } else {
                    statusDiv.textContent = 'No files found.';
                }
                return;
            }
        }
        
        // Fallback for browsers without webkitGetAsEntry
        const files = dt.files;
        handleFiles(files);
    });

    // Recursively traverse file tree for folder drops
    async function traverseFileTree(entry, path, allFiles) {
        if (entry.isFile) {
            return new Promise((resolve) => {
                entry.file((file) => {
                    // Store file with its relative path
                    allFiles.push({ file: file, path: path + file.name });
                    resolve();
                }, () => resolve()); // Ignore errors for individual files
            });
        } else if (entry.isDirectory) {
            const dirReader = entry.createReader();
            const entries = await readAllDirectoryEntries(dirReader);
            for (const childEntry of entries) {
                await traverseFileTree(childEntry, path + entry.name + '/', allFiles);
            }
        }
    }

    // Read all entries from a directory (handles batching)
    function readAllDirectoryEntries(dirReader) {
        return new Promise((resolve) => {
            const allEntries = [];
            
            function readEntries() {
                dirReader.readEntries((entries) => {
                    if (entries.length === 0) {
                        resolve(allEntries);
                    } else {
                        allEntries.push(...entries);
                        readEntries(); // Continue reading (entries are batched)
                    }
                }, () => resolve(allEntries)); // Ignore errors
            }
            
            readEntries();
        });
    }

    function handleFiles(files) {
        if (files.length === 0) return;
        // Convert FileList to array of {file, path} objects
        const filesWithPaths = Array.from(files).map(f => ({ file: f, path: f.name }));
        uploadFilesWithPaths(filesWithPaths);
    }

    function uploadFilesWithPaths(filesWithPaths) {
        const url = '/upload';
        const formData = new FormData();

        // Get current directory path from URL
        const currentPath = decodeURIComponent(window.location.pathname);
        formData.append('path', currentPath);

        for (const item of filesWithPaths) {
            formData.append('files', item.file);
            formData.append('filenames', item.path); // Send relative path
        }

        statusDiv.textContent = `Uploading ${filesWithPaths.length} file(s)...`;

        const xhr = new XMLHttpRequest();
        xhr.open('POST', url, true);

        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                statusDiv.textContent = `Uploading: ${Math.round(percentComplete)}%`;
            }
        };

        xhr.onload = function() {
            if (xhr.status === 204) {
                statusDiv.textContent = 'Upload successful! Reloading...';
                setTimeout(() => location.reload(), 1000);
            } else if (xhr.status === 401) {
                 statusDiv.textContent = 'Authentication required.';
                 location.href = '/upload'; 
            } else {
                statusDiv.textContent = `Error: ${xhr.status} ${xhr.statusText}`;
            }
        };

        xhr.onerror = function() {
            statusDiv.textContent = 'Upload failed due to connection error.';
        };

        xhr.send(formData);
    }

    // --- New Feature: Create Folder ---
    function createFolder() {
        const input = document.getElementById('foldername');
        const foldername = input.value.trim();
        if (!foldername) return;

        const formData = new FormData();
        formData.append('foldername', foldername);
        // Get current directory path from URL
        const currentPath = decodeURIComponent(window.location.pathname);
        formData.append('path', currentPath);

        fetch('/mkdir', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.status === 201) {
                location.reload();
            } else if (response.status === 401) {
                alert('Authentication required');
                location.reload();
            } else {
                return response.text().then(text => alert('Error: ' + text));
            }
        })
        .catch(err => alert('Error: ' + err));
    }

    // --- New Feature: Delete Buttons ---
    // Inject delete buttons and file info into the file list
    document.addEventListener('DOMContentLoaded', () => {
        const list = document.querySelector('ul');
        if (!list) return;

        const items = list.querySelectorAll('li');
        items.forEach(li => {
            const link = li.querySelector('a');
            if (!link) return;
            
            const name = link.getAttribute('href');
            // Skip parent directory link
            if (name === '../' || name === '..') return;

            // Add file info span
            const infoSpan = document.createElement('span');
            infoSpan.style.marginLeft = '15px';
            infoSpan.style.color = 'gray';
            infoSpan.style.fontSize = '0.85em';
            infoSpan.textContent = '';
            li.appendChild(infoSpan);

            // Fetch file info using HEAD request
            fetch(name, { method: 'HEAD' })
                .then(response => {
                    const size = response.headers.get('Content-Length');
                    const modified = response.headers.get('Last-Modified');
                    let info = [];
                    
                    if (size && !name.endsWith('/')) {
                        info.push(formatFileSize(parseInt(size)));
                    }
                    if (modified) {
                        info.push(formatDate(modified));
                    }
                    
                    if (info.length > 0) {
                        infoSpan.textContent = '(' + info.join(', ') + ')';
                    }
                })
                .catch(() => {});

            // Add delete button if auth enabled
            if (typeof ENABLE_DELETE !== 'undefined' && ENABLE_DELETE) {
                const delBtn = document.createElement('span');
                delBtn.innerHTML = ' &#128465;'; // Trash can icon
                delBtn.style.cursor = 'pointer';
                delBtn.style.color = 'red';
                delBtn.style.marginLeft = '10px';
                delBtn.title = 'Delete';
                
                delBtn.onclick = (e) => {
                    e.preventDefault();
                    if (confirm(`Delete "${decodeURIComponent(name)}"?`)) {
                        deleteFile(name);
                    }
                };
                
                li.appendChild(delBtn);
            }
        });
    });

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function formatDate(dateStr) {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        } catch (e) {
            return dateStr;
        }
    }

    function deleteFile(filename) {
        fetch(filename, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.status === 204) {
                location.reload();
            } else if (response.status === 401) {
                alert('Authentication required');
                location.reload();
            } else if (response.status === 403) {
                alert('Access denied');
            } else {
                alert('Delete failed (directory not empty?)');
            }
        })
        .catch(err => alert('Error: ' + err));
    }
</script>
<hr>
<!-- End injection by updownserver -->
'''



class PersistentFieldStorage(cgi.FieldStorage):
    # Override cgi.FieldStorage.make_file() method. Valid for Python 3.1 ~ 3.10.
    # Modified version of the original .make_file() method (base copied from
    # Python 3.10)
    def make_file(self) -> object:
        if self._binary_file:
            return tempfile.NamedTemporaryFile(mode = 'wb+',
                dir = args.directory, delete = False)
        else:
            return tempfile.NamedTemporaryFile("w+", dir = args.directory,
                delete = False, encoding = self.encoding, newline = '\n')

# True argument/return type is str | pathlib.Path, but Python 3.9 doesn't
# support |
def auto_rename(path: pathlib.Path) -> pathlib.Path:
    if not os.path.exists(path):
        return path
    (base, ext) = os.path.splitext(path)
    for i in range(1, sys.maxsize):
        renamed_path = f'{base} ({i}){ext}'
        if not os.path.exists(renamed_path):
            return renamed_path
    raise FileExistsError(f'File {path} already exists.')

def receive_upload(handler: http.server.BaseHTTPRequestHandler,
) -> tuple[http.HTTPStatus, str]:
    result = (http.HTTPStatus.INTERNAL_SERVER_ERROR, 'Server error')
    name_conflict = False
    
    form = PersistentFieldStorage(fp=handler.rfile, headers=handler.headers,
        environ={'REQUEST_METHOD': 'POST'})
    if 'files' not in form:
        return (http.HTTPStatus.BAD_REQUEST, 'Field "files" not found')
    
    # Get the target path from form data (current directory in browser)
    upload_path = form.getvalue('path', '/')
    # Remove leading slash and sanitize
    upload_path = upload_path.lstrip('/')
    # Build target directory, validate it's within the served directory
    target_dir = pathlib.Path(args.directory) / upload_path
    target_dir = target_dir.resolve()
    server_root = pathlib.Path(args.directory).resolve()
    
    # Security check: ensure target is within server root
    if server_root not in target_dir.parents and server_root != target_dir:
        return (http.HTTPStatus.FORBIDDEN, 'Invalid upload path')
    
    if not target_dir.is_dir():
        return (http.HTTPStatus.BAD_REQUEST, 'Target directory does not exist')
    
    fields = form['files']
    if not isinstance(fields, list):
        fields = [fields]
    
    # Get custom filenames (with relative paths for folder uploads)
    filenames_list = []
    if 'filenames' in form:
        filenames_data = form['filenames']
        if isinstance(filenames_data, list):
            filenames_list = [f.value for f in filenames_data]
        else:
            filenames_list = [filenames_data.value]
    
    if not all(field.file and field.filename for field in fields):
        return (http.HTTPStatus.BAD_REQUEST, 'No files selected')
    
    for idx, field in enumerate(fields):
        if field.file and field.filename:
            # Use custom filename (with path) if provided, otherwise use original filename
            if idx < len(filenames_list) and filenames_list[idx]:
                relative_path = filenames_list[idx]
                # Sanitize: remove leading slashes and normalize
                relative_path = relative_path.lstrip('/\\')
                # Security: prevent directory traversal
                relative_path = os.path.normpath(relative_path)
                if relative_path.startswith('..') or os.path.isabs(relative_path):
                    relative_path = pathlib.Path(field.filename).name
            else:
                relative_path = pathlib.Path(field.filename).name
        else:
            relative_path = None
        
        if relative_path:
            destination = target_dir / relative_path
            destination = destination.resolve()
            
            # Security check: ensure destination is still within server root
            if server_root not in destination.parents and server_root != destination.parent:
                handler.log_message('[Upload Rejected] Path traversal attempt: %s', relative_path)
                continue
            
            # Create parent directories if needed (for folder uploads)
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            if os.path.exists(destination):
                if args.allow_replace and os.path.isfile(destination):
                    os.remove(destination)
                else:
                    destination = auto_rename(destination)
                    name_conflict = True
            if hasattr(field.file, 'name'):
                source = field.file.name
                field.file.close()
                os.rename(source, destination)
            # class '_io.BytesIO', small file (< 1000B, in cgi.py), in-memory
            # buffer
            else:
                with open(destination, 'wb') as f:
                    f.write(field.file.read())
            handler.log_message('[Uploaded] "%s" --> %s', relative_path, destination)
            result = (http.HTTPStatus.NO_CONTENT, 'Some filename(s) changed '
                'due to name conflict' if name_conflict else 'Files accepted')
    
    return result

def receive_mkdir(handler: http.server.BaseHTTPRequestHandler
) -> tuple[http.HTTPStatus, str]:
    if args.basic_auth_upload and not check_http_authentication(handler):
         # This should have been handled by do_POST but double check
         return (http.HTTPStatus.UNAUTHORIZED, 'Authentication required')

    form = PersistentFieldStorage(fp=handler.rfile, headers=handler.headers,
        environ={'REQUEST_METHOD': 'POST'})
    
    if 'foldername' not in form:
        return (http.HTTPStatus.BAD_REQUEST, 'Field "foldername" not found')
    
    foldername = form['foldername'].value
    if not foldername:
        return (http.HTTPStatus.BAD_REQUEST, 'Folder name is empty')
        
    # Sanitize folder name - prevent directory traversal or absolute paths
    foldername = os.path.basename(foldername)
    
    # Get the current path from form data
    current_path = form.getvalue('path', '/')
    current_path = current_path.lstrip('/')
    
    # Build target directory
    base_dir = pathlib.Path(args.directory) / current_path
    base_dir = base_dir.resolve()
    server_root = pathlib.Path(args.directory).resolve()
    
    # Security check: ensure target is within server root
    if server_root not in base_dir.parents and server_root != base_dir:
        return (http.HTTPStatus.FORBIDDEN, 'Invalid path')
    
    target_path = base_dir / foldername
    
    if os.path.exists(target_path):
        return (http.HTTPStatus.CONFLICT, 'Directory or file already exists')
    
    try:
        os.mkdir(target_path)
        handler.log_message('[Mkdir] Created directory "%s"', target_path)
        return (http.HTTPStatus.CREATED, 'Directory created')
    except OSError as e:
        return (http.HTTPStatus.INTERNAL_SERVER_ERROR, f'Failed to create directory: {e}')


# True return type is tuple[bool, str | None], but Python 3.9 doesn't support |
def check_http_authentication_header(
handler: http.server.BaseHTTPRequestHandler, auth: str,
) -> tuple[bool, str]:
    auth_header = handler.headers.get('Authorization')
    if auth_header is None:
        return (False, 'No credentials given')
    
    auth_header_words = auth_header.split(' ')
    if len(auth_header_words) != 2:
        return (False, 'Credentials incorrectly formatted')
    
    if auth_header_words[0].lower() != 'basic':
        return (False, 'Credentials incorrectly formatted')
    
    try:
        http_username_password = base64.b64decode(auth_header_words[1]).decode()
    except binascii.Error:
        return (False, 'Credentials incorrectly formatted')
    
    http_username, http_password = http_username_password.split(':', 2)
    args_username, args_password = auth.split(':', 2)
    if http_username != args_username: return (False, 'Bad username')
    if http_password != args_password: return (False, 'Bad password')
    
    return (True, None)

def check_http_authentication(handler: http.server.BaseHTTPRequestHandler
) -> bool:
    """
    This function should be called in at the beginning of HTTP method handler.
    It validates Authorization header and sends back 401 response on failure.
    It returns False if this happens.
    """
    if not args.basic_auth_upload:
        # If no auth settings apply, check always passes
        if not args.basic_auth:
            return True
        
        # If only --basic-auth is supplied, it's used for all requests
        valid, message = check_http_authentication_header(handler, args.basic_auth)
    else:
        # If --basic-auth-upload is supplied, it's always required for /upload
        # and other write operations (mkdir, delete)
        is_write_op = (handler.path == '/upload' or 
                       handler.path == '/mkdir' or 
                       (hasattr(handler, 'command') and handler.command == 'DELETE'))
        
        if is_write_op:
            valid, message = check_http_authentication_header(handler,
                args.basic_auth_upload)
        else:
            # For paths outside /upload, no auth is required when --basic-auth
            # is not supplied
            if not args.basic_auth:
                return True
            
            # For paths outside /upload (read ops), if both auths are supplied,
            # both are accepted.
            valid, message = check_http_authentication_header(handler,
                args.basic_auth)
            if not valid:
                valid, message = check_http_authentication_header(handler,
                    args.basic_auth_upload)
    
    if not valid:
        handler.send_response(http.HTTPStatus.UNAUTHORIZED)
        handler.send_header('WWW-Authenticate', 'Basic realm="Upload"')
        handler.end_headers()
    return valid

# Let's not inherit http.server.SimpleHTTPRequestHandler - that would cause
# diamond-pattern inheritance
class ListDirectoryInterception:
    # Only runs when serving directory listings
    def flush_headers_interceptor(self):
        # Calculate auth state for delete JS injection size matching copyfile_interceptor
        has_auth = args.basic_auth or args.basic_auth_upload or args.client_certificate
        enable_delete_js = b'<script>const ENABLE_DELETE = ' + \
            (b'true' if has_auth else b'false') + b';</script>'

        for i, header in enumerate(self._headers_buffer):
            if header[:15] == b'Content-Length:':
                length = int(header[15:]) + len(DIRECTORY_BODY_INJECTION) + \
                    len(get_directory_head_injection(args.theme)) + \
                    len(enable_delete_js) + \
                    len(get_shutdown_timer_injection())
                
                # Use same encoding that self.send_header() uses
                self._headers_buffer[i] = f'Content-Length: {length}\r\n' \
                    .encode('latin-1', 'strict')
        
        # Can't use super() - avoiding diamond-pattern inheritance'
        http.server.SimpleHTTPRequestHandler.flush_headers(self)
    
    # Only runs when serving directory listings
    def copyfile_interceptor(self, source, outputfile):
        content = source.read()
        content = content.replace(b'</head>',
            get_directory_head_injection(args.theme) + b'</head>')
        
        # Determine if delete/mkdir should be enabled based on auth
        has_auth = args.basic_auth or args.basic_auth_upload or args.client_certificate
        enable_delete_js = b'<script>const ENABLE_DELETE = ' + \
            (b'true' if has_auth else b'false') + b';</script>'
            
        content = content.replace(b'<ul>', enable_delete_js + DIRECTORY_BODY_INJECTION + b'<ul>')
        
        # Inject shutdown timer if enabled (or warning if disabled)
        content = content.replace(b'</body>', get_shutdown_timer_injection() + b'</body>')
        
        outputfile.write(content)
    
    # True argument type is str | pathlib.Path, but Python 3.9 doesn't support |
    def list_directory(self, path: pathlib.Path) -> object:
        setattr(self, 'flush_headers', self.flush_headers_interceptor)
        setattr(self, 'copyfile', self.copyfile_interceptor)
        
        # Can't use super() - avoiding diamond-pattern inheritance'
        return http.server.SimpleHTTPRequestHandler.list_directory(self, path)

class SimpleHTTPRequestHandler(ListDirectoryInterception,
    http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if not check_http_authentication(self): return
        
        if self.path == '/upload':
            send_upload_page(self)
        else:
            super().do_GET()
    
    def do_POST(self):
        if not check_http_authentication(self): return
        
        if self.path == '/upload':
            result = receive_upload(self)
        elif self.path == '/mkdir':
            result = receive_mkdir(self)
        else:
            self.send_error(http.HTTPStatus.NOT_FOUND,
                'Can only POST/PUT to /upload or /mkdir')
            return

        if result[0] < http.HTTPStatus.BAD_REQUEST:
            self.send_response(result[0], result[1])
            self.end_headers()
        else:
            self.send_error(result[0], result[1])
    
    def do_PUT(self):
        self.do_POST()

    def do_DELETE(self):
        if not check_http_authentication(self): return
        
        # Security: Prevent directory traversal
        target_path = self.translate_path(self.path)
        
        # Ensure target is within the served directory
        server_root = pathlib.Path(args.directory).resolve()
        try:
            target_path_obj = pathlib.Path(target_path).resolve()
            if server_root not in target_path_obj.parents and server_root != target_path_obj:
                self.send_error(http.HTTPStatus.FORBIDDEN, "Access denied")
                return
        except Exception:
             self.send_error(http.HTTPStatus.BAD_REQUEST, "Invalid path")
             return

        if os.path.isfile(target_path):
            try:
                os.remove(target_path)
                self.send_response(http.HTTPStatus.NO_CONTENT)
                self.end_headers()
            except OSError:
                self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to delete file")
        elif os.path.isdir(target_path):
            try:
                shutil.rmtree(target_path)
                self.send_response(http.HTTPStatus.NO_CONTENT)
                self.end_headers()
            except OSError:
                self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to delete directory")
        else:
            self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")

class CGIHTTPRequestHandler(ListDirectoryInterception,
    http.server.CGIHTTPRequestHandler):
    def do_GET(self):
        if not check_http_authentication(self): return
        
        super().do_GET()
    
    def do_POST(self):
        if not check_http_authentication(self): return
        
        if self.path == '/upload':
            result = receive_upload(self)
        elif self.path == '/mkdir':
             result = receive_mkdir(self)
        else:
            super().do_POST()
            return
            
        if result[0] < http.HTTPStatus.BAD_REQUEST:
            self.send_response(result[0], result[1])
            self.end_headers()
        else:
            self.send_error(result[0], result[1])

    def do_DELETE(self):
        # reuse the implementation from SimpleHTTPRequestHandler (safe since we check args.directory)
        SimpleHTTPRequestHandler.do_DELETE(self)
    
    def do_PUT(self):
        self.do_POST()

def intercept_first_print():
    if args.server_certificate:
        # Use the right protocol in the first print call in case of HTTPS
        old_print = builtins.print
        def new_print(*args, **kwargs):
            old_print(args[0].replace('HTTP', 'HTTPS').replace('http', 'https'),
                **kwargs)
            builtins.print = old_print
        builtins.print = new_print

def ssl_wrap(socket: socket.socket) -> ssl.SSLSocket:
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    server_root = pathlib.Path(args.directory).resolve()
    
    # Server certificate handling
    server_certificate = pathlib.Path(args.server_certificate).resolve()
    
    if not server_certificate.is_file():
        print(f'Server certificate "{server_certificate}" not found, exiting')
        sys.exit(4)
    
    if server_root in server_certificate.parents:
        print(f'Server certificate "{server_certificate}" is inside web server '
            f'root "{server_root}", exiting')
        sys.exit(3)
    
    try:
        context.load_cert_chain(certfile=server_certificate)
    except ssl.SSLError as e:
        print(f'Unable to load certificate "{server_certificate}", exiting\n\n'
            f'NOTE: Certificate must be a single file in .pem format. If you '
            'have multiple certificate files, such as Let\'s Encrypt provides, '
            'you can cat them together to get one file.')
        sys.exit(4)
    
    if args.client_certificate:
        # Client certificate handling
        client_certificate = pathlib.Path(args.client_certificate).resolve()
        
        if not client_certificate.is_file():
            print(f'Client certificate "{client_certificate}" not found, '
                'exiting')
            sys.exit(4)
        
        if server_root in client_certificate.parents:
            print(f'Client certificate "{client_certificate}" is inside web '
                f'server root "{server_root}", exiting')
            sys.exit(3)
    
        context.load_verify_locations(cafile=client_certificate)
        context.verify_mode = ssl.CERT_REQUIRED
    
    try:
        return context.wrap_socket(socket, server_side=True)
    except ssl.SSLError as e:
        print('SSL error: "{}", exiting'.format(e))
        sys.exit(5)

def serve_forever():
    # Verify arguments in case the method was called directly
    assert hasattr(args, 'port') and type(args.port) is int
    assert hasattr(args, 'cgi') and type(args.cgi) is bool
    assert hasattr(args, 'allow_replace') and type(args.allow_replace) is bool
    assert hasattr(args, 'bind')
    assert hasattr(args, 'theme')
    assert hasattr(args, 'server_certificate')
    assert hasattr(args, 'client_certificate')
    assert hasattr(args, 'basic_auth')
    assert hasattr(args, 'basic_auth_upload')
    assert hasattr(args, 'directory') and type(args.directory) is str
    
    if args.cgi:
        handler_class = CGIHTTPRequestHandler
    else:
        handler_class = functools.partial(SimpleHTTPRequestHandler,
            directory=args.directory)
    
    print('File upload available at /upload')
    
    class DualStackServer(http.server.ThreadingHTTPServer):
        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            bind = super().server_bind()
            if args.server_certificate:
                self.socket = ssl_wrap(self.socket)
            return bind
    server_class = DualStackServer
    
    # Enforce safety: If no authentication is configured, prevent infinite run
    has_auth = args.basic_auth or args.basic_auth_upload or args.client_certificate
    if not has_auth and args.timeout <= 0:
        print('\n[Security Warning] Running without authentication. Forcing auto-shutdown in 300 seconds.')
        args.timeout = 300

    # Auto-shutdown logic
    if args.timeout > 0:
        print(f'\n[Auto-Shutdown] Server will automatically shut down in {args.timeout} seconds.')
        if has_auth:
             print(f'[Auto-Shutdown] Pass --timeout 0 to disable this behavior.\n')
        else:
             print(f'[Auto-Shutdown] Authentication required to disable auto-shutdown.\n')
        shutdown_timer = threading.Timer(args.timeout, lambda: os._exit(0))
        shutdown_timer.daemon = True
        shutdown_timer.start()
    else:
        print(f'\n[Auto-Shutdown] Disabled. Server will run indefinitely.\n')

    if args.qr:
        print_qr_codes()
        
    intercept_first_print()
    http.server.test(
        HandlerClass=handler_class,
        ServerClass=server_class,
        port=args.port,
        bind=args.bind,
    )

def get_shutdown_timer_injection() -> bytes:
    if args.timeout <= 0:
        return b'''
        <div style="position:fixed; top:10px; right:10px; background: #dc3545; color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; z-index: 9999; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            &#9888; Auto-Shutdown Disabled
        </div>
        '''
    else:
        return f'''
        <div id="shutdown-timer" style="position:fixed; top:10px; right:10px; background: #28a745; color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; z-index: 9999; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            Shutdown in: <span id="time-remaining">{args.timeout}</span>s
        </div>
        <script>
            let seconds = {args.timeout};
            const timerSpan = document.getElementById('time-remaining');
            const timerDiv = document.getElementById('shutdown-timer');
            
            setInterval(() => {{
                seconds--;
                if (seconds < 0) {{
                    timerDiv.style.background = '#dc3545';
                    timerDiv.textContent = 'Server Shutting Down...';
                    return;
                }}
                timerSpan.textContent = seconds;
                
                if (seconds < 60) {{
                    timerDiv.style.background = '#ffc107'; // yellow warning
                    timerDiv.style.color = 'black';
                }}
                if (seconds < 10) {{
                    timerDiv.style.background = '#dc3545'; // red critical
                    timerDiv.style.color = 'white';
                }}
            }}, 1000);
        </script>
        '''.encode('utf-8')

# We need to monkey-patch DIRECTORY_BODY_INJECTION usage or append to it dynamically
# But DIRECTORY_BODY_INJECTION is a constant. 
# Better strategy: Modify DIRECTORY_BODY_INJECTION definition to include a placeholder or append at runtime?
# Since DIRECTORY_BODY_INJECTION is used in list_directory (ListDirectoryInterception), 
# let's update ListDirectoryInterception to append this.


def print_qr_codes():
    try:
        import qrcode
    except ImportError:
        print('\nTip: Install "qrcode" to see a QR code for mobile connection:')
        print('      pip install updownserver[qr]\n')
        return

    protocol = 'https' if args.server_certificate else 'http'
    port = args.port
    
    # Determine IPs to display
    ips = []
    if args.bind and args.bind != '0.0.0.0' and args.bind != '::':
        ips = [args.bind]
    else:
        try:
            # Best effort to find LAN IPs without external dependencies
            hostname = socket.gethostname()
            _, _, all_ips = socket.gethostbyname_ex(hostname)
            ips = [ip for ip in all_ips if not ip.startswith('127.')]
        except Exception:
            pass

    if not ips:
        return

    print('\nScan to connect from mobile:')
    for ip in ips:
        url = f'{protocol}://{ip}:{port}/'
        # qrcode.make() returns an image, relying on terminal support is tricky
        # Better to use qrcode.ConsoleASCIIQRCode (if available) or print_ascii
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make(fit=True)
        
        print(f'  > {url}')
        try:
            # Try to print inverted for better compatibility with dark terminals
            qr.print_ascii(invert=True)
        except Exception:
            qr.print_ascii()
    print('')

def main():
    global args
    
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int, default=8000, nargs='?',
        help='Specify alternate port [default: 8000]')
    parser.add_argument('--cgi', action='store_true',
        help='Run as CGI Server')
    parser.add_argument('--allow-replace', action='store_true', default=False,
        help='Replace existing file if uploaded file has the same name. Auto '
        'rename by default.')
    parser.add_argument('--bind', '-b', metavar='ADDRESS',
        help='Specify alternate bind address [default: all interfaces]')
    parser.add_argument('--directory', '-d', default=os.getcwd(),
        help='Specify alternative directory [default:current directory]')
    parser.add_argument('--theme', type=str, default='auto',
        choices=['light', 'auto', 'dark'],
        help='Specify a light or dark theme for the upload page '
        '[default: auto]')
    parser.add_argument('--server-certificate', '--certificate', '-c',
        help='Specify HTTPS server certificate to use [default: none]')
    parser.add_argument('--client-certificate',
        help='Specify HTTPS client certificate to accept for mutual TLS '
        '[default: none]')
    parser.add_argument('--basic-auth',
        help='Specify user:pass for basic authentication (downloads and '
        'uploads)')
    parser.add_argument('--basic-auth-upload',
        help='Specify user:pass for basic authentication (uploads only)')
    parser.add_argument('--timeout', type=int, default=300,
        help='Auto-shutdown server after N seconds (0 to disable) [default: 300]')
    parser.add_argument('--qr', action='store_true',
        help='Show QR code at startup')
    
    args = parser.parse_args()
    if not hasattr(args, 'directory'): args.directory = os.getcwd()
    
    serve_forever()
