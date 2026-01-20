# updownserver

一個輕量級的 Python HTTP 伺服器，整合了統一的上傳/下載介面。
基於 Densaugeo 優異的 [uploadserver](https://github.com/Densaugeo/uploadserver) 專案修改而來。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://mit-license.org/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/updownserver?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/updownserver)
![Vibe Coding](https://img.shields.io/badge/Built%20with-Vibe%20Coding-FF69B4?style=flat-square)

## 主要功能

*   **統一介面**：在單一頁面中進行拖曳上傳、檔案管理與下載。
*   **檔案管理**：直接從網頁介面建立資料夾和刪除檔案。
*   **行動友善**：在終端機產生 QR Code，方便手機掃描連線。
*   **安全優先**：預設自動關機計時器 (5分鐘)，並強制限制未認證連線的執行時間。
*   **Docker 支援**：提供 Dockerfile 供容器化部署使用。
*   **零依賴**：核心功能完全使用 Python 標準函式庫。

## 支援平台

| 平台 | 支援狀態 | 備註 |
|---|---|---|
| Python 3.9+ | 是 | 針對 3.9 到 3.14 的每個版本進行測試。 |
| Python 3.6-3.8 | 否 | 舊版本曾支援，但已不再維護。 |
| Python 3.5- | 否 | |
| Linux | 是 | 針對 Fedora 和 Ubuntu 每個發行版進行測試。 |
| Windows | 是 | 偶爾進行手動測試，目前未發現明顯問題。 |
| Mac | 不確定 | 我沒有 Mac，不確定是否能運作。 |

## 安裝

~~~bash
python3 -m pip install --user updownserver
# 選用：安裝 QR code 支援所需的套件
python3 -m pip install --user updownserver[qr]

# 或使用 uv (推薦，速度更快)
uv pip install updownserver[qr]
~~~

## Docker 支援

建置映像檔：
~~~bash
docker build -t updownserver .
~~~

執行並分享當前目錄 (掛載至容器內的 `/data`)：
~~~bash
# Linux/Mac
docker run -p 8000:8000 -v $(pwd):/data updownserver

# Windows (PowerShell)
docker run -p 8000:8000 -v ${PWD}:/data updownserver
~~~

執行並帶入自訂參數 (例如：關閉自動關機功能)：
~~~bash
docker run -p 8000:8000 -v $(pwd):/data updownserver --timeout 0 --basic-auth user:pass
~~~

## 使用說明

啟動伺服器：
~~~bash
python3 -m updownserver
~~~

顯示手機連線用的 QR Code (需要安裝 `updownserver[qr]`)：
~~~bash
python3 -m updownserver --qr
~~~

為避免忘記關閉伺服器，預設會在 300 秒 (5分鐘) 後自動關機。
若要永久執行 (**基於安全考量必須設定認證**)：
~~~bash
python3 -m updownserver --timeout 0 --basic-auth user:pass
~~~

伺服器啟動後，您可以在**根目錄**看到整合好的上傳/下載介面。

這個主頁面允許您：
- **下載檔案**：點擊列表中的任何檔案即可下載。
- **上傳檔案**：將檔案拖放到頁面頂部的上傳區域，或使用檔案選擇器。
- **管理檔案**：直接從 UI 建立新資料夾或刪除檔案 (垃圾桶圖示)。(**注意**：基於安全考量，若未設定認證，這些功能將被自動停用。)

`/upload` 這個 POST 端點仍然保留，供程式化存取（例如 cURL）使用。

警告：這是一個上傳伺服器，執行它將允許任何人上傳檔案到您的電腦。

支援同時上傳多個檔案！在網頁的檔案選擇器中選取多個檔案，或使用 cURL 上傳：
~~~bash
curl -X POST http://127.0.0.1:8000/upload -F 'files=@multiple-example-1.txt' -F 'files=@multiple-example-2.txt'
~~~

## 基本認證 (Basic Authentication) - 下載與上傳

~~~bash
python3 -m updownserver --basic-auth hello:world
~~~

現在您上傳時需要基本認證。例如：
~~~bash
curl -X POST http://127.0.0.1:8000/upload -F 'files=@basicauth-example.txt' -u hello:world
~~~

所有未經認證的請求都會被拒絕。請注意，如果透過純 HTTP 傳送，基本認證的憑證可能會被竊取，因此建議搭配 HTTPS 使用此選項。

## 基本認證 (Basic Authentication) - 僅上傳

~~~bash
python3 -m updownserver --basic-auth-upload hello:world
~~~

與上述相同，但只有「上傳操作」需要認證。

如果同時指定了 `--basic-auth` 和 `--basic-auth-upload`，所有請求都需要其中一組憑證，但只有使用 `--basic-auth-upload` 的憑證才能上傳檔案。

## 佈景主題選項

上傳頁面支援深色模式（Dark Mode），在黑色背景顯示白色文字。如果未指定選項，將根據用戶瀏覽器的偏好設定自動選擇（通常會跟隨作業系統設定）。若要強制使用淺色或深色主題，可以使用 CLI 參數 `--theme`：
~~~bash
python3 -m updownserver --theme light
~~~
或是
~~~bash
python3 -m updownserver --theme dark
~~~

## HTTPS 選項

使用 HTTPS 執行，但不驗證客戶端憑證：
~~~bash
# 產生自簽伺服器憑證
openssl req -x509 -out server.pem -keyout server.pem -newkey rsa:2048 -nodes -sha256 -subj '/CN=server'

# 基於安全考量，伺服器根目錄不應包含憑證檔案
cd server-root
python3 -m updownserver --server-certificate server.pem

# 作為客戶端連接
curl -X POST https://localhost:8000/upload --insecure -F files=@simple-example.txt
~~~

使用 HTTPS 執行，並驗證客戶端憑證 (mTLS)：
~~~bash
# 產生自簽伺服器憑證
openssl req -x509 -out server.pem -keyout server.pem -newkey rsa:2048 -nodes -sha256 -subj '/CN=server'

# 產生自簽客戶端憑證
openssl req -x509 -out client.pem -keyout client.pem -newkey rsa:2048 -nodes -sha256 -subj '/CN=client'

# 從自簽客戶端憑證中提取公鑰
openssl x509 -in client.pem -out client.crt

# 基於安全考量，伺服器根目錄不應包含憑證檔案
cd server-root
python3 -m updownserver --server-certificate server.pem --client-certificate client.crt

# 作為客戶端連接
curl -X POST https://localhost:8000/upload --insecure --cert client.pem -F files=@mtls-example.txt
~~~

注意：這裡使用的是自簽憑證，瀏覽器或 cURL 等客戶端會發出警告。大多數瀏覽器允許您新增例外後繼續訪問，cURL 則需加上 `-k`/`--insecure` 選項。使用來自憑證授權單位 (CA) 的憑證可避免這些警告。

## 可用選項

```
usage: __main__.py [-h] [--cgi] [--allow-replace] [--bind ADDRESS]
                   [--directory DIRECTORY] [--theme {light,auto,dark}]
                   [--server-certificate SERVER_CERTIFICATE]
                   [--client-certificate CLIENT_CERTIFICATE]
                   [--basic-auth BASIC_AUTH]
                   [--basic-auth-upload BASIC_AUTH_UPLOAD]
                   [--timeout TIMEOUT] [--qr]
                   [port]

positional arguments:
  port                  指定替代連接埠 [預設: 8000]

options:
  -h, --help            顯示此幫助訊息並退出
  --cgi                 作為 CGI 伺服器執行
  --allow-replace       如果上傳的檔案檔名已存在，則覆蓋它。預設行為是自動重新命名。
  --bind, -b ADDRESS    指定替代綁定地址 [預設: 所有介面]
  --directory, -d DIRECTORY
                        指定替代目錄 [預設: 當前目錄]
  --theme {light,auto,dark}
                        指定上傳頁面的主題 (淺色/深色) [預設: auto]
  --server-certificate, --certificate, -c SERVER_CERTIFICATE
                        指定使用的 HTTPS 伺服器憑證 [預設: 無]
  --client-certificate CLIENT_CERTIFICATE
                        指定接受的 HTTPS 客戶端憑證，用於雙向 TLS (mTLS)驗證 [預設: 無]
  --basic-auth BASIC_AUTH
                        指定 user:pass 進行基本認證 (下載與上傳皆需)
  --basic-auth-upload BASIC_AUTH_UPLOAD
                        指定 user:pass 進行基本認證 (僅上傳需)
  --timeout TIMEOUT     自動在 N 秒後關閉伺服器 (0 代表禁用)
                        [預設: 300]
  --qr                  在啟動時顯示 QR Code
```

## 致謝 (Acknowledgements)

特別感謝 [Densaugeo](https://github.com/Densaugeo) 以及原 [uploadserver](https://github.com/Densaugeo/uploadserver) 專案的所有貢獻者，為此工具提供了堅實的基礎。
