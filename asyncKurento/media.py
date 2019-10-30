import logging

logger = logging.getLogger(__name__)

# This is the object graph as described at http://www.kurento.org/docs/5.0.3/mastering/kurento_API.html
# We dont mimic it precisely yet as its still being built out, not all abstractions are necessary
#                   MediaObject
# Hub               MediaElement                MediaPipeline
#          HubPort    Endpoint    Filter

class MediaType(object):
  AUDIO = "AUDIO"
  VIDEO = "VIDEO"
  DATA = "DATA"

class MediaObject(object):

  @classmethod
  async def build(cls, parent, **args):
    self = cls()
    self.parent = parent
    self.options = args
    if 'id' in args:
      logger.debug(f"Creating existing {self.__class__.__name__} with id={args['id']}",)
      self.id = args['id']
    else:
      logger.debug(f"Creating new {self.__class__.__name__}")
      self.id = await self.get_transport().create(self.__class__.__name__, **args)
    return self
  
  def get_transport(self):
    return self.parent.get_transport()

  def get_pipeline(self):
    return self.parent.get_pipeline()

  # todo: remove arguments that have a value of None to let optional params work seamlessly
  async def invoke(self, method, **args):
    return await self.get_transport().invoke(self.id, method, **args)

  async def subscribe(self, event, fn):
    def _callback(value):
      fn(value, self)
    return await self.get_transport().subscribe(self.id, event, _callback)

  async def release(self):
    return await self.get_transport().release(self.id)


class MediaPipeline(MediaObject):
  def get_pipeline(self):
    return self


class MediaElement(MediaObject):

  @classmethod
  async def build(self, parent, **args):
    args["mediaPipeline"] = parent.get_pipeline().id
    return await super().build(parent, **args)

  async def connect(self, sink):
    return await self.invoke("connect", sink=sink.id)

  async def disconnect(self, sink):
    return await self.invoke("disconnect", sink=sink.id)

  async def set_audio_format(self, caps):
    return await self.invoke("setAudioFormat", caps=caps)

  async def set_video_format(self, caps):
    return await self.invoke("setVideoFormat", caps=caps)

  async def get_source_connections(self, media_type):
    return await self.invoke("getSourceConnections", mediaType=media_type)

  async def get_sink_connections(self, media_type):
    return await self.invoke("getSinkConnections", mediaType=media_type)

# ENDPOINTS

class UriEndpoint(MediaElement):
  async def get_uri(self):
    return await self.invoke("getUri")

  async def pause(self):
    return await self.invoke("pause")

  async def stop(self):
    return await self.invoke("stop")


class PlayerEndpoint(UriEndpoint):
  async def play(self):
    return await self.invoke("play")

  async def on_end_of_stream_event(self, fn):
    return await self.subscribe("EndOfStream", fn)


class RecorderEndpoint(UriEndpoint):
  async def record(self):
    return await self.invoke("record")


class SessionEndpoint(MediaElement):
  async def on_media_session_started_event(self, fn):
    return await self.subscribe("MediaSessionStarted", fn)

  async def on_media_session_terminated_event(self, fn):
    return await self.subscribe("MediaSessionTerminated", fn)


class HttpEndpoint(SessionEndpoint):
  async def get_url(self):
    return await self.invoke("getUrl")


class HttpGetEndpoint(HttpEndpoint):
  pass


class HttpPostEndpoint(HttpEndpoint):
  async def on_end_of_stream_event(self, fn):
    return await self.subscribe("EndOfStream", fn)


class SdpEndpoint(SessionEndpoint):
  async def generate_offer(self):
    return await self.invoke("generateOffer")

  async def process_offer(self, offer):
    return await self.invoke("processOffer", offer=offer)

  async def process_answer(self, answer):
    return await self.invoke("processAnswer", answer=answer)

  async def get_local_session_descriptor(self):
    return await self.invoke("getLocalSessionDescriptor")

  async def get_remote_session_descriptor(self):
    return await self.invoke("getRemoteSessionDescriptor")


class RtpEndpoint(SdpEndpoint):
  pass

  
class WebRtcEndpoint(SdpEndpoint):
  async def on_add_ice_candidate_event(self, fn):
    return await self.subscribe("OnIceCandidate", fn)

  async def add_ice_candidate(self, candidate):
    return await self.invoke("addIceCandidate", candidate=candidate)

  async def gather_candidates(self):
    return await self.invoke("gatherCandidates")

# FILTERS

class GStreamerFilter(MediaElement):
  pass


class FaceOverlayFilter(MediaElement):
  async def set_overlayed_image(self, uri, offset_x, offset_y, width, height):
    return await self.invoke("setOverlayedImage", uri=uri, offsetXPercent=offset_x, offsetYPercent=offset_y, widthPercent=width, heightPercent=height)


class ZBarFilter(MediaElement):
  async def on_code_found_event(self, fn):
    return await self.subscribe("CodeFound", fn)


# HUBS

class Composite(MediaElement):
  pass


class Dispatcher(MediaElement):
  pass


class DispatcherOneToMany(MediaElement):
  pass
