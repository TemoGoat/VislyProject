from wsgiref.validate import validator

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired, FileSize
from wtforms.fields import StringField, PasswordField, SubmitField, EmailField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Email, Optional, URL

from models import User


class RegisterForm(FlaskForm):
    username = StringField(
        "Enter Name",
        validators=[
            DataRequired(message="User is required"),
            Length(min=8, max=24),
        ],
    )

    email = EmailField(
        "Enter Email",
        validators=[DataRequired()],
    )

    password = PasswordField(
        "Enter Password",
        validators=[
            DataRequired(),
            Length(min=8, max=24),
        ],
    )

    repeat_password = PasswordField(
        "Repeat Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="*The password is incorrect"),
        ],
    )

    profile_image = FileField(
        "Upload Your Profile Photo",
        validators=[
            FileSize(10 * 1024 * 1024),
            FileAllowed(["jpg", "png", "jpeg"]),
        ],
    )

    submit = SubmitField("Sign Up")


    def validate_username(self, username):
        from models import User
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('This Username Is Already Taken.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("The Email Is Already Used")


class LoginForm(FlaskForm):
    username = StringField(
        "Enter Name",
        validators=[
            DataRequired(message="User is required"),
            Length(min=8, max=24),
        ],
    )

    password = PasswordField(
        "Enter Password",
        validators=[
            DataRequired(),
            Length(min=8, max=24),
        ],
    )

    submit = SubmitField("Login")

class EditProfileForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    profile_image = FileField("Profile Image", validators=[Optional()])

    old_password = PasswordField("Old Password", validators=[Optional()])
    new_password = PasswordField("New Password", validators=[Optional(), EqualTo('confirm_password', message='Passwords must match')])
    confirm_password = PasswordField("Confirm New Password", validators=[Optional()])
    about_me = TextAreaField("About Me", validators=[Length(max=500)])

    pinterest_url = StringField("Pinterest URL", validators=[Optional(), URL()])
    instagram_url = StringField("Instagram URL", validators=[Optional(), URL()])
    behance_url = StringField("Behance URL", validators=[Optional(), URL()])
    website_url = StringField("Website URL", validators=[Optional(), URL()])

    submit = SubmitField("Update Profile")

class EditPhotoForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional()])
    tags = StringField("Tags", validators=[Optional()])
    image = FileField("Replace Image", validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField("Save Changes")




