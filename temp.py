
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify, Response, g
from wtforms import Form, StringField, PasswordField, TextAreaField, IntegerField, validators
from wtforms.validators import DataRequired
from passlib.hash import sha256_crypt
from functools import wraps
import timeago
import datetime
from wtforms.fields.html5 import EmailField
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from flask_mail import Mail, Message
import plotly.graph_objects as go
import pandas as pd
from flask import send_file
import os
import sqlite3

app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('config.py')
app.secret_key = 'abcd2123445'

# SQLite3 configuration
DATABASE = 'tracker.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Check if the database file exists, if not create it
if not os.path.exists(DATABASE):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Create transactions table
    cursor.execute('''
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            description TEXT,
            category TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()

mail = Mail(app)

class User:
    def __init__(self, first_name, last_name, email, username, password):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.username = username
        self.password = password

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

class User:
    def __init__(self, first_name, last_name, email, username, password):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.username = username
        self.password = password

# Registration route



class SignUpForm(Form):
    first_name = StringField('First Name', [validators.Length(min=1, max=100)])
    last_name = StringField('Last Name', [validators.Length(min=1, max=100)])
    email = EmailField('Email address', [
                       validators.DataRequired(), validators.Email()])
    username = StringField('Username', [validators.Length(min=4, max=100)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'logged_in' in session and session['logged_in'] == True:
        flash('You are already logged in', 'info')
        return redirect(url_for('addTransactions'))
    
    form = SignUpForm(request.form)
    
    if request.method == 'POST' and form.validate():
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        conn = get_db()
        cur = conn.cursor()

        # Check if email is already taken
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        if cur.fetchone():
            flash('The entered email address has already been taken. Please try using or creating another one.', 'info')
            return redirect(url_for('signup'))
        else:
            cur.execute("INSERT INTO users(first_name, last_name, email, username, password) VALUES (?, ?, ?, ?, ?)",
                        (first_name, last_name, email, username, password))
            conn.commit()
            cur.close()
            flash('You are now registered and can log in', 'success')
            return redirect(url_for('login'))

    return render_template('signUp.html', form=form)


class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=100)])
    password = PasswordField('Password', [
        validators.DataRequired(),
    ])
# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session and session['logged_in'] == True:
        flash('You are already logged in', 'info')
        return redirect(url_for('addTransactions'))

    form = LoginForm(request.form)
    
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password_input = form.password.data

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cur.fetchone()

        if user:
            user_id, *_rest = user  # Use *_rest to capture any additional columns

            hashed_password = _rest[-1]  # Assuming the last column is the hashed password

            if sha256_crypt.verify(password_input, hashed_password):
                session['logged_in'] = True
                session['username'] = username
                session['userID'] = user_id
                flash('You are now logged in', 'success')
                return redirect(url_for('addTransactions'))
            else:
                error = 'Invalid Password'
                return render_template('login.html', form=form, error=error)

        else:
            error = 'Username not found'
            return render_template('login.html', form=form, error=error)

    return render_template('login.html', form=form)
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and session['logged_in'] == True:
            return f(*args, **kwargs)
        else:
            flash('Please login', 'info')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Add Transactions route
class TransactionForm(Form):
    amount = IntegerField('Amount', validators=[DataRequired()])
    description = StringField('Description', [validators.Length(min=1)])
    
@app.route('/addTransactions', methods=['GET', 'POST'])
@is_logged_in
def addTransactions():
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        amount = request.form['amount']
        description = request.form['description']
        category = request.form['category']

        cur.execute("INSERT INTO transactions(user_id, amount, description, category) VALUES (?, ?, ?, ?)",
                    (session['userID'], amount, description, category))
        conn.commit()

        flash('Transaction Successfully Recorded', 'success')

    # Fetch updated transactions
    cur.execute("SELECT SUM(amount) FROM transactions WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now') AND user_id = ?",
                [session['userID']])
    data = cur.fetchone()
    totalExpenses = data[0]

    result = cur.execute(
        "SELECT * FROM transactions WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now') AND user_id = ? ORDER BY date DESC", [
            session['userID']]
    )

    transactions = [dict(zip([column[0] for column in result.description], row)) for row in result.fetchall()]

    for transaction in transactions:
        if datetime.datetime.now() - datetime.datetime.strptime(transaction['date'], '%Y-%m-%d %H:%M:%S') < datetime.timedelta(days=0.5):
            transaction['date'] = timeago.format(
                datetime.datetime.strptime(transaction['date'], '%Y-%m-%d %H:%M:%S'), datetime.datetime.now())
        else:
            transaction['date'] = datetime.datetime.strptime(
                transaction['date'], '%Y-%m-%d %H:%M:%S').strftime('%d %B, %Y')

    cur.close()

    return render_template('addTransactions.html', totalExpenses=totalExpenses, transactions=transactions)


@app.route('/editTransaction/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def editTransaction(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM transactions WHERE id = ?", [id])
    transaction = cur.fetchone()
    cur.close()

    form = TransactionForm(request.form)
    form.amount.data = transaction[2]
    form.description.data = transaction[3]

    if request.method == 'POST' and form.validate():
        amount = request.form['amount']
        description = request.form['description']

        cur = conn.cursor()
        cur.execute("UPDATE transactions SET amount=?, description=? WHERE id = ?",
                    (amount, description, id))
        conn.commit()
        cur.close()

        flash('Transaction Updated', 'success')

        return redirect(url_for('transactionHistory'))

    return render_template('editTransaction.html', form=form)

# Delete Transaction route
@app.route('/deleteTransaction/<string:id>', methods=['POST'])
@is_logged_in
def deleteTransaction(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM transactions WHERE id = ?", [id])
    conn.commit()
    cur.close()

    flash('Transaction Deleted', 'success')

    return redirect(url_for('transactionHistory'))

# Edit Current Month Transaction route
@app.route('/editCurrentMonthTransaction/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def editCurrentMonthTransaction(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM transactions WHERE id = ?", [id])
    transaction = cur.fetchone()
    cur.close()

    form = TransactionForm(request.form)
    form.amount.data = transaction[2]
    form.description.data = transaction[3]

    if request.method == 'POST' and form.validate():
        amount = request.form['amount']
        description = request.form['description']

        cur = conn.cursor()
        cur.execute("UPDATE transactions SET amount=?, description=? WHERE id = ?",
                    (amount, description, id))
        conn.commit()
        cur.close()

        flash('Transaction Updated', 'success')

        return redirect(url_for('addTransactions'))

    return render_template('editTransaction.html', form=form)

# Delete Current Month Transaction route
@app.route('/deleteCurrentMonthTransaction/<string:id>', methods=['POST'])
@is_logged_in
def deleteCurrentMonthTransaction(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM transactions WHERE id = ?", [id])
    conn.commit()
    cur.close()

    flash('Transaction Deleted', 'success')

    return redirect(url_for('addTransactions'))

class RequestResetForm(Form):
    email = EmailField('Email address', [
                       validators.DataRequired(), validators.Email()])

# Reset Request route
@app.route("/reset_request", methods=['GET', 'POST'])
def reset_request():
    if 'logged_in' in session and session['logged_in'] == True:
        flash('You are already logged in', 'info')
        return redirect(url_for('index'))

    form = RequestResetForm(request.form)
    
    if request.method == 'POST' and form.validate():
        email = form.email.data
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id, username, email FROM users WHERE email = ?", [email])
        user = cur.fetchone()

        if not user:
            flash('There is no account with that email. You must register first.', 'warning')
            return redirect(url_for('signup'))

        user_id, username, user_email = user
        cur.close()

        s = Serializer(app.config['SECRET_KEY'], 1800)
        token = s.dumps({'user_id': user_id}).decode('utf-8')

        msg = Message('Password Reset Request',
                      sender='noreply@demo.com', recipients=[user_email])
        msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make password reset request then simply ignore this email and no changes will be made.
Note:This link is valid only for 30 mins from the time you requested a password change request.
'''
        mail.send(msg)

        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))

    return render_template('reset_request.html', form=form)

# Reset Password Form
class ResetPasswordForm(Form):
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# Reset Token route
@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if 'logged_in' in session and session['logged_in'] == True:
        flash('You are already logged in', 'info')
        return redirect(url_for('index'))

    s = Serializer(app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token)['user_id']
    except:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE id = ?", [user_id])
    data = cur.fetchone()
    cur.close()

    user_id = data[0]
    form = ResetPasswordForm(request.form)

    if request.method == 'POST' and form.validate():
        password = sha256_crypt.encrypt(str(form.password.data))
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password = ? WHERE id = ?", (password, user_id))
        conn.commit()
        cur.close()

        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))

    return render_template('reset_token.html', title='Reset Password', form=form)

# Category Wise Pie Chart For Current Year As Percentage
@app.route('/category')
def createBarCharts():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        f"SELECT Sum(amount) AS amount, category FROM transactions WHERE strftime('%Y', date) = strftime('%Y', 'now') AND user_id = ? GROUP BY category ORDER BY category", [session['userID']])
    transactions = cur.fetchall()

    values = [transaction[0] for transaction in transactions]
    labels = [transaction[1] for transaction in transactions]

    fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
    fig.update_traces(textinfo='label+value', hoverinfo='percent')
    fig.update_layout(
        title_text='Category Wise Pie Chart For Current Year')
    fig.show()

    cur.close()

    return redirect(url_for('addTransactions'))

@app.route('/daily_line')
def dailyLineChart():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT DATE(date) AS transaction_date, SUM(amount) AS total_amount FROM transactions WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now') AND user_id = ? GROUP BY DATE(date) ORDER BY DATE(date)",
        [session['userID']]
    )
    data = cur.fetchall()

    dates = [entry[0] for entry in data]
    amounts = [entry[1] for entry in data]

    fig = go.Figure(data=go.Scatter(x=dates, y=amounts, mode='lines+markers'))
    fig.update_layout(title_text='Daily Expenses Line Chart', xaxis_title='Date', yaxis_title='Total Amount')
    fig.show()

    cur.close()

    return redirect(url_for('addTransactions'))

# Excel Form route
@app.route('/excel_form')
def excelForm():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM transactions WHERE user_id = ?", [session['userID']])
    data = cur.fetchall()
    cur.close()

    df = pd.DataFrame(data)

    # Save DataFrame to Excel file
    excel_file_path = 'transactions_data.xlsx'
    df.to_excel(excel_file_path, index=False)

    # Start the download
    return send_file(excel_file_path, as_attachment=True, download_name='transactions_data.xlsx')

if __name__ == '__main__':
    app.run(debug=True)
