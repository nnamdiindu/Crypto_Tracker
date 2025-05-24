from flask_wtf import FlaskForm
from wtforms.fields.numeric import FloatField
from wtforms.fields.simple import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")

class BuyCoin(FlaskForm):
    name = StringField("Coin", validators=[DataRequired()])
    amount = FloatField("Amount in USD", validators=[DataRequired()])
    submit = SubmitField("Confirm")