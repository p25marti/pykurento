import tornado.web
import tornado.websocket
from examples import render_view
from asyncKurento import (
    KurentoClient,
    media
)

import asyncio
import json
import uuid
import logging

logger = logging.getLogger(__name__)

class HelloWorldHandler(tornado.web.RequestHandler):
    
    def get(self):
        render_view(self, "helloworld")

class HelloWorldWSHandler(tornado.websocket.WebSocketHandler):
    async def open(self):
        logger.info("WebSocket opened!")
        self.session_id = uuid.uuid4()
        self.url = "ws://localhost:8888/kurento"
        self.client = await KurentoClient.build(self.url)

    async def on_message(self, message):

        json_message = json.loads(message)
        id = json_message.get("id")

        if id == "PROCESS_SDP_OFFER":
            await self._handle_process_sdp_offer(json_message)
        elif id == "ADD_ICE_CANDIDATE":
            await self._handle_add_ice_candidate(json_message)
        elif id == "STOP":
            await self._handle_stop(json_message)
        elif id == "ERROR":
            await self._handle_error(json_message)
        else:
            logger.info(f"Found invalid message, skipping. Message: ({message}) ")

    def on_close(self):
        logger.info("WebSocket closed!")

    async def _handle_process_sdp_offer(self, json_message):

        self.pipeline = await self.client.create_pipeline()
        self.wrtc = await media.WebRtcEndpoint.build(self.pipeline)
        await self.wrtc.connect(self.wrtc)

        logger.info("webrtc endpoint connected")

        await self.wrtc.on_add_ice_candidate_event(self._on_event)

        sdp_answer = await self.wrtc.process_offer(json_message["sdpOffer"])

        message = {
            "id": "PROCESS_SDP_ANSWER",
            "sdpAnswer": sdp_answer 
        }
        self.write_message(json.dumps(message))

        logger.info("gathering candidates")
        await self.wrtc.gather_candidates()

        logger.info("starting the recording")
        self.recorder = await media.RecorderEndpoint.build(
            self.pipeline, uri="file:///etc/kurento/videos/test.webm")
        await self.wrtc.connect(self.recorder)
        await self.recorder.record()

    async def _handle_add_ice_candidate(self, json_message):
        await self.wrtc.add_ice_candidate(json_message["candidate"])

    async def _handle_stop(self, json_message):
        logger.info(f"stopping session: {self.session_id}")
        await self.pipeline.release()

    async def _handle_error(self, json_message):
        logger.warning(f"browser error: ({json_message})")
        await self.pipeline.release()

    def _on_event(self, event, *args, **kwargs):
        candidate = event["candidate"]
        message = {
            "id": "ADD_ICE_CANDIDATE",
            "candidate": candidate
        }
        self.write_message(json.dumps(message))
