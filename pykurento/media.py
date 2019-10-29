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
  def __init__(self, parent, **args):
    self.parent = parent
    self.options = args
    if 'id' in args:
      logger.debug("Creating existing %s with id=%s", self.__class__.__name__, args['id'])
      self.id = args['id']
    else:
      logger.debug("Creating new %s", self.__class__.__name__)
      self.id = self.get_transport().create(self.__class__.__name__, **args)
  
  def get_transport(self):
    return self.parent.get_transport()

  def get_pipeline(self):
    return self.parent.get_pipeline()

  # todo: remove arguments that have a value of None to let optional params work seamlessly
  def invoke(self, method, **args):
    return self.get_transport().invoke(self.id, method, **args)

  def subscribe(self, event, fn):
    def _callback(value):
      fn(value, self)
    return self.get_transport().subscribe(self.id, event, _callback)

  def release(self):
    return self.get_transport().release(self.id)


class MediaPipeline(MediaObject):
  def get_pipeline(self):
    return self


class MediaElement(MediaObject):
  def __init__(self, parent, **args):
    args["mediaPipeline"] = parent.get_pipeline().id
    super(MediaElement, self).__init__(parent, **args)

  def connect(self, sink):
    return self.invoke("connect", sink=sink.id)

  def disconnect(self, sink):
    return self.invoke("disconnect", sink=sink.id)

  def set_audio_format(self, caps):
    return self.invoke("setAudioFormat", caps=caps)

  def set_video_format(self, caps):
    return self.invoke("setVideoFormat", caps=caps)

  def get_source_connections(self, media_type):
    return self.invoke("getSourceConnections", mediaType=media_type)

  def get_sink_connections(self, media_type):
    return self.invoke("getSinkConnections", mediaType=media_type)

# ENDPOINTS

class UriEndpoint(MediaElement):
  def get_uri(self):
    return self.invoke("getUri")

  def pause(self):
    return self.invoke("pause")

  def stop(self):
    return self.invoke("stop")


class PlayerEndpoint(UriEndpoint):
  def play(self):
    return self.invoke("play")

  def on_end_of_stream_event(self, fn):
    return self.subscribe("EndOfStream", fn)


class RecorderEndpoint(UriEndpoint):
  def record(self):
    return self.invoke("record")


class SessionEndpoint(MediaElement):
  def on_media_session_started_event(self, fn):
    return self.subscribe("MediaSessionStarted", fn)

  def on_media_session_terminated_event(self, fn):
    return self.subscribe("MediaSessionTerminated", fn)


class HttpEndpoint(SessionEndpoint):
  def get_url(self):
    return self.invoke("getUrl")


class HttpGetEndpoint(HttpEndpoint):
  pass


class HttpPostEndpoint(HttpEndpoint):
  def on_end_of_stream_event(self, fn):
    return self.subscribe("EndOfStream", fn)


class SdpEndpoint(SessionEndpoint):
  def generate_offer(self):
    return self.invoke("generateOffer")

  def process_offer(self, offer):
    return self.invoke("processOffer", offer=offer)

  def process_answer(self, answer):
    return self.invoke("processAnswer", answer=answer)

  def get_local_session_descriptor(self):
    return self.invoke("getLocalSessionDescriptor")

  def get_remote_session_descriptor(self):
    return self.invoke("getRemoteSessionDescriptor")


class RtpEndpoint(SdpEndpoint):
  pass

  
class WebRtcEndpoint(SdpEndpoint):
  def on_add_ice_candidate_event(self, fn):
    return self.subscribe("OnIceCandidate", fn)

  def add_ice_candidate(self, candidate):
    return self.invoke("addIceCandidate", candidate=candidate)

  def gather_candidates(self):
    return self.invoke("gatherCandidates")

# FILTERS

class GStreamerFilter(MediaElement):
  pass


class FaceOverlayFilter(MediaElement):
  def set_overlayed_image(self, uri, offset_x, offset_y, width, height):
    return self.invoke("setOverlayedImage", uri=uri, offsetXPercent=offset_x, offsetYPercent=offset_y, widthPercent=width, heightPercent=height)


class ZBarFilter(MediaElement):
  def on_code_found_event(self, fn):
    return self.subscribe("CodeFound", fn)


# HUBS

class Composite(MediaElement):
  pass


class Dispatcher(MediaElement):
  pass


class DispatcherOneToMany(MediaElement):
  pass
