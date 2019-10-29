import tornado.web
import tornado.websocket
from pykurento import media
from examples import kurento, render_view

import json
import uuid

class HelloWorldHandler(tornado.web.RequestHandler):
    
    def on_event(self, *args, **kwargs):
        print("received event!")
        print(args)
        print(kwargs)

    def get(self):
        render_view(self, "helloworld")

    def post(self):
        sdp_offer = self.request.body
        pipeline = kurento.create_pipeline()
        wrtc = media.WebRtcEndpoint(pipeline)

        wrtc.on_media_session_started_event(self.on_event)
        wrtc.on_media_session_terminated_event(self.on_event)

        sdp_answer = wrtc.process_offer(sdp_offer)
        self.finish(str(sdp_answer))

        # setup recording
        recorder = media.RecorderEndpoint(
            pipeline, uri="file:///tmp/test.webm")
        wrtc.connect(recorder)
        recorder.record()

        # plain old loopback
        # wrtc.connect(wrtc)

        # fun face overlay
        face = media.FaceOverlayFilter(pipeline)
        face.set_overlayed_image(
            "https://raw.githubusercontent.com/minervaproject/pykurento/master/example/static/img/rainbowpox.png", 0, 0, 1, 1)
        wrtc.connect(face)
        face.connect(wrtc)

class HelloWorldWSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print("WebSocket opened!")
        self.session_id = uuid.uuid4()

    def on_message(self, message):

        json_message = json.loads(message)
        id = json_message.get("id")

        if id == "PROCESS_SDP_OFFER":
            self._handle_process_sdp_offer(json_message)
        elif id == "ADD_ICE_CANDIDATE":
            self._handle_add_ice_candidate(json_message)
        elif id == "STOP":
            self._handle_stop(json_message)
        elif id == "ERROR":
            self._handle_error(json_message)
        else:
            print(f"Found invalid message, skipping. Message: ({message}) ")

    def on_close(self):
        # TODO: Release MediaPipeline when closing websocket connection
        print("WebSocket closed!")

    def _handle_process_sdp_offer(self, json_message):

        self.pipeline = kurento.create_pipeline()
        self.wrtc = media.WebRtcEndpoint(self.pipeline)
        self.wrtc.connect(self.wrtc)

        print("webrtcendpoint successfully connected!")

        self.wrtc.on_add_ice_candidate_event(self.on_event)

        sdp_answer = self.wrtc.process_offer(json_message["sdpOffer"])

        message = {
            "id": "PROCESS_SDP_ANSWER",
            "sdpAnswer": sdp_answer 
        }
        self.write_message(json.dumps(message))

        print("gathering candidates")
        self.wrtc.gather_candidates()


    def _handle_add_ice_candidate(self, json_message):
        self.wrtc.add_ice_candidate(json_message["candidate"])

    def _handle_stop(self, json_message):
        print(f"stopping session: {self.session_id}")

    def _handle_error(self, json_message):
        print(f"browser error: ({json_message})")

    def on_event(self, event, *args, **kwargs):
        """ TODO: This runs in its own thread and has no access to the main tornado event 
            loop. We need a way to write this so that we can execute self.write_message()
        """
        candidate = event["candidate"]
        message = {
            "id": "ADD_ICE_CANDIDATE",
            "candidate": candidate
        }
        self.write_message(json.dumps(message))
