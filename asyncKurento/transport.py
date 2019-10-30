import json
import logging
import websockets
import asyncio

logger = logging.getLogger(__name__)

class KurentoTransportException(Exception):
    def __init__(self, message, response={}):
      super(KurentoTransportException, self).__init__(message)
      self.response = response

    def __str__(self):
      return "%s - %s" % (str(self.message), json.dumps(self.response))


class AsyncTransport(object):

  @classmethod
  async def build(cls, url):
    self = AsyncTransport()
    self.url = url
    self.ws = await websockets.client.connect(url)
    self.worker = asyncio.create_task(
      self._response_worker()
    )
    self.responses = []
    self.current_id = 0
    self.session_id = None
    self.pending_responses = {}
    self.subscriptions = {}
    return self

  def _next_id(self):
    self.current_id += 1
    return self.current_id

  async def _response_worker(self):
    while True:
      await asyncio.sleep(0) # Just for a foothold into this method

      try:
        message = await self.ws.recv()
        logger.debug(f"<== {message}")
        response_obj = json.loads(message)
        
        if "id" in response_obj:
            self.pending_responses.update({response_obj["id"]: response_obj})

        if "method" in response_obj and response_obj["method"] == "onEvent":
          self._execute_subscriber_callback(response_obj)


      except Exception as e:
        logger.critical(f"There was an error parsing the response {e}")

  def _execute_subscriber_callback(self, response_obj):
    # Ensure that both nested values exist
    try:
      event_type = response_obj["params"]["value"]["type"]
      data = response_obj["params"]["value"]["data"]
    except KeyError as e:
      return 
    else:
      if event_type in self.subscriptions:
        callback = self.subscriptions[event_type]
        callback(data)

  async def _get_specific_response(self, id):
      while True:
          await asyncio.sleep(0)

          if id in self.pending_responses:
              return self.pending_responses[id]

  async def _rpc(self, rpc_type, **args):
    if self.session_id:
      args["sessionId"] = self.session_id

    request = {
      "jsonrpc": "2.0",
      "id": self._next_id(),
      "method": rpc_type,
      "params": args
    }
    json_message = json.dumps(request)

    await self.ws.send(json_message)
    logger.debug(f"==> {json_message}")

    resp = await self._get_specific_response(request["id"])
    
    if 'error' in resp:
      raise KurentoTransportException(resp['error']['message'] if 'message' in resp['error'] else 'Unknown Error', resp)
    elif 'result' in resp and 'value' in resp['result']:
      return resp['result']['value']
    else:
      return None # just to be explicit

  async def create(self, obj_type, **args):
    return await self._rpc("create", type=obj_type, constructorParams=args)

  async def invoke(self, object_id, operation, **args):
    return await self._rpc("invoke", object=object_id, operation=operation, operationParams=args)

  async def subscribe(self, object_id, event_type, fn):
    subscription_id = await self._rpc("subscribe", object=object_id, type=event_type)
    self.subscriptions[event_type] = fn
    return subscription_id

  async def unsubscribe(self, subscription_id):
    del self.subscriptions[subscription_id]
    return await self._rpc("unsubscribe", subscription=subscription_id)

  async def release(self, object_id):
    return await self._rpc("release", object=object_id)
