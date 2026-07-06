import os
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from flask import flash

from models import db, Post, Comment, Like


class UploadService:
    def __init__(self, app):
        self.upload_folder = app.config.get("UPLOAD_FOLDER", "static/uploads")
        os.makedirs(self.upload_folder, exist_ok=True)

    def save(self, file):
        if not file:
            return None
        filename = secure_filename(file.filename)
        path = os.path.join(self.upload_folder, filename)
        file.save(path)
        return filename


class PostService:
    def __init__(self, upload_service: UploadService):
        self.upload = upload_service

    def create_post(self, form, author):
        image_filename = None
        video_filename = None

        if getattr(form, "image", None) and form.image.data:
            image_filename = self.upload.save(form.image.data)

        if getattr(form, "video", None) and form.video.data:
            video_filename = self.upload.save(form.video.data)

        post = Post(
            title=form.title.data,
            content=form.content.data,
            image_file=image_filename,
            video_file=video_filename,
            author=author,
        )
        db.session.add(post)
        db.session.commit()
        return post

    def update_post_media(self, post, form):
        if getattr(form, "image", None) and form.image.data:
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(self.upload.upload_folder, image_filename))
            post.image_file = image_filename

        if getattr(form, "video", None) and form.video.data:
            video_filename = secure_filename(form.video.data.filename)
            form.video.data.save(os.path.join(self.upload.upload_folder, video_filename))
            post.video_file = video_filename

        db.session.commit()
        return post

    def delete_post(self, post):
        db.session.delete(post)
        db.session.commit()


class CommentService:
    def add_comment(self, post, form, author):
        comment = Comment(content=form.content.data, author=author, post=post)
        db.session.add(comment)
        db.session.commit()
        return comment

    def edit_comment(self, comment, form):
        comment.content = form.content.data
        db.session.commit()
        return comment

    def delete_comment(self, comment):
        db.session.delete(comment)
        db.session.commit()


class LikeService:
    def toggle_like(self, post, user):
        existing = Like.query.filter_by(user_id=user.id, post_id=post.id).first()

        if existing:
            try:
                db.session.delete(existing)
                post.likes_count = max((post.likes_count or 1) - 1, 0)
                db.session.commit()
                flash("Removed like.", "info")
            except IntegrityError:
                db.session.rollback()
                flash("Database error. Try again.", "danger")
        else:
            try:
                db.session.add(Like(user_id=user.id, post_id=post.id))
                post.likes_count = (post.likes_count or 0) + 1
                db.session.commit()
                flash("Post liked.", "success")
            except IntegrityError:
                db.session.rollback()
                flash("Database error. Try again.", "danger")


upload_service = None
post_service = None
comment_service = None
like_service = None


def init_services(app):
    global upload_service, post_service, comment_service, like_service
    upload_service = UploadService(app)
    post_service = PostService(upload_service)
    comment_service = CommentService()
    like_service = LikeService()
