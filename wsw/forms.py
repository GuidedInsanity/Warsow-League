from flask import (g)
from flask.ext.wtf import (Form, TextField, PasswordField, BooleanField,
        validators, ValidationError)


def is_unique(form, field):
    query = 'SELECT COUNT(*) FROM users WHERE ' + field.id + ' = ?'
    values = [field.data]
    count = g.db.execute(query, values)
    if(count.fetchone()[0]):
        raise ValidationError(field.label.text + " is already in use")


class LoginForm(Form):
    username = TextField('Username')
    password = PasswordField('Password')
    remember = BooleanField("Remember Me")


class RegistrationForm(Form):
    username = TextField('Username',
            [validators.Length(min=4, max=25), is_unique])
    email = TextField('Email Address', [validators.Required(), is_unique])
    password = PasswordField('New Password',
            [validators.Required(),
            validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password')
