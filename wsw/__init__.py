import sqlite3

from flask import Flask, g, request, url_for

from flask.ext.bcrypt import Bcrypt
from flask.ext.login import LoginManager, current_user

from wsw.forms import LoginForm
from wsw.users import User, Anonymous
from wsw.admin import RemoveDivisionForm
from wsw.league import Season
import admin


# Application

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config.from_object('wsw.config')
app.register_blueprint(admin.admin, url_prefix='/admin')


# Callbacks

@app.before_request
def before_request():
    g.db = connect_db()
    query = 'PRAGMA foreign_keys = ON'
    g.db.execute(query)


def match_link():
    if current_user.is_authenticated():
        season_id = Season.get_current_season_id()
        query = """
        SELECT COUNT(*) as count FROM matches
        LEFT JOIN match_players ON match_id = matches.id
        WHERE season_id = ?
        AND user_id = ?
        """
        result = query_db(query, (season_id, current_user.get_id()), True)
        if result['count']:
            return ('matches/my', 'matches', "Matches (%i)" % result['count'])

    return ('/matches', 'matches', "Matches")

def season_link():
    query = """
    SELECT id FROM seasons
    ORDER BY id DESC
    """
    cur = g.db.execute(query)
    seasons = (x[0] for x in cur.fetchall())
    links = []
    for season_id in seasons:
        links = links + [(url_for('season', id=season_id), 'season', 'Season %i'%season_id)]
    return ('/', 'season', "Season %i" % Season.get_current_season_id())

@app.context_processor
def inject_navigation():
    menu = [
            ('/', 'index', 'Home'),
            season_link(),
            ('/users', 'users', 'Users'),
            ('/signups', 'signups', 'Sign-ups'),
            match_link(),
            ('/reset', 'reset', 'Reset'),
            ]
    if current_user.is_authenticated():
        menu = menu + [('/logout', 'logout', 'Logout')]
        if current_user.is_admin():
            menu = menu + [('/admin', 'admin', 'Admin')]
    else:
        menu = menu + [
                ('/login', 'login', 'Login'),
                ('/register', 'register', 'Register')
                ]
    return dict(navigation_bar=menu)


@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()


# Login manager

login_manager = LoginManager()

@login_manager.user_loader
def load_user(id):
    query = 'SELECT username, is_active, is_admin FROM users WHERE id = ?'
    result = query_db(query, [id], True)
    if result:
        return User(result['username'], id, result['is_admin'], result['is_active'])
    return Anonymous()

login_manager.setup_app(app)
login_manager.anonymous_user = Anonymous


# Helper functions

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def get_connection():
    db = getattr(g, 'db', None)
    if db is None:
        db = g.db = connect_db()
    return db


def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
        for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv


def get_divisions(season_id, form=False):
    # find populated divisions for a season
    query = """SELECT DISTINCT division FROM signups
    WHERE season_id = ? ORDER BY division ASC"""
    values = [season_id]
    cur = g.db.execute(query, values)
    division_numbers = cur.fetchall()

    # return None if no divisions are populated
    if not division_numbers:
        return None

    divisions = []

    # fetch divisions
    query = """
    SELECT user_id, username, division FROM signups
    LEFT JOIN users ON users.id = user_id
    WHERE season_id = ?
    AND division = ?
    """
    for i in division_numbers:
        i = i[0]
        if i:
            values = (season_id, unicode(i))
            division = query_db(query, values)
            if form:
                for i in range(len(division)):
                    division[i]['form'] = RemoveDivisionForm()
                    division[i]['form'].season_id.data = season_id
                    division[i]['form'].user_id.data = division[i]['user_id']
                    division[i]['form'].season_id.divisions = None
            divisions.append(division)

    return divisions


def get_admin_menu():
    menu = [
            {'label':'Back', 'url':url_for('index'), 'path':''},
            {'label':'Dashboard', 'url':url_for('admin.dashboard'),
                'path':'/'},
            {'label':'League', 'url':url_for('admin.league'),
                'path':'/league'},
            {'label':'Users', 'url':url_for('admin.users'), 'path':'/users'},
            ]
    return menu


def get_login_form():
    return LoginForm(request.form, prefix="login_")


def register_user(username, email, password, admin=False):
    query = """
    INSERT INTO users(username, email, password, is_admin)
    VALUES(?, ?, ?, ?)
    """
    values = [username, email, bcrypt.generate_password_hash(password), admin]
    cur = g.db.execute(query, values)

    query = """
    INSERT INTO signups(season_id, user_id)
    VALUES(?, ?)
    """
    values = (1, cur.lastrowid)
    g.db.execute(query, values)
    g.db.commit()


def create_season():
    query = 'INSERT INTO seasons DEFAULT VALUES'
    g.db.execute(query)
    g.db.commit()


def create_maps():
    query = """INSERT INTO maps(id, name) VALUES(?, ?)"""
    maps = [
            ('wdm3', 'Deepre Underground'),
            ('wdm5', 'Viciious\' Lair'),
            ('wdm6', 'deemsix'),
            ('wdm12', 'Courtryard'),
            ('wdm17', 'Le Toxiquet'),
            ]
    g.db.executemany(query, maps)
    g.db.commit()


def setup(username='admin', email='admin@localhost', password='pass'):
    f = open('wsw/schema.sql', 'r')
    script = unicode(f.read())
    g.db.executescript(script)
    g.db.commit()
    create_season()
    register_user(username, email, password, admin=True)
    for i in range(20):
        register_user('user' + str(i), str(i) + '@user', 'pass', False)
    create_maps()




# Unavoidable circular import
import wsw.views
