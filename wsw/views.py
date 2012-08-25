from flask import (render_template, request, g, flash, redirect, url_for)
from flask.ext.login import (login_user, logout_user, login_required,
        current_user)
from wsw import (app, bcrypt, query_db, register_user, setup, get_divisions)
from wsw.forms import LoginForm, RegistrationForm
from wsw.users import User
from wsw.league import Season


# Helper functions

def get_users():
    query = """
    SELECT id, username, email, password, is_admin FROM users
    WHERE is_active = 1
    """
    return query_db(query)


def get_signups(season_id):
    query = """
    SELECT id, username FROM signups
    LEFT JOIN users ON id = user_id
    WHERE season_id = ?
    AND division IS NULL
    """
    return query_db(query, [season_id])


# Error handlers

@app.errorhandler(401)
def unauthorized(e):
    flash("Unauthorized")
    return redirect(url_for('index'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Routes

@app.route('/reset')
def reset():
    setup()
    return redirect(url_for('index'))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegistrationForm(request.form)
    if request.method == "POST" and form.validate():
        register_user(form.username.data, form.email.data, form.password.data)
        # TODO check if registration completed
        flash("Account created, check your inbox for activation instructions")
        return redirect(url_for("index"))
    return render_template('register.html', form=form)


@app.route('/users/')
def users():
    return render_template('users.html', users=get_users())


@app.route('/user/<id>')
def user(id):
    return render_template('users.html', users=get_users())


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm(request.form, prefix='login_')
    if request.method == 'POST':
        if form.validate_on_submit():
            query = """
            SELECT id, username, password, is_admin, is_active FROM users
            WHERE username LIKE ?
            """
            values = [form.username.data]
            result = query_db(query, values, one=True)
            if result and bcrypt.check_password_hash(result['password'],
            form.password.data):
                user = User(result['username'], result['id'],
                        result['is_admin'], result['is_active'])
                if login_user(user, form.remember.data):
                    flash("Welcome back, %s" % (result['username']))
                    return redirect(url_for("index"))
                else:
                    flash("Could not login")  # better message?
            else:
                flash("Invalid username or password")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(request.referrer or url_for('index'))


# TODO limit access

@app.route("/season/<id>")
def season(id):
    return str(id)


@app.route("/signup", methods=['POST'])
def signup():
    query = 'INSERT INTO signups(season_id, user_id) VALUES(?, ?)'
    values = [Season.get_current_season_id(), current_user.get_id()]
    try:
        g.db.execute(query, values)
        g.db.commit()
        flash("Signed up")
    except Exception as e:
        print e  # TODO what was I going to catch?
    return redirect(request.referrer)


@app.route("/unsignup", methods=['POST'])
def usnignup():
    query = 'DELETE FROM signups WHERE season_id = ? AND user_id = ?'
    values = (Season.get_current_season_id(), current_user.get_id())
    cur = g.db.execute(query, values)
    if cur.rowcount:
        g.db.commit()
        flash("Signup removed")
    else:
        g.db.rollback()
        flash("Failed to remove your signup")
    return redirect(request.referrer)


@app.route("/signups/")
def signups():
    season_id = Season.get_current_season_id()
    user_id = current_user.get_id()
    signups = get_signups(season_id)
    query = """
    SELECT COUNT(*) as count FROM signups
    WHERE season_id = ?
    AND user_id = ?
    """
    signedup = query_db(query, [season_id, user_id], True)['count']
    return render_template('signups.html', signups=signups, signedup=signedup,
            divisions=get_divisions(season_id))
