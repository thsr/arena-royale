from google.cloud import storage
import os
from urllib.parse import urlparse
import requests


class GCStuff:
    def __init__(self, cred_file, bucket):
        self.storage_client = storage.Client.from_service_account_json(cred_file)
        self.bucket = self.storage_client.get_bucket(bucket)

    def upload_to_gcs(self, source_url, destination, make_public=False):
        """destination folder and filename has to be specified"""
        blob = self.bucket.blob(destination)
        f = requests.get(source_url)
        blob.upload_from_string(data=f.content, content_type=f.headers['Content-Type'])
        if make_public:
            blob.make_public()
        return str(blob.public_url)

    def upload_to_gcs_folder(self, source_url, folder, make_public=False):
        """keeps the same filename as origin url"""
        parsed = urlparse(source_url)
        filename = os.path.basename(parsed.path)
        destination = os.path.join(folder, filename)
        return self.upload_to_gcs(url, destination, make_public)

    def check_if_file_exists(self, file):
        return storage.Blob(bucket=self.bucket, name=file).exists(self.storage_client)

    def get_public_url(self, file):
        return self.bucket.blob(file).public_url


gc_stuff = GCStuff(os.environ.get('GCS_CRED_FILE'), os.environ.get('GCS_BUCKET'))