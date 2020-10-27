from datetime import datetime, date, timedelta
from app.models import tabelas
from app import db
#CRIPTOGRAFIA DE SENHA
from werkzeug.security import generate_password_hash, check_password_hash
from app.api_iq import api_iq as api
import sqlite3, threading, time, pytz


ativos_comandos= ['AUD/CAD','AUD/CHF','AUD/JPY','AUD/USD','AUD/NZD','CAD/CHF','CAD/JPY','CHF/JPY','EUR/USD',
'EUR/USD-OTC','NZD/USD-OTC','AUD/CAD-OTC','GBP/USD-OTC','USD/CHF-OTC','EUR/GBP-OTC','EUR/JPY-OTC',
'EUR/GBP','EUR/CHF','EUR/AUD','EUR/NZD','EUR/JPY','GBP/JPY','GBP/CHF','GBP/AUD','GBP/CAD',
'GBP/USD','GBP/NZD','NZD/CHF','NZD/USD','NZD/JPY','USD/JPY','USD/CHF','USD/CAD','CALL','PUT'] 


#VERIFICA SE A HORA INFORMADA É VÁLIDA
def string_to_datetime(hora):    
    try:
       datetime.strptime(hora,'%H:%M')
       return True
    except :
        return False 

#CONVERTE O HOÁRIO PARA O TIMEZONE DE SÃO PAULO
def converte_data_timezone(data_hora):
    '''
    CONVERTE O HORÁRIO PARA O TIMEZONE DE SÃO PAULO
    '''
    data_hora_convertida = data_hora.astimezone(tz=pytz.timezone('America/Sao_Paulo'))
    return data_hora_convertida

#Cria as iformações padrão no se for o primeiro uso
def acesso(email,senha):
    user = tabelas.Usuario()
    gerencia = tabelas.Gerencia()

    #CONECTANDO COM A IQ OPTION    
 
    if not user.query.get(1):
        #nessa parte será feita a conxão com a iqoption
        user.email = email
        user.senha = generate_password_hash(senha)
        user.conectado= True
        #criptografia de senha            
        db.session.add(user)
        db.session.commit()
        gerencia.tipo_conta = 'DEMO'
        gerencia.stop_loss = 10
        gerencia.stop_gain = 10
        gerencia.pay_out_min = 70
        gerencia.delay = 1
        gerencia.lote =1
        gerencia.fil_entrada_sma = False
        gerencia.periodo_sma = 100
        gerencia.block_ord_todas = True
        gerencia.block_ord_mesmo_par= True
        gerencia.vela_cor_oposta = False
        gerencia.martingale_tipo = 1
        gerencia.martingale_retorno=0
        gerencia.id_user = 1
        # gerencia.saldo_dia = 0
        db.session.add(gerencia)
        db.session.commit()

        return True
    
    else:
        #SE JÁ EXISTIR UM USUÁRIO CADASTRADO PE A IFORMAÇÃO DO TIPO DE CONTA
        ger = tabelas.Gerencia.query.get(1)
        if ger.tipo_conta == 'DEMO':

            api.set_tipo_conta('PRACTICE')
        else:
            api.set_tipo_conta('REAL')
        
        user = tabelas.Usuario.query.get(1)
        # user.conectado = True
        # db.session.commit()
        # return True

        if check_password_hash(user.senha,senha):
            user.conectado = True
            db.session.commit()
            return True
        else:
            return False     
            
            




    

def importar_lista(usar_lista_em):
    '''
    O parâmetro usar_lista_em, deve receber 0, se for para usar a data atual
    , e 1 se for para usar no dia seguinte.
    '''
    try:
        arquivo = open('app/upload/lista_entradas.txt', 'r')

        for linha in arquivo:
            #lista = []
            #REMOVENDO OS ESPAÇO EM BRANCO

            linha = linha.replace('\n','')
            

            #CRIANDO A LISTA A PARTIR DO COMANDO SPLIT NA STRING LINHA
            lista = linha.split(';')
            # print(lista)

            hora_valida = string_to_datetime(lista[0])
            # ativo_valido = lista[1][:7].upper() in ativos_comandos
            comando_valido = lista[2].upper() in ativos_comandos
            

            if  hora_valida  and comando_valido:
                ger = tabelas.Gerencia.query.get(1)
                entrada = tabelas.Entrada()
                data_atual = converte_data_timezone(datetime.now()) + timedelta(days=usar_lista_em)
                entrada.data = data_atual.strftime('%Y-%m-%d')
                entrada.hora = lista[0]
                entrada.ativo = lista[1]
                entrada.duracao = 'M'+lista[3]
                entrada.tipo_ordem = lista[2]
                entrada.observacoes=''
                entrada.executar = True
                entrada.expirado = False
                entrada.enviada = False
                # entrada.block_todas = False
                # entrada.block_mesmo_par = False
                entrada.ciclo = 0
                entrada.martingale_ativo = False
                entrada.lote = 0
                entrada.id_user = 1
                entrada.resultado_op = 0
                entrada.tipo_conta = ''
                entrada.id_ini_martingale = 0
                db.session.add(entrada)
                
                
            else:
               exit() 
        

        db.session.commit()
        arquivo.close()
        return True
        
    except:
        arquivo.close() 
        return False
    finally:
        arquivo.close()

def deletar_lista():
    '''
    Deleta as Ordens que com o campo Exetucar.
    '''
    try:
        con = sqlite3.connect('app/banco.db',timeout=10)
        cur = con.cursor()
        data_atual = converte_data_timezone(datetime.now()) #datetime.fromtimestamp(api.API.get_server_timestamp())
        cur.execute('delete  from entrada where (executar = 0 or enviada = 0)'+
                ' and data >= ?',(data_atual.strftime('%Y-%m-%d'),))
        con.commit()
        con.close()
        
    except Exception as e:
        print('Falha funcoes_uteis.py em deletar_lista: ' + str(e))
    finally:
        con.close()
# def threaded(fn):
#     def wrapper(*args, **kwargs):
#         thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
#         thread.start()
#         return thread
#     return wrapper

# @threaded
# def conta_thread():
#     while True:
#         print('Total de threads: ' + str(threading.active_count()))
#         print('Nomes das threads: ' + str(threading.enumerate()))
#         time.sleep(3)
    

      