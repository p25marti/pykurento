#!/usr/bin/env python

import asyncio
import sys
import logging

from asyncKurento import (
    media,
    KurentoClient
)

logger = logging.getLogger("asyncKurento")
logger.setLevel(logging.WARNING)
logger.addHandler(logging.StreamHandler(sys.stdout))

async def main():
    url = "ws://localhost:8888/kurento"
    client = await KurentoClient.build(url)

    pipeline = await client.create_pipeline()
    wrtc = await media.WebRtcEndpoint.build(pipeline)
    await wrtc.connect(wrtc)
    await pipeline.release()


asyncio.get_event_loop().run_until_complete(main())
