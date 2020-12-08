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

CRON_ENABLED=TRUE

BASIC_AUTH_USERNAME=user
BASIC_AUTH_PASSWORD=pass
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
- run the app on `localhost:5036`
- setup cron to call the `/backup` endpoint everyday at 4:45am UTC

When adding new packages to `requirements.txt`:

```bash
$ docker-compose up --build -d
```

Usage
-----

### Endpoints:

Create and back up new blocks and channels for user:
```
curl -X POST localhost:5036/backup
```

Delete the entire database, then back up everything:
```
curl -X POST localhost:5036/backup/reset
```

### Views:

All backed up blocks and channels:
- `localhost:5036/blocks`
- `localhost:5036/blocks/<page number>` with pagination
- `localhost:5036/blocks?nsfw=1` includes blocks from channels with "private" status

All backed up blocks and channels for **\<channel id\>**:
- `localhost:5036/blocks?channel=<channel id>`
