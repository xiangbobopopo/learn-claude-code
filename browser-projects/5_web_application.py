#!/usr/bin/env python3
"""
Web Application using Flask
A complete web application with multiple features
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import hashlib

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///webapp.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize database
db = SQLAlchemy(app)

# Create uploads directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Helper functions
def hash_password(password):
    """Hash a password for storing"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hash):
    """Verify a stored password against one provided by user"""
    return hash_password(password) == hash

# Routes
@app.route('/')
def index():
    """Home page with recent posts"""
    posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
    return render_template('index.html', posts=posts)

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/posts')
def posts():
    """All posts page"""
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template('posts.html', posts=posts)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    """Individual post page"""
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
    return render_template('post_detail.html', post=post, comments=comments)

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    """Create a new post"""
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']
        
        # For demo purposes, using user_id=1 (would normally get from session)
        post = Post(title=title, content=content, category=category, user_id=1)
        
        try:
            db.session.add(post)
            db.session.commit()
            flash('Post created successfully!', 'success')
            return redirect(url_for('post_detail', post_id=post.id))
        except Exception as e:
            db.session.rollback()
            flash('Error creating post. Please try again.', 'error')
    
    return render_template('create_post.html')

@app.route('/api/posts')
def api_posts():
    """API endpoint for posts"""
    posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
    
    posts_data = []
    for post in posts:
        posts_data.append({
            'id': post.id,
            'title': post.title,
            'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
            'created_at': post.created_at.isoformat(),
            'author': post.author.username,
            'category': post.category
        })
    
    return jsonify({
        'posts': posts_data,
        'total': len(posts_data)
    })

@app.route('/api/comment', methods=['POST'])
def add_comment():
    """API endpoint to add a comment"""
    data = request.get_json()
    
    comment = Comment(
        content=data['content'],
        post_id=data['post_id'],
        user_id=1  # Demo: would get from session
    )
    
    try:
        db.session.add(comment)
        db.session.commit()
        return jsonify({'success': True, 'comment_id': comment.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# Template creation functions
def create_templates():
    """Create HTML templates for the web application"""
    
    # Base template
    base_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Web Application{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background: #4CAF50; color: white; padding: 1rem 0; }
        nav { display: flex; justify-content: space-between; align-items: center; }
        .nav-links { display: flex; list-style: none; }
        .nav-links li { margin-left: 20px; }
        .nav-links a { color: white; text-decoration: none; }
        .flash-messages { margin: 20px 0; }
        .flash { padding: 10px; margin: 5px 0; border-radius: 4px; }
        .flash.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .post { background: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .post-title { font-size: 1.5em; margin-bottom: 10px; }
        .post-meta { color: #666; font-size: 0.9em; margin-bottom: 10px; }
        .post-content { margin-bottom: 15px; }
        .btn { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn:hover { background: #45a049; }
        form { max-width: 600px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="email"], textarea, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        textarea { height: 150px; resize: vertical; }
        .pagination { display: flex; justify-content: center; margin: 20px 0; }
        .pagination a { margin: 0 5px; padding: 8px 12px; text-decoration: none; border: 1px solid #ddd; border-radius: 4px; }
        .pagination a.active { background: #4CAF50; color: white; }
        footer { background: #333; color: white; text-align: center; padding: 20px 0; margin-top: 40px; }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <nav>
                <h1>🌐 WebApp</h1>
                <ul class="nav-links">
                    <li><a href="{{ url_for('index') }}">Home</a></li>
                    <li><a href="{{ url_for('posts') }}">Posts</a></li>
                    <li><a href="{{ url_for('create_post') }}">Create Post</a></li>
                    <li><a href="{{ url_for('about') }}">About</a></li>
                </ul>
            </nav>
        </div>
    </header>
    
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="flash-messages">
                    {% for category, message in messages %}
                        <div class="flash {{ category }}">{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
    
    <footer>
        <div class="container">
            <p>&copy; 2024 Web Application. Built with Flask.</p>
        </div>
    </footer>
</body>
</html>
    """
    
    # Index template
    index_html = """
{% extends "base.html" %}

{% block title %}Home - Web Application{% endblock %}

{% block content %}
<h1>Welcome to Our Web Application</h1>
<p>This is a demo web application built with Flask, featuring user posts, comments, and a REST API.</p>

<h2>Recent Posts</h2>
{% for post in posts %}
    <div class="post">
        <h3 class="post-title">{{ post.title }}</h3>
        <div class="post-meta">
            By {{ post.author.username }} on {{ post.created_at.strftime('%Y-%m-%d') }}
            {% if post.category %}
                | Category: {{ post.category }}
            {% endif %}
        </div>
        <div class="post-content">
            {{ post.content[:200] }}{% if post.content|length > 200 %}...{% endif %}
        </div>
        <a href="{{ url_for('post_detail', post_id=post.id) }}" class="btn">Read More</a>
    </div>
{% else %}
    <p>No posts yet. Be the first to <a href="{{ url_for('create_post') }}">create a post</a>!</p>
{% endfor %}
{% endblock %}
    """
    
    # Create templates directory and files
    os.makedirs('templates', exist_ok=True)
    
    with open('templates/base.html', 'w') as f:
        f.write(base_html)
    
    with open('templates/index.html', 'w') as f:
        f.write(index_html)
    
    # Create other template files (simplified versions)
    templates = {
        'about.html': '<h1>About Us</h1><p>This is a demo web application showcasing Flask capabilities.</p>',
        'posts.html': '<h1>All Posts</h1><p>Browse all posts here.</p>',
        'post_detail.html': '<h1>{{ post.title }}</h1><div>{{ post.content }}</div>',
        'create_post.html': '''
<h1>Create New Post</h1>
<form method="POST">
    <div class="form-group">
        <label for="title">Title:</label>
        <input type="text" id="title" name="title" required>
    </div>
    <div class="form-group">
        <label for="content">Content:</label>
        <textarea id="content" name="content" required></textarea>
    </div>
    <div class="form-group">
        <label for="category">Category:</label>
        <select id="category" name="category">
            <option value="">Select Category</option>
            <option value="tech">Technology</option>
            <option value="science">Science</option>
            <option value="general">General</option>
        </select>
    </div>
    <button type="submit" class="btn">Create Post</button>
</form>
        '''
    }
    
    for filename, content in templates.items():
        with open(f'templates/{filename}', 'w') as f:
            f.write(content)

class WebApplicationDemo:
    """Demo class for web application concepts"""
    
    @staticmethod
    def show_flask_concepts():
        """Show Flask web development concepts"""
        print("=== Flask Web Application Concepts ===")
        
        print("\n1. Basic Flask App:")
        print("""
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def home():
            return 'Hello, World!'
        
        if __name__ == '__main__':
            app.run(debug=True)
        """)
        
        print("\n2. Templates with Jinja2:")
        print("""
        <!-- templates/hello.html -->
        <h1>Hello, {{ name }}!</h1>
        <p>Today is {{ date }}.</p>
        
        # In Flask route:
        return render_template('hello.html', name='John', date=today)
        """)
        
        print("\n3. Forms and POST requests:")
        print("""
        @app.route('/submit', methods=['GET', 'POST'])
        def submit():
            if request.method == 'POST':
                name = request.form['name']
                email = request.form['email']
                # Process form data
                return redirect(url_for('success'))
            return render_template('form.html')
        """)
        
        print("\n4. Database with SQLAlchemy:")
        print("""
        from flask_sqlalchemy import SQLAlchemy
        
        db = SQLAlchemy(app)
        
        class User(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            username = db.Column(db.String(80), unique=True)
            email = db.Column(db.String(120), unique=True)
        
        # Create user
        user = User(username='john', email='john@example.com')
        db.session.add(user)
        db.session.commit()
        """)
        
        print("\n5. REST API endpoints:")
        print("""
        @app.route('/api/users', methods=['GET'])
        def get_users():
            users = User.query.all()
            return jsonify([{'id': u.id, 'username': u.username} for u in users])
        
        @app.route('/api/users', methods=['POST'])
        def create_user():
            data = request.get_json()
            user = User(username=data['username'], email=data['email'])
            db.session.add(user)
            db.session.commit()
            return jsonify({'id': user.id}), 201
        """)

if __name__ == "__main__":
    # Create templates
    create_templates()
    
    # Show Flask concepts
    demo = WebApplicationDemo()
    demo.show_flask_concepts()
    
    print("\n🚀 Web Application Setup Complete!")
    print("To run the application:")
    print("1. Install Flask: pip install flask flask-sqlalchemy")
    print("2. Run: python web_application.py")
    print("3. Visit: http://localhost:5000")
    
    # Initialize database and run app (commented out for demo)
    """
    # Initialize database
    with app.app_context():
        db.create_all()
        
        # Create a demo user if none exists
        if not User.query.first():
            demo_user = User(
                username='demo_user',
                email='demo@example.com',
                password_hash=hash_password('demo123')
            )
            db.session.add(demo_user)
            db.session.commit()
    
    # Run the application
    app.run(debug=True)
    """