from flask import Flask, render_template, redirect, url_for, flash, abort, Response
from functools import wraps
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor, CKEditorField
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import LoginForm, ContactForm
from flask_gravatar import Gravatar
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
Bootstrap(app)

# ckeditor
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_HEIGHT'] = 400
app.config['CKEDITOR_PKG_TYPE'] = 'full'
app.config['CKEDITOR_CODE_THEME'] = 'rainbow'
app.config['CKEDITOR_ENABLE_CODESNIPPET'] = True
ckeditor = CKEditor(app)

# sendgrid
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_SENDER')
mail = Mail(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# admin
app.config['FLASK_ADMIN_SWATCH'] = 'paper'

# Log-in settings
login_manager = LoginManager()
login_manager.init_app(app)

# gravatar settings
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


##CONFIGURE TABLES

tags_posts = db.Table('tags_posts',
                      db.Column('id_tag', db.Integer, db.ForeignKey('tags.id')),
                      db.Column('blog_post_id', db.Integer, db.ForeignKey('blog_posts.id'))
                      )


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author = relationship("User", back_populates="posts")
    id_author = db.Column(db.Integer, db.ForeignKey("users.id"))
    comments = relationship("Comment", back_populates="parent_post")
    published = db.Column(db.Boolean, default=False, nullable=False)
    tags = relationship('Tag', secondary=tags_posts, lazy='subquery',
                        backref=db.backref('blog_post', lazy=True))

    def __repr__(self):
        return f"<Post {self.title}>"


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)

    def __repr__(self):
        return f"<Tag {self.name}>"


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    posts = relationship('BlogPost', back_populates="author")
    comments = relationship('Comment', back_populates="comment_author")

    def __repr__(self):
        return f"<User {self.name}>"


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    comment_author = relationship("User", back_populates="comments")
    id_author = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))


class BlogPostAdminView(ModelView):
    form_overrides = dict(body=CKEditorField)
    create_template = 'admin/edit.html'
    edit_template = 'admin/edit.html'
    column_exclude_list = ['body', 'subtitle', 'img_url', ]

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login'))


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login'))


class UserView(ModelView):
    column_exclude_list = ['password', ]

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login'))


db.create_all()
admin = Admin(app, name='Blog', template_mode='bootstrap3', index_view=MyAdminIndexView())
admin.add_view(BlogPostAdminView(BlogPost, db.session))
admin.add_view(UserView(User, db.session))
admin.add_view(ModelView(Tag, db.session))





@app.route('/')
def get_all_posts():
    posts = BlogPost.query.filter_by(published=True)

    return render_template("index.html", all_posts=posts)




@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        # Everything ok
        else:
            login_user(user)
            return redirect(url_for('admin.index'))
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    requested_post = BlogPost.query.get_or_404(post_id)
    if requested_post.published:
        tags = Tag.query.filter(BlogPost.tags)
        return render_template("post.html", post=requested_post, all_tags=tags)
    return "<h1>Sorry this post is not ready yet</h1>"


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        message = form.message.data
        msg = Message('New contact', recipients=['suardini.raffaella@gmail.com'])
        msg.body = f'Questa persona: {name} email: {email} Ha scritto: {message}'
        msg.html = f'<h1>New contact</h1> ' \
                   f'<p>Questa persona: <b>{name}</b> ' \
                   f'Email: <b>{email}</b></p>' \
                   f'<p>Ha scritto: {message}</p>'
        mail.send(msg)
        flash('La mail è stata spedita correttamente.')
        return redirect(url_for('contact'))

    return render_template("contact.html", form=form)


@app.route('/github')
def github():
    return redirect("https://github.com/raffaellasuardini")

@app.route('/linkedin')
def linkedin():
    return redirect("https://www.linkedin.com/in/raffaella-suardini-8a163a175/")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
