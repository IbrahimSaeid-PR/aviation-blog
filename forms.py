from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional
from flask_wtf.file import FileAllowed


def strip_filter(x):
    return x.strip() if x else None


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=50)],
        filters=[strip_filter],
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)],
        filters=[strip_filter],
    )
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)],
        filters=[strip_filter],
    )
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class PostForm(FlaskForm):
    title = StringField(
        "Title",
        validators=[DataRequired(), Length(max=200)],
        filters=[strip_filter],
    )
    content = TextAreaField("Content", validators=[Optional(), Length(min=1)])
    image = FileField(
        "Upload Image",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "gif"], "Images only!")],
    )
    video = FileField(
        "Upload Video",
        validators=[Optional(), FileAllowed(["mp4", "webm", "ogg"], "Videos only!")],
    )
    submit = SubmitField("Publish")


class CommentForm(FlaskForm):
    content = TextAreaField(
        "Comment",
        validators=[DataRequired(), Length(min=1, max=2000)],
        filters=[strip_filter],
    )
    submit = SubmitField("Post Comment")


class LikeForm(FlaskForm):
    submit = SubmitField("Like")


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")
