from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, backref

# --- FIX START: Separate import for hybrid_property ---
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
# --- FIX END ---

# Initialize SQLAlchemy here
db = SQLAlchemy()

class AuditableEntity:
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    def getId(self):
        return self.id


class Content(AuditableEntity):
    __abstract__ = True
    text = Column("text", Text, nullable=True)


class Notification(AuditableEntity, db.Model):
    __tablename__ = "notification"
    
    title = Column(String(255), unique=False, nullable=True)
    content = Column(String(255), unique=False, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    def create(self):
        db.session.add(self)
        db.session.commit()    


class User(UserMixin, AuditableEntity, db.Model):
    __tablename__ = "users"

    username = Column(String(120), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    age = Column(Integer, nullable=True)
    # store hashed password in column named 'password' to keep compatibility
    password_hash = Column("password", String(255), nullable=False)

    posts = relationship("Post", backref="author", lazy="dynamic")
    comments = relationship("Comment", backref="author", lazy="dynamic")
    likes = relationship("Like", backref="user", lazy="dynamic")
    notifications = relationship("Notification", backref="autor", lazy="dynamic")
    

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def addLike(self, post):
        like = Like(user_id=self.id, post_id=post.id)
        db.session.add(like)
        post.likes_count = (post.likes_count or 0) + 1
        db.session.commit()
        return like

    def addComment(self, post, content_text):
        comment = Comment(content=content_text, user_id=self.id, post_id=post.id)
        db.session.add(comment)
        post.comments_count = (post.comments_count or 0) + 1
        db.session.commit()
        return comment

    def makePost(self, title, content_text, image_file=None, video_file=None):
        post = Post(
            title=title,
            content=content_text,
            image_file=image_file,
            video_file=video_file,
            user_id=self.id,
        )
        db.session.add(post)
        db.session.commit()
        return post


class Post(Content, db.Model):
    __tablename__ = "posts"

    title = Column(String(255), nullable=False)

    @hybrid_property
    def content(self):
        return self.text

    @content.setter
    def content(self, value):
        self.text = value

    image_file = Column(String(255), nullable=True)
    video_file = Column(String(255), nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    likes_count = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)

    @hybrid_property
    def date(self):
        return self.created_at

    likes = relationship("Like", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    comments = relationship("Comment", backref="post", lazy="dynamic", cascade="all, delete-orphan")

    def addLike(self, user):
        existing = Like.query.filter_by(user_id=user.id, post_id=self.id).first()
        if existing:
            return existing
        like = Like(user_id=user.id, post_id=self.id)
        db.session.add(like)
        self.likes_count = (self.likes_count or 0) + 1
        db.session.commit()
        return like

    def addComment(self, user, content_text, reply_to=None):
        comment = Comment(content=content_text, user_id=user.id, post_id=self.id)
        if reply_to:
            comment.reply_to_id = reply_to.id
        db.session.add(comment)
        self.comments_count = (self.comments_count or 0) + 1
        db.session.commit()
        return comment


class Comment(Content, db.Model):
    __tablename__ = "comments"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    reply_to_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    reply_to = relationship(
        "Comment",
        remote_side="Comment.id",
        backref=backref("replies", lazy="dynamic"),
    )

    @hybrid_property
    def content(self):
        return self.text

    @content.setter
    def content(self, value):
        self.text = value

    @hybrid_property
    def date(self):
        # compatibility for queries ordering by Comment.date
        return self.created_at

    def edit(self, new_text):
        self.text = new_text
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class Like(AuditableEntity, db.Model):
    __tablename__ = "likes"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    def create(self):
        db.session.add(self)
        db.session.commit()
        if self.post:
            self.post.likes_count = (self.post.likes_count or 0) + 1
            db.session.commit()

    def remove(self):
        if self.post:
            self.post.likes_count = max((self.post.likes_count or 1) - 1, 0)
        db.session.delete(self)
        db.session.commit()