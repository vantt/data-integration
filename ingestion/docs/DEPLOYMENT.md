# Deployment Guide: Sapo Orders Pipeline (DLT)

This guide details how to deploy and run the Sapo Orders Pipeline in a production environment.

## 1. Prerequisites

- **OS**: Linux (recommended for production) or Windows.
- **Python**: Version 3.8 or higher.
- **Hardware**:
  - Minimum 1 CPU, 2GB RAM (Playwright requires sufficient memory for headless browser).
  - Disk space for logs and local data storage.

## 2. Project Structure

The project uses a Python `src-layout`:

```
dlt/
├── run_sapo_orders.py       # Entry point script
├── requirements.txt         # Dependencies
├── .dlt/
│   ├── secrets.toml         # Credentials (DO NOT COMMIT)
│   └── config.toml          # DLT config
└── src/
    ├── sapo/                # Sapo source logic
    └── utils/               # Shared utilities (Cookie Manager)
```

## 3. Installation

1.  **Clone/Copy Project**:
    Copy the `dlt` folder to your server.

2.  **Create Virtual Environment** (Recommended):

    ```bash
    python -m venv venv

    # Linux/Mac
    source venv/bin/activate

    # Windows
    venv\Scripts\activate
    ```

3.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright Browsers**:
    This is required for the login process.
    ```bash
    playwright install chromium
    ```
    _Note: On some Linux distributions (like Ubuntu Server), you may need to install minimal system dependencies:_
    ```bash
    playwright install-deps
    ```

## 4. Configuration

1.  **Secrets File**:
    Create `.dlt/secrets.toml` if it doesn't exist.

    ```toml
    [sources.sapo]
    login_url = "https://fwg.mysapogo.com/admin/orders"
    username = "YOUR_PRODUCTION_USERNAME"
    password = "YOUR_PRODUCTION_PASSWORD"
    base_url = "https://fwg.mysapogo.com/admin"
    ```

2.  **Environment Variables** (Optional alternative):
    You can also provide secrets via environment variables:
    ```bash
    export SOURCES__SAPO__USERNAME="your_user"
    export SOURCES__SAPO__PASSWORD="your_password"
    ```

## 5. Execution

### Manual Run

Run the pipeline from the project root:

```bash
python run_sapo_orders.py
```

### Scheduled Run (Cron)

To run hourly, add to crontab:

```bash
# Edit crontab
crontab -e

# Add line (runs at minute 0 of every hour)
0 * * * * cd /path/to/dlt && /path/to/dlt/venv/bin/python run_sapo_orders.py >> /path/to/dlt/logs/cron.log 2>&1
```

## 6. Maintenance & Troubleshooting

### Cookie Expiry

- The system automatically handles login and cookie refreshing (default TTL: 6 hours).
- Cookies are stored in `.cookies/sapo_cookies.json`.
- **Issue**: If login fails repeatedly (e.g., CAPTCHA or password change), check the logs.
- **Fix**: Delete `.cookies/sapo_cookies.json` to force a fresh login attempt.

### File Locking

- The system uses file locking to support concurrent runs safely.
- On Windows, ensure no other process has the cookie file open if you encounter locking errors.

### Browser Issues

- If Playwright fails to launch, ensure system dependencies are installed (`playwright install-deps`).
- Running as `root` is generally discouraged for Chrome; use a standard user.
