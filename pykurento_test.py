#!/usr/bin/env python

import sys
from time import sleep
import logging

from pykurento import (
    media,
    KurentoClient
)

# Logging
root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
root.addHandler(handler)

# Actual fun
uri = "ws://localhost:8888/kurento"
kurento = KurentoClient(uri)
sleep(1)

pipeline = kurento.create_pipeline()
wrtc = media.WebRtcEndpoint(pipeline)
