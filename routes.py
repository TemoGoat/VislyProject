from pathlib import Path
from uuid import uuid4
from datetime import datetime
from sqlalchemy import or_, func
from collections import defaultdict
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from flask import render_template, redirect, url_for, request, session, flash, abort, current_app
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash
from forms import RegisterForm, LoginForm, EditProfileForm, EditPhotoForm

from ext import app, db
from models import Comment, User, Photo, ViewedPhoto, Post, StorylinePhoto, Storyline

from werkzeug.utils import secure_filename
import os

from PIL import Image


def search_photos(query):
    if not query:
        return []
    like_pattern = f"%{query}%"
    return Photo.query.filter(
        or_(
            Photo.title.ilike(like_pattern),
            Photo.description.ilike(like_pattern),
            Photo.tags.ilike(like_pattern)
        )
    ).all()

def search_users(query):
    if not query:
        return []
    like_pattern = f"%{query}%"
    return User.query.filter(
        or_(
            User.username.ilike(like_pattern),
            User.email.ilike(like_pattern)
        )
    ).all()


@app.route("/", methods=["GET", "POST"])
def home():
    query = request.args.get("q", "").strip()
    if query:
        photo_results = search_photos(query)
        user_results = search_users(query)
        return render_template(
            "UI-FINAL-COMING.html",
            photos=photo_results,
            users=user_results,
            query=query
        )
    else:
        photos = Photo.query.order_by(Photo.uploaded_at.desc()).all()
        return render_template(
            "UI-FINAL-COMING.html",
            photos=photos,
            users=[],
            query=""
        )


@app.route("/Login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if not user:
            flash("The Person Is Not Found", "danger")

        elif user and user.check_password(form.password.data):
            login_user(user)
            return redirect("/")

        print(form.username.data)

    return render_template("Login.html", form=form)


@app.route("/logout")
def logout():
    db.session.commit()
    logout_user()
    return redirect("/")


@app.route("/profile")
@login_required
def profile():
    photos = Photo.query.filter_by(user_id=current_user.id).order_by(Photo.uploaded_at.desc()).all()
    return render_template("Profile.html", user=current_user, photos=photos, )


@app.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()

    if request.method == "GET":
        form.about_me.data = current_user.about_me

    if request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.pinterest_url.data = current_user.pinterest_url
        form.instagram_url.data = current_user.instagram_url
        form.behance_url.data = current_user.behance_url
        form.website_url.data = current_user.website_url

    if form.validate_on_submit():

        if form.new_password.data:
            if not current_user.check_password(form.old_password.data):
                flash("Old Password Is Incorrect", "danger")
                return render_template("edit_profile.html", form=form)
            current_user.set_password(form.new_password.data)

        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.pinterest_url = form.pinterest_url.data
        current_user.instagram_url = form.instagram_url.data
        current_user.behance_url = form.behance_url.data
        current_user.website_url = form.website_url.data

        if form.profile_image.data:
            image_file = form.profile_image.data
            filename = secure_filename(image_file.filename)
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
            image_file.save(upload_path)
            current_user.image = filename

        current_user.about_me = form.about_me.data

        try:
            db.session.commit()
            flash("Profile DataBase Updated", "success")
            return redirect(url_for("profile"))
        except IntegrityError as e:
            db.session.rollback()
            if 'UNIQUE constraint failed: users.username' in str(e):
                flash("Username Is Already Taken.", "danger")
            else:
                flash("Try Again.", "danger")

    return render_template("edit_profile.html", form=form)


@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)

    if photo.user_id != current_user.id:
        flash("You are not authorized to delete this photo.", "danger")
        return redirect(url_for('profile', username=current_user.username))


    image_path = os.path.join(app.static_folder, 'uploads', photo.filename)
    if os.path.exists(image_path):
        os.remove(image_path)


    db.session.delete(photo)
    db.session.commit()
    flash("Photo deleted successfully", "success")
    return redirect(url_for('profile', username=current_user.username))



@app.route("/u/<string:username>")
def public_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    photos = Photo.query.filter_by(user_id=user.id).order_by(Photo.uploaded_at.desc()).all()
    return render_template("Profile.html", user=user, photos=photos)


@app.route('/history')
@login_required
def history():
    viewed = ViewedPhoto.query.filter_by(user_id=current_user.id) \
        .order_by(ViewedPhoto.viewed_at.desc()) \
        .limit(100).all()

    photos = [v.photo for v in viewed if v.photo is not None]

    return render_template('history.html', photos=photos)


UPLOAD_DIR = Path(app.root_path) / "static" / "uploads"
ALLOWED = {"png", "jpg", "jpeg", "gif"}

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            flash("No file selected", "danger")
            return redirect(request.url)

        ext = file.filename.rsplit(".", 1)[1].lower()
        if ext not in ALLOWED:
            flash("Unsupported format", "warning")
            return redirect(request.url)

        if request.content_length and request.content_length > 20 * 1024 * 1024:
            flash("Request Entity Too Large", "warning")
            return redirect(request.url)

        filename = f"{uuid4().hex}.{ext}"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        temp_path = UPLOAD_DIR / filename
        file.save(temp_path)

        try:
            image = Image.open(temp_path)
            image.thumbnail((1600, 1600))
            image.save(temp_path, optimize=True, quality=65)
        except Exception as e:
            flash("Image processing failed", "danger")
            return redirect(request.url)

        photo = Photo(
            filename=filename,
            title=request.form["title"],
            description=request.form.get("description", ""),
            tags=request.form.get("tags", ""),
            user=current_user
        )
        db.session.add(photo)
        db.session.commit()

        return redirect(url_for("public_profile", username=current_user.username))

    return render_template("Upload.html")



photo_views = defaultdict(int)


@app.route("/photo/<int:photo_id>", methods=["GET", "POST"])
def photo_detail(photo_id):
    photo = (Photo.query
             .options(selectinload(Photo.comments)
                      .selectinload(Comment.user))
             .get_or_404(photo_id))

    posts = Post.query.all()

    if current_user.is_authenticated:
        vp = (ViewedPhoto.query
              .filter_by(user_id=current_user.id, photo_id=photo_id)
              .first())
        if vp:
            vp.viewed_at = datetime.utcnow()
        else:
            db.session.add(ViewedPhoto(user_id=current_user.id,
                                       photo_id=photo_id))
        db.session.commit()

    if request.method == "GET":
        session['comment_start'] = datetime.utcnow().timestamp()

    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("You must be logged in to comment.", "warning")
            return redirect(url_for("login"))

        if request.form.get("website"):
            flash("Bot protection triggered.", "danger")
            return redirect(url_for("photo_detail", photo_id=photo_id))

        start_time = session.get("comment_start")
        now = datetime.utcnow().timestamp()
        if start_time and (now - start_time) < 10:
            flash("You're commenting too fast. try in 10 second", "warning")
            return redirect(url_for("photo_detail", photo_id=photo_id))

        content = request.form.get("comment", "").strip()
        if content:
            db.session.add(Comment(content=content,
                                   photo=photo,
                                   user=current_user))
            db.session.commit()
            return redirect(url_for("photo_detail", photo_id=photo.id))
        else:
            flash("Comment cannot be empty.", "danger")

    comments = sorted(photo.comments, key=lambda c: c.timestamp, reverse=True)
    related_photos = (Photo.query
                      .filter(Photo.id != photo.id)
                      .order_by(func.random())
                      .limit(8).all())

    return render_template(
        "photo_detail.html",
        posts=posts,
        photo=photo,
        comments=comments,
        related_photos=related_photos,
    )


@app.route("/edit-photo/<int:photo_id>", methods=["GET", "POST"])
@login_required
def edit_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)


    if photo.user_id != current_user.id and not current_user.is_admin:
        flash("You are not authorized to edit this photo.", "danger")
        return redirect(url_for("home"))

    form = EditPhotoForm()

    if request.method == "GET":
        form.title.data = photo.title
        form.description.data = photo.description
        form.tags.data = photo.tags

    if form.validate_on_submit():
        photo.title = form.title.data
        photo.description = form.description.data
        photo.tags = form.tags.data

        if form.image.data:
            image_file = form.image.data
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(current_app.root_path, 'static/uploads', filename)
            image_file.save(image_path)
            photo.filename = filename

        db.session.commit()
        flash("Photo updated successfully!", "success")
        return redirect(url_for("photo_detail", photo_id=photo.id))

    return render_template("edit_photo.html", form=form, photo=photo)


UPLOAD_FOLDER = Path(app.root_path) / "static" / "uploads"
DEFAULT_IMAGE = "BLANKVISLY.png"


@app.route("/SignUp", methods=["GET", "POST"])
def signup():
    form = RegisterForm()

    if request.method == "GET":
        session['signup_start'] = datetime.utcnow().timestamp()

    if request.method == "POST":

        # honeypot
        if request.form.get("website"):
            flash("Bot protection triggered.", "danger")
            return redirect(url_for("Signup"))

        start = session.get("Signup_start")
        if start and (datetime.utcnow().timestamp() - start) < 5:
            flash("Please wait a few seconds before submitting the form.", "warning")
            return redirect(url_for("signup"))

        if form.validate_on_submit():
            img_file = form.profile_image.data
            filename = DEFAULT_IMAGE

            if img_file and img_file.filename:
                filename = secure_filename(img_file.filename)
                save_path = UPLOAD_FOLDER / filename
                save_path.parent.mkdir(parents=True, exist_ok=True)
                img_file.save(save_path)

            username = form.username.data

            is_admin = False
            if username in ["TemoGoat", "VislyWeb"]:
                existing = User.query.filter_by(username=username).first()
                if not existing:
                    is_admin = True

            new_user = User(
                username=username,
                password=generate_password_hash(form.password.data),
                image=filename,
                is_admin=is_admin
            )

            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect('/')

    print(form.errors)
    return render_template("SignUp.html", form=form)


@app.route("/add_to_storyline/<int:photo_id>", methods=["POST"])
@login_required
def add_to_storyline(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    storyline_id = request.form.get("storyline_id")
    comment = request.form.get("comment")
    date_str = request.form.get("date")

    if date_str:
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            date_obj = datetime.utcnow().date()  # fallback
    else:
        date_obj = datetime.utcnow().date()

    storyline = Storyline.query.filter_by(id=storyline_id, user_id=current_user.id).first()
    if not storyline:
        flash("Storyline not found or unauthorized", "danger")
        return redirect(request.referrer)

    order = len(storyline.photos)
    new_entry = StorylinePhoto(
        image_filename=photo.filename,
        comment=comment,
        date=date_obj,
        order=order,
        storyline_id=storyline.id
    )
    db.session.add(new_entry)
    db.session.commit()
    flash("Photo added to your Storyline!", "success")
    return redirect(request.referrer)


@app.route("/aboutus")
def aboutus():
    return render_template("aboutus.html")

@app.route("/Contact")
def contact():
    return render_template("Contact.html")


@app.route('/storylines')
@login_required
def storyline_list():
    storylines = Storyline.query.filter_by(user_id=current_user.id).all()
    return render_template('storyline_list.html', storylines=storylines)


@app.route('/storyline/<int:storyline_id>')
@login_required
def storyline_detail(storyline_id):
    storyline = Storyline.query.get_or_404(storyline_id)
    if storyline.user_id != current_user.id:
        abort(403)
    return render_template('storyline_detail.html', storyline=storyline)


@app.route("/create_storyline", methods=["POST"])
@login_required
def create_storyline():
    title = request.form.get("title")
    if not title:
        flash("Title is required", "warning")
        return redirect(url_for("storyline_list"))

    new_storyline = Storyline(title=title, user_id=current_user.id)
    db.session.add(new_storyline)
    db.session.commit()
    flash("Storyline created!", "success")
    return redirect(url_for("storyline_list"))


@app.route('/storyline/<int:storyline_id>/delete', methods=['POST'])
@login_required
def delete_storyline(storyline_id):
    storyline = Storyline.query.get_or_404(storyline_id)
    if storyline.user_id != current_user.id:
        abort(403)
    db.session.delete(storyline)
    db.session.commit()
    flash("Storyline deleted successfully.", "success")
    return redirect(url_for('storyline_list'))


@app.route("/profile/<int:user_id>")
def view_profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(author_id=user.id).all()
    total_likes = sum(post.like_count for post in posts)
    return render_template("Profile.html", user=user, posts=posts, total_likes=total_likes)

import smtplib
from email.message import EmailMessage
import os

def notify_admin(username):
    sender_email = os.environ.get('EMAIL_USER', 'vislywebstite@gmail.com')
    receiver_email = os.environ.get('EMAIL_RECEIVER', 'vislywebstite@gmail.com')
    app_password = os.environ.get('EMAIL_PASS')

    msg = EmailMessage()
    msg.set_content(f"ახალი მომხმარებელი დარეგისტრირდა: {username}")
    msg['Subject'] = 'ახალი რეგისტრაცია საიტზე'
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
            print("შეტყობინება გაიგზავნა")
    except Exception as e:
        print("შეცდომა შეტყობინების გაგზავნისას:", e)
