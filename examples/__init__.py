from pykurento import KurentoClient
import os
import sys

base_path = os.path.dirname(__file__)

sys.path.append(os.path.abspath(os.path.join(base_path, '..')))


kurento = KurentoClient("ws://localhost:8888/kurento")


def render_view(handler, name):
    with open("%s/views/%s.html" % (base_path, name), "r") as f:
        handler.finish(f.read())
