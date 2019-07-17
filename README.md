Are.na Royale
=============

*️⃣ A tool to periodically back up the full contents of Are.na blocks and channels in Google Cloud Storage.

Settings
--------

Create a `.env` file in the same directory as `docker-compose.yml` and add the following settings (all required).

```
ARENA_API_TOKEN=abc123
ARENA_USER_ID=12345

NEO4J_AUTH=neo4j/pass
NEO4J_USER=neo4j
NEO4J_PASSWORD=pass

GCS_PROJECT=project
GCS_BUCKET=bucket
GCS_ARCHIVE_FOLDER=archivefolder
GCS_CRED_FILE=./gcskey.json
```

- `ARENA_API_TOKEN`: to obtain an API token, register an app on https://dev.are.na/.

- `ARENA_USER_ID` is the user to backup. To find out the user ID with a known user slug:
    ```
    curl -X GET https://api.are.na/v2/users/<your-slug-here>
    ```

- Neo4j login/password: free to choose.

- Create a Google Cloud Storage project, bucket, folder, and service account key (json) and paste their names here. The service account json has to be in the same directory as `app.py`.

Install and run
---------------

With Docker installed, execute:

```bash
$ docker-compose up -d
```

This will:
- start a Neo4j database and create 2 folders for Neo4j data & logs
- run the app on `localhost:5000`
- setup cron to call the `/backup` endpoint everyday at 4:45am UTC

Usage
-----

### Endpoints:

Create and back up new blocks and channels for user:
```
curl -X POST localhost:5000/backup
```

Delete the entire database, then back up everything:
```
curl -X POST localhost:5000/backup/reset
```

### Views:

All backed up blocks and channels:
- `localhost:5000/all`
- `localhost:5000/all?skip=200&limit=50` with pagination

All backed up blocks and channels for **\<channel id\>**:
- `localhost:5000/all?channel=<channel id>`
