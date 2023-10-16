import jinja2

from aam.db import db
from aam.app import create_app

app = create_app(debug=True)

# Set options for Jinja templating engine
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# Set where to look for templates
my_loader = jinja2.FileSystemLoader(['aam/templates'])
app.jinja_loader = my_loader

app.url_map.strict_slashes = False
app.app_context().push()

from aam import views

# Initialise database and create tables if not present.
db.init_app(app)
db.create_all()
db.session.commit()
