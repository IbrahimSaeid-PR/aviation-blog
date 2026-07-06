from events import post_published
from flask_migrate import Migrate
from datetime import datetime
from flask import (
    Flask,  # main app
    render_template,  # show html pages
    url_for,  # links to routes
    redirect,  # send user to another page
    request,  # read data from user
    flash,  # show short messages
    abort,  # stop action
    session,  # temp data while session
    jsonify,
)

from flask_login import (
    LoginManager,  # manage everything for login
    login_user,  # for login
    logout_user,  # for logout
    current_user,  # user info logged in
    login_required,  # allow only logged in users
)

from sqlalchemy.exc import IntegrityError  # handle database errors
from werkzeug.utils import (
    secure_filename,
)  # differentiate between uploading files and videos
import os

from forms import (
    RegistrationForm,  # sign-up form
    LoginForm,  # login form
    PostForm,  # new posts
    CommentForm,  # add comments
    LikeForm,  # like posts
    DeleteForm,  # for deletion (anything)
)

# Import db and models from models.py
from models import Notification, db, User, Post, Comment, Like
from config import DevConfig

import services  # <<-- added import for services module

from events import *
from flask_sqlalchemy import SQLAlchemy

########################### App Setup ############################

app = Flask(__name__)
app.config.from_object(DevConfig)

# UPDATED: Corrected typo (SQLALCHEMY) and set for PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123456@localhost/aviation_user'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Good practice to disable this if not needed

# Directory for uploaded files
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize DB with App
db.init_app(app)
migrate = Migrate(app, db)

# initialize services with app (must be after db.init_app to avoid circular init issues)
services.init_services(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

# ------------------ User Loader ------------------


@login_manager.user_loader  # look for user in DB by id
def load_user(user_id):
    return User.query.get(int(user_id))


# ------------------ Routes ------------------


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/home")
@login_required
def home():
    # Show all posts by newest
    posts = Post.query.order_by(Post.date.desc()).all()

    return render_template("home.html", posts=posts)


@app.route("/post/<int:post_id>")
@login_required
def post_detail(post_id):
    # View post details by id / comments
    post = Post.query.get_or_404(post_id)
    comments = (
        Comment.query.filter_by(post_id=post.id)
        .order_by(Comment.date.asc())
        .all()  # oldest first
    )

    return render_template(  # send all data to template
        "post_detail.html",
        post=post,
        comments=comments,
        form=CommentForm(),
        like_form=LikeForm(),
        delete_form=DeleteForm(),
        comment_delete_form=DeleteForm(),
        liked=(  # check if user liked post
            Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
            is not None
            if current_user.is_authenticated
            else False
        ),
    )


# ------------------ New Post with Media ------------------

# only logged in users can create a post
# if valid the post is saved on detail page


@app.route("/new", methods=["GET", "POST"])
@login_required
def new_post():
    form = PostForm()  # a form for the post

    if form.validate_on_submit():
        image_filename = None
        video_filename = None

        # Handle image upload
        if form.image.data:
            image_file = form.image.data
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
            image_file.save(image_path)

        # Handle video upload
        if form.video.data:
            video_file = form.video.data
            video_filename = secure_filename(video_file.filename)
            video_path = os.path.join(app.config["UPLOAD_FOLDER"], video_filename)
            video_file.save(video_path)

        post = Post(
            title=form.title.data,
            content=form.content.data,
            image_file=image_filename,
            video_file=video_filename,
            author=current_user,
        )
    
        db.session.add(post)
        db.session.commit()
        post_published(post)


        flash("Post published.", "success")
        return redirect(
            url_for("post_detail", post_id=post.id)
        )  # after posting, go to the new post’s detail page

    return render_template("new_post.html", form=form)


# ------------------ Register ------------------


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))  # if user logged in go home

    form = RegistrationForm()

    if form.validate_on_submit():

        if User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first():
            flash(
                "Username or email already exists.", "warning"
            )  # check if user with same username or email exist and make warning
        else:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            flash("Account created — you can now log in.", "success")

            return redirect(url_for("login"))
    return render_template("register.html", form=form)


# ------------------ Login ------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))  # if user logged in go home

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()  # find user by email

        if user and user.check_password(form.password.data):  # check email and pass
            login_user(user, remember=False)  # no remember me cookie

            next_page = request.args.get(
                "next"
            )  # if user wanted to access before logging the page will be stored until logging

            return redirect(next_page or url_for("home"))  # if wrong go home

        flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form)


# ------------------ Logout ------------------


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")

    return redirect(url_for("login"))


# ------------------ Comments ------------------


@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()

    if form.validate_on_submit():
        try:
            post.addComment(current_user, form.content.data)
            flash("Comment posted.", "success")
        except Exception:
            db.session.rollback()
            flash("Could not post comment.", "warning")
    else:
        flash("Could not post comment.", "warning")

    return redirect(url_for("post_detail", post_id=post.id))


@app.route("/comment/<int:comment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != current_user.id:
        abort(403)

    form = CommentForm(obj=comment)

    if form.validate_on_submit():
        try:
            comment.edit(form.content.data)
            flash("Comment updated.", "success")
            return redirect(url_for("post_detail", post_id=comment.post_id))
        except Exception:
            db.session.rollback()
            flash("Could not update comment.", "warning")

    return render_template("edit_comment.html", form=form, comment=comment)


@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != current_user.id:
        abort(403)

    post_id = comment.post_id
    try:
        comment.delete()
        flash("Comment deleted.", "info")
    except Exception:
        db.session.rollback()
        flash("Could not delete comment.", "warning")

    return redirect(url_for("post_detail", post_id=post_id))


# ------------------ Likes ------------------


@app.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def toggle_like(post_id):
    post = Post.query.get_or_404(post_id)

    existing = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    if existing:
        # Use model remove helper which adjusts counters and commits
        try:
            existing.remove()
        except Exception:
            db.session.rollback()
            flash("Database error. Try again.", "danger")
            return redirect(url_for("post_detail", post_id=post.id))

        flash("Removed like.", "info")
    else:
        try:
            # Post.addLike will create and commit the Like and update counter
            post.addLike(current_user)
        except Exception:
            db.session.rollback()
            flash("Database error. Try again.", "danger")
            return redirect(url_for("post_detail", post_id=post.id))

        flash("Post liked.", "success")

    return redirect(url_for("post_detail", post_id=post.id))
# ------------------ Edit Post ------------------


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.user_id != current_user.id:
        abort(403)

    form = PostForm(obj=post)

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data

        # Keep UploadService behavior for files if you want
        try:
            services.post_service.update_post_media(post, form)
            flash("Post updated.", "success")
            return redirect(url_for("post_detail", post_id=post.id))
        except Exception:
            db.session.rollback()
            flash("Could not update post.", "warning")

    return render_template("edit_post.html", form=form, post=post)

# ------------------ Delete Post ------------------


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.user_id != current_user.id:
        abort(403)  # check if post exist

    db.session.delete(post)
    db.session.commit()  # delete post from DB

    flash("Post deleted.", "info")

    return redirect(url_for("home"))


# ------------------ Profile ------------------

@app.route("/profile/<int:user_id>")
@login_required
def profile(user_id):
    user = User.query.get_or_404(user_id)  # find profile user by id
    
    # 1. FETCH NOTIFICATIONS (instead of posts)
    # Ordered by created_at (newest first)
    notifications = (
        Notification.query.filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    # 2. CALCULATE TOTAL LIKES
    # We still need to query posts briefly to sum up the likes for the profile stat
    user_posts = Post.query.filter_by(user_id=user.id).all()
    total_likes = sum((p.likes_count or 0) for p in user_posts)

    return render_template(
        "profile.html", 
        user=user, 
        notifications=notifications, # UPDATED: Sending notifications to the template
        total_likes=total_likes
    )


@app.route("/me")
@login_required
def me():  # show profile of user logged in
    return redirect(url_for("profile", user_id=current_user.id))


# ------------------ Clear Session ------------------


@app.route("/clear_session")  # clear all sessions when logged out
def clear_session():
    session.clear()
    logout_user()
    flash("Session cleared. You are logged out.", "info")

    return redirect(url_for("login"))


# ------------------ Run ------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)