from collections import MutableMapping
import logging
import os
from urllib.parse import urlparse




logging.basicConfig(filename='./app.2.log',level=logging.WARNING,format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')




def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def generate_epoch_filename(ext="jpg"):
    return str(int(datetime.now().timestamp()*1000)) + "." + ext

def millis_now():
    return str(int(datetime.now().timestamp()*1000))

def extract_file_name(url):
    parsed = urlparse(url)
    return os.path.basename(parsed.path)

def extract_file_extension(url):
    return os.path.splitext(extract_file_name(url))[1]