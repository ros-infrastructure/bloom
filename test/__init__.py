# Add the scripts folder to the path

import os
if 'PATH' in os.environ:
    scripts = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    scripts = os.path.abspath(scripts)
    os.environ['PATH'] = scripts + ':' + os.environ['PATH']

os.environ['ROSDISTRO_INDEX_URL'] = 'file://' + os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'fake_rosdistro',
    'index-v4.yaml',
)

user_email = 'test@example.com'
user_name = 'Test User'

os.environ.setdefault('GIT_AUTHOR_NAME', user_name)
os.environ.setdefault('GIT_AUTHOR_EMAIL', user_email)
os.environ.setdefault('GIT_COMMITTER_NAME', user_name)
os.environ.setdefault('GIT_COMMITTER_EMAIL', user_email)
