from datetime import datetime
from uuid import uuid4

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from ext import db, login_manager


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    image = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(120), nullable=False, default='',)
    photos = db.relationship(
        "Photo",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    is_admin = db.Column(db.Boolean, default=False)
    about_me = db.Column(db.Text)
    pinterest_url = db.Column(db.String(255))
    instagram_url = db.Column(db.String(255))
    behance_url = db.Column(db.String(255))
    website_url = db.Column(db.String(255))

    def set_password(self, raw_password: str):
        self.password = generate_password_hash(raw_password)

    def check_password(self, unhashed_password: str) -> bool:
        return check_password_hash(self.password, unhashed_password)

class Photo(db.Model):
    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(260), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.String(250))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user = db.relationship("User", back_populates="photos")
    comments = db.relationship("Comment", back_populates="photo", cascade="all, delete-orphan")


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    photo_id = db.Column(db.Integer, db.ForeignKey("photos.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    user = db.relationship("User", backref="comments")
    photo = db.relationship("Photo", back_populates="comments")

@classmethod
def create_from_upload(cls, file_obj, form_data, upload_dir):
    from werkzeug.utils import secure_filename
    ext = file_obj.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{uuid4().hex}.{ext}")
    save_path = upload_dir / filename
    file_obj.save(save_path)

    return cls(
        filename=filename,
        title=form_data["title"],
        description=form_data.get("description", ""),
        tags=form_data.get("tags", ""),
    )


class ViewedPhoto(db.Model):
    __tablename__ = "viewedphotos"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    photo_id = db.Column(db.Integer, db.ForeignKey('photos.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('viewed_photos', lazy='dynamic'))
    photo = db.relationship('Photo')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(120), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class Storyline(db.Model):
    __tablename__ = "storylines"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = db.relationship("User", backref=db.backref("storylines", cascade="all, delete-orphan", lazy="dynamic"))


    photos = db.relationship("StorylinePhoto", back_populates="storyline", cascade="all, delete-orphan", order_by="StorylinePhoto.order")


class StorylinePhoto(db.Model):
    __tablename__ = "storyline_photos"

    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, nullable=False, default=0)


    storyline_id = db.Column(db.Integer, db.ForeignKey("storylines.id", ondelete="CASCADE"), nullable=False)
    storyline = db.relationship("Storyline", back_populates="photos")

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))

