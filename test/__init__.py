# Add the scripts folder to the path

import os
if 'PATH' in os.environ:
    scripts = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    scripts = os.path.abspath(scripts)
    os.environ['PATH'] = scripts + ':' + os.environ['PATH']
