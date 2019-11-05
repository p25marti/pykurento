from OwlKurentoClient import media
from OwlKurentoClient.transport import AsyncTransport

class KurentoClient(object):

  @classmethod
  async def build(self, url, transport=None):
    self = KurentoClient()
    self.url = url
    self.transport = transport or await AsyncTransport.build(self.url)
    return self

  def get_transport(self):
    return self.transport

  async def create_pipeline(self):
    return await media.MediaPipeline.build(self)

  async def get_pipeline(self, id):
    return await media.MediaPipeline.build(self, id=id)
