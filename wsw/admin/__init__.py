from datetime import datetime

from flask import Blueprint
from flask import redirect, request, g, flash, render_template, url_for
from flask.ext.login import current_user
from flask.ext.wtf import (Form, BooleanField, TextField, HiddenField,
        IntegerField, validators, SelectField, SubmitField,
        SelectMultipleField, RadioField, DateTimeField)

from wsw.forms import is_unique
from wsw.league import Season

admin = Blueprint('admin', __name__, template_folder="templates/admin")


# Helpers

def set_signup_division(form):
    if form.validate_on_submit():
        query = """
        UPDATE signups SET division = ?
        WHERE season_id = ?
        AND user_id = ?
        """
        values = (form.division.data, form.season_id.data, form.user_id.data)
        cur = g.db.execute(query, values)
        if cur.rowcount:
            g.db.commit()
            return True
        g.db.rollback()
    return False


def get_divisions(season):
    divisions = season.get_divisions()
    if not divisions:
        return None

    for i in range(len(divisions)):
        for j in range(len(divisions[i])):
            form = RemoveDivisionForm()
            form.season_id.data = season.id
            form.user_id.data = divisions[i][j]['id']
            form.season_id.divisions = None
            divisions[i][j]['form'] = form

    return divisions


def set_user_field(user_id, field, value):
    query = 'UPDATE users SET ' + field + ' = ? WHERE id = ?'
    values = (value, user_id)
    cur = g.db.execute(query, values)
    if cur.rowcount:
        g.db.commit()
        return True
    g.db.rollback()
    return False


def set_user_admin(user_id, value):
    return set_user_field(user_id, 'is_admin', value)


def set_user_active(user_id, value):
    return set_user_field(user_id, 'is_active', value)


# Callbacks

@admin.before_request
def restrict_to_admins():
    if not current_user.is_admin():
        flash("Admins only")
        return redirect(url_for('index'))


# Forms

class SeasonForm(Form):
    signup_limit = TextField("Signup Limit")
    signups_open = BooleanField("Signups Open")
    submit = SubmitField("Update")


class SignupForm(Form):
    season_id = HiddenField(validators=[validators.Required()])
    user_id = SelectField(u"", validators=[validators.Required()],
            coerce=int)
    submit = SubmitField("Add")


class MapPoolForm(Form):
    season_id = HiddenField(validators=[validators.Required()])
    map_id = SelectField(u"", validators=[validators.Required()])
    submit = SubmitField("Add")


class DivisionForm(Form):
    season_id = HiddenField(validators=[validators.Required()])
    user_id = SelectMultipleField(u"Players", coerce=int)
    division = IntegerField(default=0)
    action = RadioField(default='assign',
            choices=[('assign', 'Assign Division'), ('remove' ,'Remove')])
    submit = SubmitField("Submit")


class RemoveMapForm(MapPoolForm):
    map_id = HiddenField(validators=[validators.Required()])


class SignupDivisionForm(Form):
    season_id = HiddenField(validators=[validators.Required()])
    user_id = HiddenField(validators=[validators.Required()])
    division = IntegerField(validators=[validators.Required()])


class RemoveDivisionForm(SignupDivisionForm):
    division = HiddenField()


class RemoveSignupForm(Form):
    season_id = HiddenField(validators=[validators.Required()])
    user_id = HiddenField(validators=[validators.Required()])


class NewUserForm(Form):
    username = TextField('Username',
            [validators.Length(min=4, max=25), is_unique])
    email = TextField('Email Address', [validators.Required(), is_unique])


class NewMapForm(Form):
    id = TextField(validators=[validators.Required()])  # FIXME conflict with __builtin__.id
    name = TextField(validators=[validators.Required()])

class GenerateMatchesForm(Form):
    season_id = HiddenField(validators=[validators.Required()])
    maps = IntegerField(validators=[validators.Required()])
    first_default_time = DateTimeField(default=datetime.now())
    interval = SelectField(choices=[('d', 'Daily'), ('w', 'Weekly')],
            validators=[validators.Required()])
    submit = SubmitField("Generate")

# Routes


@admin.route("/")
def index():
    return render_template("admin/index.html")


@admin.route("/league")
def league():
    return redirect(url_for('.signups', id=Season.get_current_season_id()))


@admin.route("/add_signup", methods=['POST'])
def add_signup():
    form = SignupForm(request.form)
    query = """
    INSERT INTO signups(season_id, user_id) VALUES(?, ?)
    """
    values = (form.season_id.data, form.user_id.data)
    cur = g.db.execute(query, values)
    if cur.rowcount:
        flash("User added")
        g.db.commit()
    else:
        flash("Couldn't add user")
        g.db.rollback()

    return redirect(request.referrer)


@admin.route("/remove_signup", methods=['POST'])
def remove_signup():
    form = RemoveSignupForm(request.form)
    if form.validate_on_submit() and Season.remove_signup(
            form.season_id.data, form.user_id.data):
        flash("Sign-up removed")
    else:
        flash("Failed to remove sign-up")
    return redirect(request.referrer)

@admin.route("/rules/<id>")
def rules(id):
    pass


@admin.route("/remove_map_from_pool", methods=['POST'])
def remove_map_from_pool():
    form = RemoveMapForm(request.form)
    if form.validate():
        query = """
        DELETE FROM season_maps
        WHERE season_id = ?
        AND map_id = ?
        """
        values = (form.season_id.data, form.map_id.data)
        cur = g.db.execute(query, values)
        if cur.rowcount:
            flash("Map removed")
            g.db.commit()
        else:
            flash("Failed to removed map")
            g.db.rollback()
    return redirect(request.referrer)


@admin.route("/map_pool/<id>", methods=['POST', 'GET'])
def map_pool(id):
    season = Season(id)
    season.load()

    form = MapPoolForm(request.form)
    form.map_id.choices = season.get_maps_not_in_pool()
    if request.method == 'POST' and form.validate_on_submit():
        query = """
        INSERT INTO season_maps(season_id, map_id)
        VALUES(?, ?)
        """
        values = (form.season_id.data, form.map_id.data)
        cur = g.db.execute(query, values)
        if cur.rowcount:
            flash("Map added to the pool")
            g.db.commit()
        else:
            flash("Failed to add map")
            g.db.rollback()

    form.season_id.data = id
    form.map_id.choices = season.get_maps_not_in_pool()

    return render_template("admin/map_pool.html", form=form, season=season)


@admin.route("/signups/<id>", methods=['GET', 'POST'])
def signups(id):
    season = Season(id)
    season.load()

    form = DivisionForm(request.form)
    form.user_id.choices = season.get_unasigned_signup_list()
    if request.method == 'POST' and form.validate_on_submit():
        if form.user_id.data:
            if form.action.data == "assign" and season.add_to_division(form.division.data, form.user_id.data):
                flash("Division assigned")
            elif form.action.data == "remove" and season.remove_signups(form.user_id.data):
                flash("Signups removed")
            else:
                flash("Failed")
        else:
            flash("No players selected")

    form.user_id.choices = season.get_unasigned_signup_list()
    form.season_id.data = id

    add_user_form = SignupForm()
    add_user_form.season_id.data = id
    add_user_form.user_id.choices = season.get_users_for_signup()

    divisions = get_divisions(season)

    return render_template("admin/signups.html", season=season, form=form,
            signups=season.get_signups(), add_user_form=add_user_form)


@admin.route("/users")
def users():
    query = 'SELECT id, username, email, is_active, is_admin FROM users'
    from wsw import query_db
    return render_template("admin/users.html", users=query_db(query))


@admin.route("/new_user")
def new_user():
    form = NewUserForm(request.form)
    return render_template("admin/new_user.html", form=form)


@admin.route("/demote_user/<id>", methods=["POST"])
def demote_user(id):
    if id == current_user.id:
        flash("Not allowed to demote your self")
    else:
        if set_user_admin(id, False):
            flash("User demoted")
        else:
            flash("Failed")
    return redirect(request.referrer)


@admin.route("/promote_user/<id>", methods=["POST"])
def promote_user(id):
    if set_user_admin(id, True):
        flash("User promoted")
    else:
        flash("Failed")
    return redirect(request.referrer)


@admin.route("/deactivate_user/<id>", methods=["POST"])
def deactivate_user(id):
    if set_user_active(id, False):
        flash("User deactivated")
    else:
        flash("Failed")
    return redirect(request.referrer)


@admin.route("/activate_user/<id>", methods=["POST"])
def activate_user(id):
    if set_user_active(id, True):
        flash("User activated")
    else:
        flash("Failed")
    return redirect(request.referrer)


@admin.route("/remove_from_division", methods=['POST'])
def remove_from_division():
    form = RemoveDivisionForm(request.form)
    form.division.data = None
    if form.validate_on_submit():
        season = Season(form.season_id.data)
        if season.remove_from_division(form.user_id.data):
            flash("Removed from division")
            return redirect(request.referrer)

    flash("Failed to remove sign-up's division")
    return redirect(request.referrer)


@admin.route("/set_division", methods=['POST'])
def set_division():
    form = SignupDivisionForm(request.form)
    if set_signup_division(form):
        flash("Division set")
    else:
        flash("Failed to set sign-up's division")
    return redirect(request.referrer)


@admin.route("/matches/<id>", methods=['GET', 'POST'])
def matches(id):
    form = GenerateMatchesForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        season = Season(form.season_id.data)
        maps = form.maps.data
        interval = form.interval.data
        start = form.first_default_time.data

        for division in season.get_division_numbers():
            if season.create_matches(division, maps, start, interval):
                flash("Generated matches for division " + str(division))
            else:
                flash("Failed to generate matches for division " + str(division))

    season = Season(id)
    season.load()

    form.season_id.data = id

    divisions = get_divisions(season)

    return render_template("admin/matches.html", season=season, form=form,
            matches=season.get_matches())

@admin.route("/generate_matches", methods=['POST'])
def generate_matches():
    pass

@admin.route("/maps")
def maps():
    from wsw import query_db
    query = "SELECT * FROM MAPS"
    maps = query_db(query)
    form = NewMapForm(request.form)

    return render_template("admin/maps.html", maps=maps, form=form)


@admin.route("/delete_user/<id>", methods=['POST'])
def delete_user(id):
    if id == current_user.id:
        flash("Can not delete your own account.")
    else:
        query = 'DELETE FROM users WHERE id = ?'
        cur = g.db.execute(query, [id])
        if cur.rowcount:
            flash("User deleted.")
            g.db.commit()
    return redirect(request.referrer or url_for("index"))

