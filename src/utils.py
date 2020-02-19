from collections import MutableMapping
import logging
import os
import re
import cv2
from urllib.parse import urlparse


logging.basicConfig(filename='./app.4.log',level=logging.WARNING,format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')


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

def video_to_thumbnail(video_filename, id):
    """Extract frames from video"""
    video_filename = re.sub('^https', 'http', video_filename)
    cap = cv2.VideoCapture(video_filename)
    if not cap.isOpened():
        logging.error("Couldn't open webm from url")
        return None
    while(True):
        # Capture frame-by-frame
        ret, frame = cap.read()
        if frame is not None:
            thumbnail_file = './%s_webm_thumb.png' % str(id)
            cv2.imwrite(thumbnail_file, frame)
        break
    return thumbnail_file