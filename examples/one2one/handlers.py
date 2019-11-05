import tornado.web
import tornado.websocket
from examples import render_view
from OwlKurentoClient import (
    KurentoClient,
    media
)

import asyncio
import json
import uuid
import logging
import timeit

logger = logging.getLogger(__name__)

class One2OneHandler(tornado.web.RequestHandler):
    
    def get(self):
        render_view(self, "one2one")

class One2OneWSHandler(tornado.websocket.WebSocketHandler):

    # Dict in the form { "<name>": {"handler": handler} }
    users = {}

    # Dict in the form of {"<session_id>": [candidates]}
    pending_candidates = {}

    # Dict in the form {"<call_id>": CallMediaPipeline}
    pipelines = {}

    async def open(self):
        logger.debug("WebSocket opened!")
        self.session_id = uuid.uuid4()
        self.url = "ws://localhost:8888/kurento"
        self.client = await KurentoClient.build(self.url)

    async def on_message(self, json_message):

        message = json.loads(json_message)
        id = message.get("id")

        if id == "register":
            self._handle_register(message)
        elif id == "call":
            self._handle_call(message)
        elif id == "incomingCallResponse":
            await self._handle_incoming_call_response(message)
        elif id == "onIceCandidate":
            await self._handle_on_ice_candidate(message)
        elif id == "stop":
            await self._handle_stop(message)
        else:
            logger.warn(f"Found invalid message, skipping. Message: ({message}) ")

    def on_close(self):
        logger.info("WebSocket closed!")
        name, _ = self._get_user_by_session_id(self.session_id)
        if (name):
            logger.debug(f"removing {name} from user registry")
            del One2OneWSHandler.users[name]
        
        if "session_id" in One2OneWSHandler.pending_candidates:
            del One2OneWSHandler.pending_candidates[session_id]

    def _handle_register(self, message):
        name = message.get("name")

        if (name and name not in One2OneWSHandler.users):
            user = { name: {"handler": self} }
            logger.debug(f"adding {name} to user registry")
            One2OneWSHandler.users.update(user)
            result = "accepted"
        else:
            result = "rejected" 

        response = {
            "id": "registerResponse",
            "response": result
        }
        self.write_message(json.dumps(response))

    def _handle_call(self, message):
        call_to = message.get("to")
        call_from = message.get("from")

        if call_to in One2OneWSHandler.users:
            self.sdp_offer = message.get("sdpOffer")
            self.calling_to = call_to

            callee_handler = One2OneWSHandler.users.get(call_to).get("handler")
            response = {
                "id": "incomingCall",
                "from": call_from
            }
            callee_handler.write_message(json.dumps(response))
        else:
            response = {
                "id": "callResponse",
                "response": f"rejected: user '{call_to}' is not registered"
            }
            self.write_message(json.dumps(response))

    async def _handle_incoming_call_response(self, message):
        call_response = message.get("callResponse")
        call_from = message.get("from")
        caller = One2OneWSHandler.users.get(call_from)
        caller_handler = One2OneWSHandler.users.get(call_from).get("handler")
        call_to = caller_handler.calling_to
        callee_handler = One2OneWSHandler.users.get(call_to).get("handler")

        if call_response == "accept":
            logger.debug(f"accepted call from {call_from} to {call_to}")

            call_id = uuid.uuid4()
            caller_handler.call_id = call_id
            callee_handler.call_id = call_id

            pipeline = await CallMediaPipeline.build(self.client)
            pipeline.caller_id = caller_handler.session_id
            pipeline.callee_id = callee_handler.session_id

            logger.debug(f"created media pipeline")

            await pipeline.callee_endpoint.on_add_ice_candidate_event(
                self._create_on_ice_candidate_callback(callee_handler)
            )
            await pipeline.caller_endpoint.on_add_ice_candidate_event(
                self._create_on_ice_candidate_callback(caller_handler)
            )
            logger.debug("subscribed to iceCandidate events")

            callee_sdp_offer = message.get("sdpOffer")
            callee_answer = await pipeline.generate_sdp_answer_for_callee(callee_sdp_offer)
            start_communication = {
                "id": "startCommunication",
                "sdpAnswer": callee_answer
            } 
            callee_handler.write_message(json.dumps(start_communication))
            logger.debug("sent callee 'startCommunication' message")
            await pipeline.callee_endpoint.gather_candidates()

            caller_sdp_offer = caller_handler.sdp_offer
            caller_answer = await pipeline.generate_sdp_answer_for_caller(caller_sdp_offer)
            call_response = {
                "id": "callResponse",
                "response": "accepted",
                "sdpAnswer": caller_answer
            }
            logger.debug("sent caller 'callResponse' message")
            caller_handler.write_message(json.dumps(call_response))
            await pipeline.caller_endpoint.gather_candidates()


            # Transmit all pending ice candidates
            if One2OneWSHandler.pending_candidates:
                for session_id, candidates in One2OneWSHandler.pending_candidates.items():
                    if session_id == pipeline.caller_id:
                        for candidate in candidates:
                            await pipeline.caller_endpoint.add_ice_candidate(candidate)
                    else:
                        for candidate in candidates:
                            await pipeline.callee_endpoint.add_ice_candidate(candidate)

            # Add pipeline to registry so that it can be referenced later
            One2OneWSHandler.pipelines[call_id] = pipeline
        else:
            response = {
                "id": "callResponse",
                "response": "rejected"
            }
            caller_handler.write_message(json.dumps(response))

    async def _handle_on_ice_candidate(self, message):
        candidate = message["candidate"]

        # If we haven't created a pipeline yet, add candidates to a queue to be sorted later
        if not hasattr(self, "call_id"):
            if self.session_id not in One2OneWSHandler.pending_candidates:
                # create first entry
                One2OneWSHandler.pending_candidates.update({self.session_id: [candidate]})
            else:
                # add new entries
                One2OneWSHandler.pending_candidates[self.session_id].append(candidate)

        # # Otherwise send them directly to the right endpoint
        else:
            pipeline = One2OneWSHandler.pipelines.get(self.call_id)
            if self.session_id == pipeline.caller_id:
                await pipeline.caller_endpoint.add_ice_candidate(candidate)
            else:
                await pipeline.callee_endpoint.add_ice_candidate(candidate)

    async def _handle_stop(self, message):
        if hasattr(self, "call_id") and One2OneWSHandler.pipelines.get(self.call_id):
            logger.debug(f"releasing pipeline!")
            await One2OneWSHandler.pipelines[self.call_id].release()

            # Tell other caller to hangup
            for _, value in One2OneWSHandler.users.items():
                handler = value.get("handler")
                if (hasattr(handler, "call_id") 
                    and handler.call_id in One2OneWSHandler.pipelines
                    and handler.session_id is not self.session_id):

                    name, value = self._get_user_by_session_id(handler.session_id)
                    logger.debug(f"telling user: {name} to hang up")
                    handler.write_message(json.dumps({"id": "stopCommunication"}))

            del One2OneWSHandler.pipelines[self.call_id]

    def _get_user_by_session_id(self, session_id):
        for name, data in One2OneWSHandler.users.items():
            if data.get("handler").session_id == session_id:
                return (name, data)
        return (None, None)

    def _create_on_ice_candidate_callback(self, handler):

        def _on_event(event, *args, **kwargs):
            candidate = event["candidate"]
            message = {
                "id": "iceCandidate",
                "candidate": candidate
            }
            handler.write_message(json.dumps(message))
        return _on_event

class CallMediaPipeline(object):

    @classmethod
    async def build(cls, client):
        self = CallMediaPipeline()
        self.pipeline = await client.create_pipeline()
        self.caller_endpoint = await media.WebRtcEndpoint.build(self.pipeline)
        self.callee_endpoint = await media.WebRtcEndpoint.build(self.pipeline)

        await self.caller_endpoint.connect(self.callee_endpoint)
        await self.callee_endpoint.connect(self.caller_endpoint)

        # adding composite recording
        self.composite = await media.Composite.build(self.pipeline)
        self.recorder = await media.RecorderEndpoint.build(
            self.pipeline, uri="file:///etc/kurento/videos/one2one.webm")

        self.hub_in_port1 = await media.HubPort.build(self.pipeline, self.composite)
        self.hub_in_port2 = await media.HubPort.build(self.pipeline, self.composite)
        self.hub_out_port = await media.HubPort.build(self.pipeline, self.composite)

        await self.caller_endpoint.connect(self.hub_in_port1)
        await self.callee_endpoint.connect(self.hub_in_port2)

        await self.hub_out_port.connect(self.recorder)
        await self.recorder.record()

        return self
        
    async def generate_sdp_answer_for_caller(self, sdp_offer):
        return await self.caller_endpoint.process_offer(sdp_offer)

    async def generate_sdp_answer_for_callee(self, sdp_offer):
        return await self.callee_endpoint.process_offer(sdp_offer)

    async def release(self):
        return await self.pipeline.release()
