import os
import pandas as pd

from flask import flash, Flask, render_template, request, redirect
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import join

from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash

import plotly.graph_objs as go


app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)

app.config['SECRET_KEY'] = 'C2HWGVoMGfNT5srYQg8EcMrdTimkZfAb'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/finalproject'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
bootstrap = Bootstrap(app)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
                       
class Household(db.Model):
    __tablename__ = 'household'
    id = db.Column(db.Integer, primary_key=True)
    hshd_num = db.Column(db.Integer)
    l = db.Column(db.String(5))
    age_range = db.Column(db.String(50))
    marital = db.Column(db.String(50))
    income_range = db.Column(db.String(50))
    homeowner = db.Column(db.String(50))
    hshd_composition = db.Column(db.String(50))
    hh_size = db.Column(db.String(10))
    children = db.Column(db.String(10))

    
class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    product_num = db.Column(db.Integer)
    department = db.Column(db.String(50))
    commodity = db.Column(db.String(50))
    brand_ty = db.Column(db.String(50))
    natural_organic_flag = db.Column(db.String(5))

    
class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    basket_num = db.Column(db.Integer)
    hshd_num = db.Column(db.Integer, db.ForeignKey('household.hshd_num'))
    purchase_date = db.Column(db.String(10))
    product_num = db.Column(db.Integer, db.ForeignKey('product.product_num'))
    spend = db.Column(db.Float)
    units = db.Column(db.Integer)
    store_r = db.Column(db.String(10))
    week_num = db.Column(db.Integer)
    year = db.Column(db.Integer)
    
    
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

    
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    
class SearchForm(FlaskForm):
    hshd_num = StringField('Household Number', validators=[DataRequired()])
    submit = SubmitField('Search')
    
    
@app.route('/', methods=['GET', 'POST'])
def index():
    db.create_all()
    return render_template('index.html', current_user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None:
            flash('Please use a different username.')
            return redirect('/register')
        email = User.query.filter_by(username=form.email.data).first()
        if email is not None:
            flash('Please use a different email.')
            return redirect('/register')
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect('/login')
    return render_template('register.html', form=form, current_user=current_user)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect('/login')
        login_user(user)
        return redirect('/dashboard')
    logout_user()
    return render_template('login.html', form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        # Define the path to the directory where the files are stored
        data_dir = os.path.join(app.root_path, 'data')

        # Load the most recent Transaction file
        transaction_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if 'transaction' in f]
        if len(transaction_files) > 0:
            latest_transaction_file = max(transaction_files, key=os.path.getctime)
            transaction_df = pd.read_csv(latest_transaction_file)
            transaction_df.to_sql('Transaction', con=db.engine, if_exists='replace', index=False)

        # Load the most recent Household file
        household_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if 'household' in f]
        if len(household_files) > 0:
            latest_household_file = max(household_files, key=os.path.getctime)
            household_df = pd.read_csv(latest_household_file)
            household_df.to_sql('Household', con=db.engine, if_exists='replace', index=False)

        # Load the most recent Product file
        product_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if 'product' in f]
        if len(product_files) > 0:
            latest_product_file = max(product_files, key=os.path.getctime)
            product_df = pd.read_csv(latest_product_file)
            product_df.to_sql('Product', con=db.engine, if_exists='replace', index=False)

        flash('Data loaded successfully.')
        return redirect('/dashboard')

    # Household size vs. total spend
    household_size = db.session.query(Household.hh_size, db.func.sum(Transaction.spend))\
        .join(Transaction, Household.hshd_num == Transaction.hshd_num)\
        .group_by(Household.hh_size).all()
    household_size_df = pd.DataFrame(household_size, columns=['Household Size', 'Total Spend'])

    # Presence of children vs. total spend
    presence_of_children = db.session.query(Household.children, db.func.sum(Transaction.spend))\
        .join(Transaction, Household.hshd_num == Transaction.hshd_num)\
        .group_by(Household.children).all()
    presence_of_children_df = pd.DataFrame(presence_of_children, columns=['Presence of Children', 'Total Spend'])

    # Income range vs. total spend
    income_range = db.session.query(Household.income_range, db.func.sum(Transaction.spend))\
        .join(Transaction, Household.hshd_num == Transaction.hshd_num)\
        .group_by(Household.income_range).all()
    income_range_df = pd.DataFrame(income_range, columns=['Income Range', 'Total Spend'])

    # Create bar charts
    household_size_chart = go.Bar(
        x=household_size_df['Household Size'],
        y=household_size_df['Total Spend'],
        name='Household Size'
    )
    presence_of_children_chart = go.Bar(
        x=presence_of_children_df['Presence of Children'],
        y=presence_of_children_df['Total Spend'],
        name='Presence of Children'
    )
    income_range_chart = go.Bar(
        x=income_range_df['Income Range'],
        y=income_range_df['Total Spend'],
        name='Income Range'
    )
    data = [household_size_chart, presence_of_children_chart, income_range_chart]
    layout = go.Layout(
        title='Demographic Factors Affecting Customer Engagement',
        xaxis=dict(title='Demographic Factor'),
        yaxis=dict(title='Total Spend')
    )
    fig = go.Figure(data=data, layout=layout)
    graph = fig.to_html(full_html=False)

    # Summary table
    summary = pd.DataFrame({'Households': [household_size_df['Total Spend'].count()],
                            'Total Spend': [household_size_df['Total Spend'].sum()]})

    return render_template('dashboard.html', graph=graph, summary=summary.to_html(index=False), current_user=current_user)
    

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    if form.validate_on_submit():
        hshd_num = form.hshd_num.data
        data = Product.query.join(Transaction).filter_by(hshd_num=hshd_num).order_by(
            Transaction.hshd_num, Transaction.basket_num, Transaction.purchase_date, 
            Transaction.product_num).with_entities(
            Transaction.hshd_num, Transaction.basket_num, Transaction.purchase_date, 
            Transaction.product_num, Product.department, Product.commodity).all()
        return render_template('search.html', data=data, form=form, current_user=current_user)
    return render_template('search.html', form=form, current_user=current_user)



if __name__ == '__main__':
    app.run(debug=True)
