from wtforms import StringField, TextAreaField, BooleanField
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, redirect, request, url_for, jsonify, session, flash
import requests
from flask_migrate import Migrate
from extensions import db
from flask_admin import Admin
from flask_admin.model.form import InlineFormAdmin
from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, SelectField
from wtforms.validators import DataRequired
from sqlalchemy.exc import IntegrityError
import re
from sqlalchemy import Column, Integer, String, Text, Boolean
from flask_admin.model.template import macro


app = Flask(__name__)
app.secret_key = 'VVVvvv'
# Replace with your database URL
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    speaker = db.Column(db.String(100))
    type = db.Column(db.String(100))

    def __init__(self, name, date, description, speaker, type):
        self.name = name
        self.date = date
        self.description = description
        self.speaker = speaker
        self.type = type


class EventForm(FlaskForm):
    name = StringField('Назва', validators=[DataRequired()])
    date = DateField('Дата', validators=[DataRequired()])
    description = TextAreaField('Опис')
    speaker = StringField('Спікер')
    type = SelectField('Тип події', choices=[(
        'Майбутній', 'Майбутній'), ('Минулий', 'Минулий')], validators=[DataRequired()])


class EventAdminView(ModelView):
    column_list = ['name', 'date', 'description', 'speaker', 'type']
    form = EventForm
    column_filters = ['type']
    column_searchable_list = ['name']


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=False)

    def __init__(self, event_name, comment):
        self.event_name = event_name
        self.comment = comment


class FeedbackForm(FlaskForm):
    event_name = StringField('Назва івенту', validators=[DataRequired()])
    comment = TextAreaField('Коментар', validators=[DataRequired()])


class FeedbackAdminView(ModelView):
    column_list = ['event_name', 'comment']
    form = FeedbackForm


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    surname = db.Column(db.String(80))
    login = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))


class UserAdminForm(FlaskForm):
    name = StringField('Ім\'я')
    surname = StringField('Прізвище')
    login = StringField('Логін')
    password = StringField('Пароль')


class UserAdminView(ModelView):
    column_list = ['name', 'surname', 'login']
    form = UserAdminForm


class Notification(db.Model):
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    send_to_all = Column(Boolean, default=True)


class NotificationForm(FlaskForm):
    text = TextAreaField('Текст повідомлення', validators=[DataRequired()])
    send_to_all = BooleanField('Надіслати всім')


class NotificationAdminView(ModelView):
    column_list = ['text', 'send_to_all']
    form = NotificationForm


# Створення об'єкта адміністративної панелі
admin = Admin(app, name='Admin Panel')

# Додавання моделі Event до адміністративної панелі з використанням EventAdminView
admin.add_view(EventAdminView(Event, db.session))
admin.add_view(FeedbackAdminView(Feedback, db.session))
admin.add_view(UserAdminView(User, db.session))
admin.add_view(NotificationAdminView(Notification, db.session))

with app.app_context():
    db.create_all()


@app.route('/add_event', methods=['POST'])
def add_event():
    if request.method == 'POST':
        name = request.json.get('name')
        date = request.json.get('date')
        description = request.json.get('description')

        if name and date:
            new_event = Event(name=name, date=date, description=description)
            db.session.add(new_event)
            db.session.commit()
            return jsonify({"message": "Event added successfully"})
        else:
            return jsonify({"error": "Name and date are required"})

# Маршрут для головної сторінки


@app.route('/')
def home():
    return render_template('index.html')

# Маршрут для сторінки авторизації


def is_valid_password(password):
    return len(password) >= 8 and re.search(r'[a-z]', password) and re.search(r'[A-Z]', password) and re.search(r'\d', password)


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        # Отримайте дані, які користувач ввів в поля введення
        name = request.form['name']
        surname = request.form['surname']
        password = request.form['password']
        email = request.form['email']

        if not name or not surname or not password or not email:
            flash('Будь ласка, заповніть всі обов\'язкові поля', 'danger')
            return redirect(url_for('registration'))

        if '@' not in email:
            flash("Некоректний формат електронної пошти", 'danger')
            return redirect(url_for('registration'))

        if not is_valid_password(password):
            flash('Пароль не відповідає критеріям. Пароль повинен містити мінімум 8 символів, включаючи великі літери та цифри.', 'danger')
            return redirect(url_for('registration'))
        try:
            new_user = User(name=name, surname=surname,
                            login=email, password=password)
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            flash('Користувач з такою адресою електронної пошти вже зареєстрований. Виберіть іншу адресу електронної пошти.', 'danger')
            # Повернення на сторінку реєстрації
            return redirect(url_for('registration'))
        return redirect(url_for('last_page'))

    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        loginInput = request.form['login']

        # Запит до бази даних, щоб знайти користувача за введеною поштою
        user = User.query.filter_by(login=loginInput).first()

        if user:
            # Вхід користувача в систему або встановлення змінної сесії
            session['user_id'] = user.id
            return redirect(url_for('last_page'))
        else:
            flash('Неправильна електронна пошта', 'danger')

    return render_template('vhid.html')


@app.route('/load-more')
def load_more():
    events = Event.query.all()
    return render_template('events.html', events=events)


@app.route('/events')
def events():
    events = Event.query.all()
    return render_template('events.html', events=events)


@app.route('/last-page', methods=['GET', 'POST'])
def last_page():
    if request.method == 'POST':
        return redirect(url_for('last_page'))

    events = Event.query.all()
    return render_template('last-page.html', events=events)


@app.route('/admin/feedback')
def admin_feedback():
    # Отримати всі записи фідбеку з бази даних
    feedback_entries = Feedback.query.all()
    return render_template('admin_feedback.html', feedback_entries=feedback_entries)


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = FeedbackForm()
    success_message = None

    if request.method == 'POST' and form.validate():
        event_name = form.event_name.data
        comment = form.comment.data

        new_feedback = Feedback(event_name=event_name, comment=comment)
        db.session.add(new_feedback)
        db.session.commit()
        success_message = "Ваш коментар відправлено."

        return redirect(url_for('load_more'))

    return render_template('feedback.html', form=form, success_message=success_message)


@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    if request.method == 'POST':
        event_name = request.form.get('event_name')
        comment = request.form.get('comment')

        if not event_name or not comment:
            flash("Будь ласка, заповніть всі обов'язкові поля для фідбеку.", 'danger')
        else:
            new_feedback = Feedback(event_name=event_name, comment=comment)
            db.session.add(new_feedback)
            db.session.commit()
        flash("Ваш коментар відправлено.")

    return redirect(url_for('last_page'))


@app.route('/admin/notifications', methods=['GET', 'POST'])
def admin_notifications():
    if request.method == 'POST':
        text = request.form['text']
        send_to_all = 'send_to_all' in request.form
        new_notification = Notification(text=text, send_to_all=send_to_all)
        db.session.add(new_notification)
        db.session.commit()
        flash('Повідомлення надіслано', 'success')
    return render_template('admin_notifications.html')


if __name__ == '__main__':
    app.run(debug=True)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    return render_template('admin.html')


def admin_panel():
    # Отримайте список користувачів з бази даних
    users = User.query.all()
    return render_template('admin_mails.html', users=users)
