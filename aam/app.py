from flask import Flask

import config


def create_app(debug=False):
    """A Flask App factory."""
    app = Flask(__name__, instance_relative_config=True)
    if debug:
        app.config.from_object(config.Config)
    else:
        app.config.from_object(config.Production)
    # a simple page that says hello

    return app
