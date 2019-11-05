import os
import sys

base_path = os.path.dirname(__file__)

sys.path.append(os.path.abspath(os.path.join(base_path, '..')))

def render_view(handler, name):
    with open("%s/views/%s.html" % (base_path, name), "r") as f:
        handler.finish(f.read())
