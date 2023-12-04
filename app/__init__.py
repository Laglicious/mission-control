"""__init__.py"""
import importlib
import os
from dotenv import find_dotenv, load_dotenv
from flask import Flask
from flask_login import LoginManager
from .admin import admin
from .models import db, migrate, User
from .routes import bp as main_bp

# Initialize dotenv settings
if os.environ.get("FLASK_ENV") == "development":
    print("Loading environment variables from .env file...")
    load_dotenv(find_dotenv())

# Initialize default environment variables
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("FLASK_APP", "app/__init__.py")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = "main.login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def format_datetime(value, date_format="%b %Y"):
    """HTML filter to format a datetime object.

    Args:
        value (str): Datetime in string format.
        format (str, optional): Defaults to '%b %Y'.

    Returns:
        datetime: Datetime object.
    """
    if value is None:
        return ""
    return value.strftime(date_format)


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)

    # Configure app settings
    app.config["DEBUG"] = os.environ.get("FLASK_ENV") == "development"

    if app.config["DEBUG"]:
        # Configure Flask Debugging
        os.environ["FLASK_DEBUG"] = "True"

        # Configure debug logging
        logging = importlib.import_module("logging")
        logging.basicConfig(level=logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)

        # Configure SQLAlchemy
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.config["SQLALCHEMY_ECHO"] = False

    try:
        print("Registering SASS bundle...")
        app.config["LIBSASS_AVAILABLE"] = importlib.util.find_spec("sass") is not None
        print(f"Is Libsass available? {app.config['LIBSASS_AVAILABLE']}")
        flask_assets = importlib.import_module("flask_assets")

        environment = flask_assets.Environment
        bundle = flask_assets.Bundle

        assets = environment(app)
        assets.debug = app.config["DEBUG"]

        scss_bundle = bundle(
            "sass/custom.scss",
            filters="libsass",
            output="css/custom.css",
        )
        assets.register("scss_all", scss_bundle)
        assets.init_app(app)
        print("Registered SASS bundle.")
    except ImportError:
        print("WARNING: libsass not installed. Skipping SASS compilation.")

    # Fetching individual components from environment variables
    if "SQLALCHEMY_DATABASE_URI" not in os.environ:
        db_user = os.environ.get("POSTGRES_USER", "pgadm")
        db_password = os.environ.get("POSTGRES_PASSWORD", "lolnope")
        db_name = os.environ.get("POSTGRES_DB", "webdb")
        db_host = os.environ.get("DATABASE_DOMAIN", "db")
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
            "SQLALCHEMY_DATABASE_URI"
        )

    # Configure CSRF protection
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "SUPERSECRETKEY")

    # Register app blueprints (routes)
    app.register_blueprint(main_bp)

    # Configure database
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()

    # Register Jinja2 filters
    app.jinja_env.filters["datetime"] = format_datetime

    # Initialize Flask-Login
    login_manager.init_app(app)
    admin.init_app(app)

    return app
