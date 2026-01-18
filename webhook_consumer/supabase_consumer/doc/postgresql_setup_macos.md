# PostgreSQL Detailed Setup Guide for macOS

- **Example Custom Path:** `/Users/yourname/my-postgres/binaries`

```bash
# Example: Moving extracted folder to a custom location
mv ~/Downloads/pgsql /Users/van.tran_fgorg/my-postgres/binaries
```

### Step 1.3: Add to PATH (Optional but Recommended)

To run commands like `psql` and `pg_ctl` easily, add the `bin` directory to your path.

- Open `~/.zshrc` or `~/.bash_profile`.
- Add: `export PATH="/Users/van.tran_fgorg/my-postgres/binaries/bin:$PATH"`
- Reload: `source ~/.zshrc`

### Step 1.4: System User Recommendation

- **Run as your current user**: On macOS, especially for development, it is standard practice to run the PostgreSQL process as your current login user (e.g., `van.tran_fgorg`). This avoids permission issues with directories in your home folder.
- **Do NOT run as root**: PostgreSQL will refuse to start if run as root for security reasons.
- **Database User**: You will still create a database superuser named `postgres` (in Step 2.2), but the _process_ itself runs as you.

---

## 2. Customize Data Folder

This is where the actual database tables and files will be stored. You can locate this anywhere (e.g., an external drive or a specific project folder).

### Step 2.1: Create the Data Directory

```bash
# Create your custom data directory
mkdir -p /Users/van.tran_fgorg/my-postgres/data
```

### Step 2.2: Initialize the Database (`initdb`)

Initialize the database cluster pointing to your custom folder. You must specify a superuser (usually your system username) and an auth method.

```bash
# Syntax: initdb -D [DATA_FOLDER] -U [USERNAME] --auth=local=trust
initdb -D /Users/van.tran_fgorg/my-postgres/data -U postgres --auth=md5 --pwfile=<(echo "your_secure_password")
```

- `-D`: Specifies the custom data directory.
- `-U`: Specifies the superuser name (e.g., `postgres`).
- `--auth=md5`: Sets default authentication to password-based (recommended over `trust`).

---

## 3. Configuration & File Locations

In a custom setup, your configuration files are located **inside your custom data directory**.

- **Main Config:** `/Users/van.tran_fgorg/my-postgres/data/postgresql.conf`
- **Auth Config:** `/Users/van.tran_fgorg/my-postgres/data/pg_hba.conf`

### Step 3.1: Customize `postgresql.conf`

Open `postgresql.conf` to adjust network and performance settings.

```bash
nano /Users/van.tran_fgorg/my-postgres/data/postgresql.conf
```

**Key settings to check:**

- `listen_addresses = '*'` (Allows remote connections; set to `'localhost'` to restrict).
- `port = 5432` (Change if you want a custom port).
- `logging_collector = on` (Enable logs).
- `log_directory = 'log'` (Logs will be stored in `.../data/log`).

---

## 4. Authenticate Setup (User and Host)

Authentication is controlled by `pg_hba.conf` (Host-Based Authentication).

### Step 4.1: Configure `pg_hba.conf`

Open the file:

```bash
nano /Users/van.tran_fgorg/my-postgres/data/pg_hba.conf
```

**Recommended Setup:**
Add or modify lines to control who can access what.

```conf
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust

# IPv4 local connections:
# Allow 'postgres' user from localhost with a password
host    all             postgres        127.0.0.1/32            scram-sha-256

# Allow specific user 'app_user' from a specific IP subnet
host    my_db           app_user        192.168.1.0/24          scram-sha-256
```

- **trust**: No password required (use carefully, mainly for local sockets).
- **scram-sha-256**: Secure password authentication (recommended over md5).

### Step 4.2: Create Users (After starting service)

Once the service is running (see Section 5), you can create users.

```bash
# Connect as the superuser created during initdb
psql -d postgres -U postgres

# SQL commands inside psql:
CREATE USER app_user WITH PASSWORD 'secure_pass';
CREATE DATABASE my_db OWNER app_user;
GRANT ALL PRIVILEGES ON DATABASE my_db TO app_user;
```

---

## 5. Start / Stop / Restart Service

Since we installed manually, we use `pg_ctl` directly. This is often more reliable than `brew services` for custom paths.

**Define an alias** (optional) in your `.zshrc` for easier management:
`export PGDATA="/Users/van.tran_fgorg/my-postgres/data"`

### Start Server

```bash
# If PGDATA is exported:
pg_ctl start

# If PGDATA is NOT exported, specify it explicitly:
pg_ctl -D /Users/van.tran_fgorg/my-postgres/data -l /Users/van.tran_fgorg/my-postgres/data/logfile start
```

### Stop Server

```bash
pg_ctl -D /Users/van.tran_fgorg/my-postgres/data stop
```

### Restart Server (Reload Config)

```bash
pg_ctl -D /Users/van.tran_fgorg/my-postgres/data restart
```

---

## 6. Validate Configuration

### Step 6.1: Check Service Status

```bash
pg_ctl -D /Users/van.tran_fgorg/my-postgres/data status
```

_Output should show "server is running" and the PID._

### Step 6.2: Validate Connection

Use `pg_isready` to check if the server is accepting connections.

```bash
pg_isready -h localhost -p 5432
```

### Step 6.3: Verify Config Loaded

Connect via `psql` and query the settings to ensure your custom config is active.

```bash
psql -U postgres -c "SHOW data_directory;"
psql -U postgres -c "SHOW config_file;"
```

_This should return your custom paths._

---

## 7. Auto-Backup & Restore

Regular backups are crucial. We will use `pg_dump` for backups and `psql` or `pg_restore` for restoration.

### 7.1 Manual Backup

To back up a specific database (e.g., `my_db`) to a file:

```bash
# Syntax: pg_dump -U [USER] -h [HOST] [DB_NAME] > [OUTPUT_FILE]
pg_dump -U postgres -h localhost my_db > /Users/van.tran_fgorg/my-postgres/backups/my_db_backup.sql
```

For a compressed, custom format (better for large DBs):

```bash
pg_dump -U postgres -h localhost -F c -b -v -f "/Users/van.tran_fgorg/my-postgres/backups/my_db_backup.dump" my_db
```

### 7.2 Auto-Backup (Cron Job)

You can automate this using macOS `cron`.

1.  **Create a Backup Script** (`backup_script.sh`):

    ```bash
    #!/bin/bash
    # Set variables
    BACKUP_DIR="/Users/van.tran_fgorg/my-postgres/backups"
    DATE=$(date +%Y-%m-%d_%H%M%S)
    DB_NAME="my_db"

    # Ensure backup directory exists
    mkdir -p $BACKUP_DIR

    # Perform backup
    /Users/van.tran_fgorg/my-postgres/binaries/bin/pg_dump -U postgres -h localhost -F c -b -v -f "$BACKUP_DIR/$DB_NAME_$DATE.dump" $DB_NAME

    # Cleanup: Keep only the last 7 backup files
    # List files by time (newest first), skip the first 7, and delete the rest
    cd "$BACKUP_DIR" && ls -1t *.dump 2>/dev/null | tail -n +8 | xargs rm -f
    ```

2.  **Make it executable**:

    ```bash
    chmod +x /path/to/backup_script.sh
    ```

3.  **Add to Crontab**:
    Open crontab editor:
    ```bash
    crontab -e
    ```
    Add line to run every day at 2 AM:
    ```bash
    0 2 * * * /path/to/backup_script.sh
    ```

### 7.3 Restore Database

**Option A: Restore from SQL file (Plain text)**
If you used the standard `> output.sql` method:

```bash
psql -U postgres -h localhost -d my_db -f /Users/van.tran_fgorg/my-postgres/backups/my_db_backup.sql
```

**Option B: Restore from Custom Dump (`.dump`)**
If you used `-F c` (Custom format):

```bash
# Syntax: pg_restore -U [USER] -h [HOST] -d [DB_NAME] [DUMP_FILE]
pg_restore -U postgres -h localhost -d my_db -v "/Users/van.tran_fgorg/my-postgres/backups/my_db_backup.dump"
```

_Note: You might need to create the database first (`CREATE DATABASE my_db;`) if it doesn't exist._
