from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditorField

##WTForm

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")



class ContactForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired('Il campo nome è obbligatorio')])
    email = StringField("Email", validators=[DataRequired('Il campo email è obbligatorio'), Email(message="L'email inserita non è valida")])
    message = TextAreaField("Messaggio", validators=[DataRequired('Il campo messaggio è obbligatorio')])
    submit = SubmitField("Invia")