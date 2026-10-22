from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(test_config=None):
    app = Flask(__name__)
    
    app.config.from_object('config')

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            parsed_id = int(user_id)
        except (TypeError, ValueError):
            return None

        return db.session.get(User, parsed_id)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    from app.routes.auth_routes import auth
    from app.routes.admin_routes import admin
    from app.routes.professor_routes import professor
    from app.routes.trilha_routes import trilhas
    from app.routes.task_routes import tasks

    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(professor, url_prefix='/professor')
    app.register_blueprint(trilhas, url_prefix='/trilhas')
    app.register_blueprint(tasks, url_prefix='/tasks')

    return app