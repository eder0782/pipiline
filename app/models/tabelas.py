from app import db
from app import application as app

#GERENCIAMENTO DE SESSÃO
from flask_login import LoginManager, UserMixin


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuario"    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique = True)
    senha = db.Column(db.String(120))
    conectado = db.Column(db.Boolean)

       

class Gerencia(db.Model):
    __tablename__ = "gerencia"
    id = db.Column(db.Integer, primary_key=True)
    tipo_conta= db.Column(db.String(15),nullable= False)
    stop_loss= db.Column(db.Float,nullable= False)
    stop_gain= db.Column(db.Float,nullable= False)
    pay_out_min = db.Column(db.Integer,nullable= False)
    delay = db.Column(db.Integer,nullable= False)
    lote = db.Column(db.Float,nullable= False)
    fil_entrada_sma= db.Column(db.Boolean )
    periodo_sma= db.Column(db.Integer)
    block_ord_todas= db.Column(db.Boolean)
    block_ord_mesmo_par = db.Column(db.Boolean)
    vela_cor_oposta = db.Column(db.Boolean)
    #SE FOR TIPO 1 É O GALE PADRÃO, CASO CONTRÁRIO É UM GALE PERSONALISADO
    martingale_tipo = db.Column(db.Integer)
    martingale_retorno= db.Column(db.Float)   
  
    #chave estrangeira
    id_user = db.Column(db.Integer,db.ForeignKey('usuario.id'), nullable = False)

class Entrada(db.Model):
    __tablename__ = "entrada"    
    id = db.Column(db.Integer, primary_key=True)
    hora = db.Column(db.String(20), nullable = False)
    data = db.Column(db.String(20), nullable=False)
    ativo = db.Column(db.String(20), nullable= False)
    duracao = db.Column(db.String(3), nullable = False)
    tipo_ordem = db.Column(db.String(10), nullable = False)
    observacoes = db.Column(db.String(50))
    executar = db.Column(db.Boolean)
    enviada = db.Column(db.Boolean)
    expirado = db.Column(db.Boolean)
    #CAMPOS PARA GERENCIAR O MARTINGALE
    ciclo = db.Column(db.Integer)
    lote = db.Column(db.Float)
    martingale_ativo = db.Column(db.Boolean)
    id_ini_martingale = db.Column(db.Integer)
    resultado_op = db.Column(db.Float)
    tipo_conta = db.Column(db.String(20))
   
    id_ordem = db.Column(db.Integer)
    id_user = db.Column(db.Integer,db.ForeignKey('usuario.id'), nullable = False)