from flask import Flask, render_template, url_for, redirect,request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from flask_uploads import UploadSet,configure_uploads,ALL,DATA,IMAGES
from tensorflow.keras.models import load_model
from matplotlib.image import imread
import tensorflow_hub as hub
import cv2
import numpy as np
from PIL import Image
from datetime import datetime

app=Flask(__name__)
db=SQLAlchemy(app)
bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecret'


login_manager = LoginManager()  #help our app with flasklogin app  and to login load user from id
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader     
def load_user(user_id):          # Use reload the object stored in the userobject session
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):             # Create Userdetails in database
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

class RegisterForm(FlaskForm):               #Regitor form created for new user
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    def validate_username(self, username):                    # If user already present in the database, will give the  output as alreadyy present in database
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                'That username already exists. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')


class CarScan(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    image = db.Column(db.BLOB())
    status = db.Column(db.String(200))
    date_created = db.Column(db.DateTime,default=datetime.utcnow)

    def __repr__(self):
        return '<Car %r>'% self.id

model = load_model('static/model/mobilenewcar.h5',custom_objects={'KerasLayer': hub.KerasLayer})

photos = UploadSet('photos',IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = 'static/img'
configure_uploads(app,photos)

def readImage(img_name):
   try:
       fin = open(img_name, 'rb')
       img = fin.read()
       return img
   except:
       print("ERROR!!")
def is_damaged(image):
    image = imread('static/img/'+image)
    scaled_image = cv2.resize(image,(224,224))
    scaled_image = scaled_image/255
    scaled_image = scaled_image.reshape(1,224,224,3)
    return model.predict(scaled_image)

 
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login',methods=['GET','POST'])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()   # check first if the user has the details in database
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):      #check/comparing password in in database and user entered
                login_user(user)
                return redirect(url_for('dashboard'))
    return render_template('login.html',form=form)

# @app.route('/checkdata')
# def check():
#     cars = CarScan.query.order_by(CarScan.date_created).all()
#     return render_template('data.html',cars=cars)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST' and 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        answer = is_damaged(filename)
        answer = round(answer[0][0]*100,2)

        img_name = imread(f'static/img/{filename}')
        car_img_binary = np.where(img_name>128,255,0)

        # add_status = CarScan(status = answer)
        # print(type(add_status))
        # add_image = CarScan(image = car_img_binary)
        # try:
        #     db.session.add(add_status)
        #     db.session.add(add_image)
        #     db.session.commit()
        # except:
        #     return 'There was a problem storing the image and status report'

        return render_template('dashboard.html',filename=filename,answer = answer)
    return render_template('dashboard.html',filename= '0188.jpg',answer=0)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))



@app.route('/register',methods=['GET','POST']) 
def register():
    form=RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html',form=form)

if __name__ == "__main__":
    app.run(debug=True)