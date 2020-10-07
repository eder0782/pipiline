from flask import Flask
from flask_sqlalchemy import SQLAlchemy




application = Flask(__name__)


application.config['SQLALCHEMY_DATABASE_URI']= 'sqlite:///banco.db'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
application.config['SECRET_KEY'] = '#15431%¨15448*'

db =SQLAlchemy(application)



from app.models import tabelas


from app.controlers import rotas





