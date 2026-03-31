# Metabase Data Migration (H2 to H2)

Since you are keeping the default H2 database, migration is simply copying the database file.

## 1. Locate the Database File (Source Machine)

You need to find the file named `metabase.db.mv.db`.

- **If running via Java (Jar)**: It is usually in the same folder where you ran the command.
- **If running via Docker**: It is inside the container.
  - Run: `docker cp <container_name_or_id>:/home/metabase/data/metabase.db ./metabase.db`
  - (Note: Check the path inside the container, default is often root `/` or `/home/metabase/data/`).

docker cp 52fb2aa550c4:/home/metabase/data/metabase.mv.db ./metabase.mv.db

## 2. Copy to Target Machine

1.  On your new Windows machine (target), go to the project folder.
2.  Create a folder named `metabase_data` (if not exists).
3.  Copy your `metabase.db` file **INTO** this `metabase_data` folder.

## 3. Verify

Your folder structure should look like this:

```
project-folder/
  ├── docker-compose.yml
  ├── metabase_data/
  │     └── metabase.db.mv.db
  └── ...
```

## 4. Start Metabase

Run your deployment script:

```powershell
.\scripts\secure_deploy.ps1
```

Metabase will detect the file at `/home/metabase/data/metabase.db` and load your old data.
