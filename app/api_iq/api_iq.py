from .iqoptionapi.stable_api import IQ_Option
import time
from datetime import datetime, date, timedelta
from dateutil import tz
import sys, json, os
import threading
from app.api_iq import chamar_api
from app.models import tabelas 
from app import db
from app.controlers import funcoes_uteis as func


API = None

#ESSA VARIÁVEL FOI CRIADA PARA PODER LISTAR OS ATIVOS 
#UMA VEZ QUE USAR APENAS A API DÁ PROBLEMA AO FAZER API.CONECT()
API_LISTA_AT = None

ORDEM_BIN_ABERTA = []
ORDEM_DIG_ABERTA = []

ATIVO = True

LISTA_INFO_CONTA={}

#ESSA VARIÁVEL É USADA PARA TESTAR SE JÁ ATINGIU O STOPLOSS OU STOPGAIN
# SALDO_DIA = 0

# LISTA_ATIVOS_ONLINE={}
LISTA_BINARIA ={}
LISTA_DIGITAL ={}
LISTA_PAYOUT_BINARY={}
#ESTOU USANDO ESTA VARIÁVEL PARA MONITORAR SE A ROTINA DE LISTAR ATIVOS ONLINE ESTÁ FUNCIONANDO
HORA_LISTA_PAYOUT = None

 ############################################################
 # THEAD USADA COMO DECORADOR                               #
 ############################################################ 
# def threaded(fn):
#     def wrapper(*args, **kwargs):
#         thread = threading.Thread(target=fn, args=args, kwargs=kwargs)        
#         thread.start()       
#         return thread
#     return wrapper
def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper
############################################################

def restart_program():
    python = sys.executable
    os.execl(python, python, * sys.argv)

def get_status_conexao():
    try:
        if API.check_connect():
            return True
        else:
            return False

    except Exception as e:
        print('Falha api.py get_status_conexao : ' + str(e) )
        return False

    


def conectar(email,senha):
    global API, API_LISTA_AT
   
    API = IQ_Option(email=email,password=senha)
    API_LISTA_AT = IQ_Option(email=email,password=senha)
    
    API.connect()
    API_LISTA_AT.connect()

    retorno = None
    for i in range(5):    
        if API.check_connect() == False:
                   		
            API.connect()
            API_LISTA_AT.connect()
            retorno = False
        else:
           
            retorno = True
            break
        
        time.sleep(1)
    
    return retorno


def set_tipo_conta(tipo_conta):
    try:
        
        global API
        
        API.change_balance(tipo_conta)
        return True
    except Exception as e:
        print(' Falha api.py set_tipo_conta : ' + str(e))
        return False

def get_info_conta():
    
    CONTA_DEMO={}
    CONTA_REAL={}
    global API
    global LISTA_INFO_CONTA
    try:
                
        if API.check_connect():

            if API.get_balance_mode()== 'PRACTICE':
                
                CONTA_DEMO['conectado']=True
                CONTA_DEMO['banca']=API.get_balance()
                CONTA_DEMO['saldo_dia']=saldo_do_dia()
                LISTA_INFO_CONTA['demo']= CONTA_DEMO
                           
                # SALDO_DIA = CONTA_DEMO['saldo_dia']
            else:
               
                CONTA_REAL['conectado']=True
                CONTA_REAL['banca']=API.get_balance()
                CONTA_REAL['saldo_dia']=saldo_do_dia()
                LISTA_INFO_CONTA['real']= CONTA_REAL
                
                # SALDO_DIA = CONTA_REAL['saldo_dia']

        else:

            CONTA_DEMO['conectado']=False
            CONTA_DEMO['banca']=0
            CONTA_DEMO['saldo_dia']=0
            LISTA_INFO_CONTA['demo']= CONTA_DEMO

            CONTA_REAL['conectado']=False
            CONTA_REAL['banca']=0
            CONTA_REAL['saldo_dia']=0
            LISTA_INFO_CONTA['real']= CONTA_REAL

            
    except Exception as e:
        print('Falha api.py get_info_conta: ' + str(e))
        CONTA_DEMO['conectado']=False
        CONTA_DEMO['banca']=0
        CONTA_DEMO['saldo_dia']=0
        LISTA_INFO_CONTA['demo']= CONTA_DEMO

        CONTA_REAL['conectado']=False
        CONTA_REAL['banca']=0
        CONTA_REAL['saldo_dia']=0
        LISTA_INFO_CONTA['real']= CONTA_REAL

def get_balanco():
    try:
        return API.get_balance()
    except :
        return 0

def desconectar():
    try:

        global ATIVO
        
        API.api.logout()
        API.api.close()
        
        #VARIÁVEL RESPONSÁVEL PELO LAÇO WHILE QUE INICIA O BOT
        ATIVO = False
        return True
    except :
        return False

def historico_ops(derrad_close_time=0,limite=10, inicio=0, final=0):
    #CAPTURA O RESULTADO DAS ORDENS 
    #O LIMITE PADRÃO É DAS ÚLTIMAS 10 ORDENS
    grupo=['digital-option','turbo-option', 'binary-option']    
    lista=[]
    for gp in grupo:
       
        global API      
        status, historico = API.get_position_history_v2(gp,limite,0,inicio,final)

        if historico['positions']:      
     
            for hist in historico['positions']:
                # hora_fechamento = func.converte_data_timezone(datetime.fromtimestamp(hist['close_time']/1000))
                # if int(hora_fechamento.timestamp())>=int(inicio):            
                dicionario ={}  
                dicionario['id']= hist['id']
                dicionario['investimento']=hist['invest']
                dicionario['close_time'] = datetime.fromtimestamp(hist['close_time']/1000) #timestamp_converter(hist['close_time']/1000)
                #SE O CLOSE PROFIT FOR ZERO, RETORNA O VALOR DO INVESTIMENTO *-1, IDICANDO O VALOR PERDIDO
                #SE O CLOSE PROFIT FOR MAIOR QUE 1, RETORNA O CLOSE-PROFIT - INVEST, INDICANDO O VALOR QUE FOI GANHO
                dicionario['resultado'] = hist['close_profit']-hist['invest'] if hist['close_profit']!=0 else hist['invest']*-1  
                lista.append(dicionario)           

    return lista
    

def saldo_do_dia():
    try:
        #PEGANDO A DATA DO SERVIDOR
        data_atual = func.converte_data_timezone(datetime.now()) #datetime.fromtimestamp(API.get_server_timestamp())
        dia = int(data_atual.strftime('%d'))
        # dia_ini = data_atual.strftime('%d/%m/%Y') + ' 00:00'
        data_ini = data_atual.replace(day=dia-1,hour=0,minute=0,second=0) #datetime.strptime(dia_ini,'%d/%m/%Y %H:%M')       
        # dia_fin = data_atual.strftime('%d/%m/%Y') + ' 23:59'        
        # data_fin = datetime.strptime(dia_fin,'%d/%m/%Y %H:%M')       
        

        operacoes = historico_ops(0,inicio=int(data_ini.timestamp()),limite=100)
        saldo=0
        
        for op in operacoes:
            # print()
            if func.converte_data_timezone(op['close_time'])>=data_atual.replace(hour=0,minute=0,second=0):
                saldo+= op['resultado']
    
        return round(saldo,2)
    except Exception as e:
        print('Falha api.py saldo_do_dia: ' + str(e))
        return False

# @threaded
def compra_op_binaria(ativo,lote,timeframe,direcao,id_tb_entrada,martingale_ativo, ciclo_marting,id_martin,id_ini_martingale):
    '''
    O PARAMETRO DE MARINGALE ATIVO, SERVE APENAS PARA QUE A INFORMAÇÃO QUE
    DE QUE ESTÁ USANDO MARTINGALE, SEJA ARMAZENADA NO CAMPO DE OBSERVAÇÕES
    E MOSTRADO PARA O USUÁRIO.
    '''
    try:
        global ORDEM_BIN_ABERTA
        check,id=API.buy(lote,str(ativo.replace('/','')).upper(),str(direcao).lower(),timeframe)
        if check:

            entrada = tabelas.Entrada.query.get(id_tb_entrada)
            entrada.observacoes='Aguardando...'
            ger = tabelas.Gerencia.query.get(1)
            entrada.tipo_conta = ger.tipo_conta
            entrada.enviada=True
            db.session.commit()

            #ESTA PARTE FOI REMOVIDA, POIS O MARTINGALE É EXECUTADO DE OUTRA FORMA AGORA
            # #MODIFICA A LINHA DA TABELA QUE ESTA COM O MARTINGALE ATIVO
            # if id_martin !=0:
            #     #ATRIBUINDO O ID DO MARTINGALE NO ID_INI_MARTINGALE DA ORDEM ATUAL
            #     entrada_id_entrada = tabelas.Entrada.query.get(int(id_tb_entrada))
            #     entrada_id_entrada.id_ini_martingale = id_martin if id_ini_martingale == 0 else id_ini_martingale
            #     db.session.commit()             
                

            #SE A ORDEM FOI ACEITA, INICIAO O ACOMPNHAMENTO DO RESULTADO
            td_resultado_ordem_binaria(id,id_tb_entrada,martingale_ativo, ciclo_marting)

            hora_expiracao = func.converte_data_timezone(datetime.now()) + timedelta(minutes=timeframe) + timedelta(seconds=10)
            hora_expiracao = hora_expiracao.replace(second=0,microsecond=0)
            print(hora_expiracao)
            #PEGA O HORÁRIO DE EXPIERAÇÃO DA ORDEM
            ORDEM_BIN_ABERTA.append(hora_expiracao)
            # print(ORDEM_BIN_ABERTA)
        else:
            entrada = tabelas.Entrada.query.get(id_tb_entrada)
            entrada.observacoes='Ignorado...Paridade/TimeFrame Inativo!'
            entrada.executar=False
            entrada.enviada=True
            db.session.commit()
            #SE A ENTRADA FALHAR, O CAMPO martingale_ativo VOLTA A SER TRUE
            if id_martin !=0:
                entrada4 = tabelas.Entrada.query.get(int(id_martin))
                entrada4.martingale_ativo = True                            
                db.session.commit()

    except Exception as e :
        entrada = tabelas.Entrada.query.get(id_tb_entrada)
        entrada.observacoes='Falha na conexão com a IQ Option!'
        entrada.executar=False
        entrada.enviada=True
        db.session.commit()
        print('Falha na execução da compra binária: ' + str(e))

        

# @threaded
def compra_op_digital(ativo,lote,timeframe,direcao,id_tb_entrada,martingale_ativo, ciclo_marting,id_martin,id_ini_martingale):
    '''
    O PARAMETRO DE MARINGALE ATIVO, SERVE APENAS PARA QUE A INFORMAÇÃO QUE
    DE QUE ESTÁ USANDO MARTINGALE, SEJA ARMAZENADA NO CAMPO DE OBSERVAÇÕES
    E MOSTRADO PARA O USUÁRIO.
    '''
    try:
        global ORDEM_DIG_ABERTA
        status,id= API.buy_digital_spot(str(ativo).upper(),lote,str(direcao).lower(),timeframe)

        if status:
            # hora = func.converte_data_timezone(datetime.now()) + timedelta(minutes= timeframe)
            #PEGANDO O HORÁRIO DE EXPIRAÇÃO DA ORDEM
            ORDEM_DIG_ABERTA.append(calcula_horario_expiraca(timeframe))
            # print(ORDEM_DIG_ABERTA)

            entrada = tabelas.Entrada.query.get(id_tb_entrada)
            entrada.observacoes='Aguardando...'
            ger = tabelas.Gerencia.query.get(1)
            entrada.tipo_conta = ger.tipo_conta
            entrada.enviada=True
            db.session.commit()
            #MODIFICA A LINHA DA TABELA QUE ESTA COM O MARTINGALE ATIVO
            if id_martin!=0:                
                 #ATRIBUINDO O ID DO MARTINGALE NO ID_INI_MARTINGALE DA ORDEM ATUAL
                entrada_id_entrada = tabelas.Entrada.query.get(int(id_tb_entrada))
                entrada_id_entrada.id_ini_martingale = id_martin if id_ini_martingale == 0 else id_ini_martingale
                db.session.commit()   
            #SE A ORDEM FOR ACEITA INICIA O ACOMPANHAMENTO
            td_resultado_ordem_digital(id,lote,id_tb_entrada,martingale_ativo, ciclo_marting)

        else:
            entrada = tabelas.Entrada.query.get(id_tb_entrada)
            entrada.observacoes='Ignorado...Paridade/TimeFrame Inativo!'
            entrada.executar=False
            entrada.enviada=True
            db.session.commit()
            #SE A ENTRADA FALHAR, O CAMPO martingale_ativo VOLTA A SER TRUE
            if id_martin!=0:
                entrada4 = tabelas.Entrada.query.get(int(id_martin))
                entrada4.martingale_ativo = True                            
                db.session.commit()


    except Exception as e:
        entrada = tabelas.Entrada.query.get(id_tb_entrada)
        entrada.observacoes='Falha na conexão com a IQ Option!'
        entrada.executar=False
        entrada.enviada=True
        db.session.commit()
        print('Falha na compra binária:  ' + str(e))

# @threaded
def resultado_ordem_digital(id_ordem,valor_entrada,id_tb_entrada, martingale_ativo, ciclo_marting):
    '''
    O PARAMETRO DE MARINGALE ATIVO, SERVE APENAS PARA QUE A INFORMAÇÃO QUE
    DE QUE ESTÁ USANDO MARTINGALE, SEJA ARMAZENADA NO CAMPO DE OBSERVAÇÕES
    E MOSTRADO PARA O USUÁRIO.
    '''
    try:
        global ORDEM_DIG_ABERTA
        if isinstance(id_ordem, int):
            mensagem_marting = (' | CICLO DE GALE N' + str(ciclo_marting)) if martingale_ativo else ''
            while True:
                status,lucro = API.check_win_digital_v2(id_ordem)
                
                if status:
                    
                    if lucro > 0:
                        entrada = tabelas.Entrada.query.get(id_tb_entrada)
                        entrada.observacoes='RESULTADO: WIN | VALOR: '+str(float(round(lucro, 2))) + mensagem_marting
                        entrada.resultado_op = float(round(lucro,2))
                        db.session.commit()
                        #REMOVENDO O HORÁRIO DA LISTA DE ORDENS PENDENTES
                        hora_expiracao = func.converte_data_timezone(datetime.now()) + timedelta(seconds=10)
                        hora_expiracao = hora_expiracao.replace(second=0,microsecond=0)
                        if hora_expiracao in ORDEM_DIG_ABERTA:
                            ORDEM_DIG_ABERTA.remove(hora_expiracao)
                        
                        break
                    else:                                                  
                           
                        #REMOVENDO O HORÁRIO DA LISTA DE ORDENS PENDENTES
                        hora_expiracao2 = func.converte_data_timezone(datetime.now()) + timedelta(seconds=10)
                        hora_expiracao2 = hora_expiracao2.replace(second=0,microsecond=0)
                        if hora_expiracao2 in ORDEM_DIG_ABERTA:
                            ORDEM_DIG_ABERTA.remove(hora_expiracao2)

                        entrada = tabelas.Entrada.query.get(id_tb_entrada)
                        entrada.observacoes='RESULTADO: LOSS | VALOR: '+str(float(round(valor_entrada*-1,2))) + mensagem_marting
                        #VERIFICA SE O CILO DE MARTINGALE É MENOR QUE FOI PARA PODER GERAR UM NOVO CICLO
                        entrada.resultado_op = float(round(valor_entrada*-1,2))                   
                        db.session.commit()
                        if ciclo_marting<2:
                            entrada = tabelas.Entrada.query.get(id_tb_entrada)
                            ativo = entrada.ativo
                            timeframe = entrada.duracao
                            direcao = entrada.tipo_ordem
                            hora_entrada = entrada.hora
                            id_ini_martingale =entrada.id_ini_martingale
                            
                            if  entrada.id_ini_martingale ==0:
                                id_ini_martingale= id_tb_entrada
                            martingale(ativo,timeframe,direcao,id_tb_entrada,ciclo_marting,id_ini_martingale,hora_entrada)
                    
                        break
                time.sleep(0.5)
    except Exception as e:
        entrada = tabelas.Entrada.query.get(id_tb_entrada)
        entrada.observacoes='Falha na conexão com a IQ Option!'
        entrada.executar=False
        entrada.enviada=True
        db.session.commit()
        print(' Falha api.py resultado_ordem_digital: ' + str(e))

            

# @threaded
def resultado_ordem_binaria(id_ordem,id_tb_entrada,martingale_ativo, ciclo_marting):
    '''
    O PARAMETRO DE MARINGALE ATIVO, SERVE APENAS PARA QUE A INFORMAÇÃO QUE
    DE QUE ESTÁ USANDO MARTINGALE, SEJA ARMAZENADA NO CAMPO DE OBSERVAÇÕES
    E MOSTRADO PARA O USUÁRIO.
    '''
    try:
        global ORDEM_BIN_ABERTA
        resultado,lucro = API.check_win_v4(id_ordem)
        print('Resultado: ' + str(resultado))
        print('Lucro: ' + str(lucro))
        print('id_ordem: ' + str(id_ordem))
        if resultado == 'loose' and ciclo_marting<2:
            entrada = tabelas.Entrada.query.get(id_tb_entrada)    
            # entrada.ciclo = ciclo_marting +1
            entrada.resultado_op = float(round(lucro,2))
            entrada.martingale_ativo = True
            db.session.commit()         
            
            ativo = entrada.ativo
            timeframe = entrada.duracao
            direcao = entrada.tipo_ordem
            hora_entrada = entrada.hora
            id_ini_martingale =entrada.id_ini_martingale
            
            if  entrada.id_ini_martingale ==0:
                id_ini_martingale= id_tb_entrada
            martingale(ativo,timeframe,direcao,id_tb_entrada,ciclo_marting,id_ini_martingale,hora_entrada)
                    

        #SE O RESULTADO FOR ZERO, REPETE O CICLO DE MARTINGALE
        if lucro == 0 and martingale_ativo and ciclo_marting<=2:
            entrada = tabelas.Entrada.query.get(id_tb_entrada)    
            entrada.resultado_op = float(round(lucro,2))   
            # entrada.martingale_ativo = True
            db.session.commit()
            ativo = entrada.ativo
            timeframe = entrada.duracao
            direcao = entrada.tipo_ordem
            hora_entrada = entrada.hora
            id_ini_martingale =entrada.id_ini_martingale
            # DIMINUI U CICLO DE MARTINGALE EM 1, PARA PODER REFAZER O MESMO CICLO
            cliclo_mart_lucro_zero = ciclo_marting-1          
            
            if  entrada.id_ini_martingale ==0:
                id_ini_martingale= id_tb_entrada
            martingale(ativo,timeframe,direcao,id_tb_entrada,cliclo_mart_lucro_zero,id_ini_martingale,hora_entrada)
                    


        #REMOVENDO O HORÁRIO DA LISTA DE ORDENS PENDENTES
        hora_expira = func.converte_data_timezone(datetime.now()) + timedelta(seconds=10)
        hora_expira = hora_expira.replace(second=0,microsecond=0)
        if hora_expira in ORDEM_BIN_ABERTA:
            ORDEM_BIN_ABERTA.remove(hora_expira)
            
        mensagem_marting = (' |CICLO DE GALE N'+ str(ciclo_marting)) if martingale_ativo else ''
        # print('ciclo_marting: ' + str(ciclo_marting)) 
        # print('martingale_ativo: ' + str(martingale_ativo))  
        # print('mensagem_marting: ' +str(mensagem_marting))
        resposta_win = 'RESULTADO: WIN'+' |  VALOR: '+str(float(round(lucro, 2))) + mensagem_marting
        resposta_loss = 'RESULTADO: LOSS'+' |  VALOR: '+str(float(round(lucro, 2))) + mensagem_marting
        resposta_equal = 'RESULTADO: EQUAL'+' |  VALOR: '+str(float(round(lucro, 2))) + mensagem_marting
        resposta =resposta_win if resultado== 'win' else resposta_loss 
        if resultado=='equal':
            resposta = resposta_equal

        # resposta = resposta_loss 
        # print('resposta: ' + str(resposta))
        entrada = tabelas.Entrada.query.get(id_tb_entrada)
        entrada.resultado_op = float(round(lucro,2))
        
        entrada.observacoes= resposta
             
        #VERIFICA SE O RESULTADO FOI LOSS E SE O CILO DE MARTINGALE É MENOR QUE DOIS PARA PODER GERAR UM NOVO CICLO
    
        db.session.commit()
        
    except Exception as e:
        entrada = tabelas.Entrada.query.get(id_tb_entrada)
        entrada.observacoes='Falha na conexão com a IQ Option!'
        entrada.executar=False
        entrada.enviada=True
        db.session.commit()
        print('Falha api.py resultado_ordem_binaria: ' + str(e))


def martingale(ativo,timeframe,direcao,id_tb_entrada, ciclo_marting,id_ini_martingale,hora_entrada):
    try:
        

        entrada = tabelas.Entrada()
               
        entrada.ativo = ativo
        entrada.duracao = timeframe
        entrada.tipo_ordem = direcao
        entrada.observacoes=''
        entrada.executar = False
        entrada.expirado = False
        entrada.enviada = True
        # entrada.block_todas = False
        # entrada.block_mesmo_par = False
        entrada.ciclo = ciclo_marting +1
        entrada.martingale_ativo = True
        
        entrada.id_user = 1
        entrada.resultado_op = 0
        entrada.tipo_conta = ''
        entrada.id_ini_martingale = id_ini_martingale

        #REMOVEMENDO A / DO NOME DO ATIVO
        ativo_entrada =str(ativo).replace('/','')
         
        duracao_entrada =str(timeframe).replace('M','')
        #VERIFICA SE O TIMEFRAM É EM HORA
        if 'H' in duracao_entrada:
            duracao_entrada= duracao_entrada.replace('H','')
            duracao_entrada= int(duracao_entrada)*60
        
        
        #CALCULANDO A HORA DA ENTRADA
        data_atual = func.converte_data_timezone(datetime.now()) 
        
        hora = hora_entrada[:2]        
        minuto = hora_entrada[3:]
        
        data_atual = data_atual.replace(hour=int(hora),minute=int(minuto),second=0) + timedelta(minutes=int(duracao_entrada))
        entrada.hora = data_atual.strftime('%H:%M')
        entrada.data = data_atual.strftime('%Y-%m-%d')

        

        #CALCULANDO O LOTE DE MARTINGALE
        melho_payout, valor_payout= get_melhor_payout(ativo_entrada.upper(),int(duracao_entrada))
        lote_marging = chamar_api.get_lote_martingale(id_ini_martingale,valor_payout)
        entrada.lote = lote_marging

        db.session.add(entrada)
        db.session.commit()

        id_tb_entrada_atual = entrada.id
        id_martin = 0

        if melho_payout == 1:
            td_compra_op_digital(ativo_entrada.upper(),float(lote_marging),int(duracao_entrada),str(direcao).lower(),int(id_tb_entrada_atual),True,ciclo_marting+1,id_martin,id_ini_martingale)
        elif melho_payout ==2:
            td_compra_op_binaria(ativo_entrada.upper(),float(lote_marging),int(duracao_entrada),str(direcao).lower(),int(id_tb_entrada_atual),True,ciclo_marting+1,id_martin,id_ini_martingale)
        elif melho_payout == 0:
            mensagem ='Ignorado...Payout Atual é menor que o mínimo permitido! -CR'
            # entrada = tabelas.Entrada.query.get(int(id_tb_entrada_atual))
            entrada.executar = False
            entrada.observacoes = mensagem
            db.session.commit()                        
        elif melho_payout == -1:
            mensagem ='Ignorado...Paridade/TimeFrame Inativo! - CR'
            # entrada = tabelas.Entrada.query.get(int(id_tb_entrada_atual))
            entrada.executar = False
            entrada.observacoes = mensagem
            db.session.commit()
        else:
            pass





    
    except Exception as e:
        print('Falha api.py mantingale: '+ str(e))


def payout_bin():
    try:
        global LISTA_PAYOUT_BINARY
        l_bin =API.get_all_profit()
        LISTA_PAYOUT_BINARY = l_bin
    except Exception as e:
        print('Falha api.py payout_bin: '+ str(e))

def calcula_horario_expiraca(timeFrame):
    '''
    RETORNA O HORÁRIO DE EXPIERAÇÃO DA ORDEM
    '''
    hora_entrada = func.converte_data_timezone(datetime.now()) + timedelta(seconds=10)
    hora_entrada = hora_entrada.replace(second=0,microsecond=0)
    minutos = int(hora_entrada.strftime('%M'))
    if timeFrame== 60:
        if minutos!=0:
            hora_expira = hora_entrada + timedelta(minutes=timeFrame) - timedelta(minutes=minutos)
            return hora_expira
        else:
            hora_expira = hora_entrada + timedelta(minutes=timeFrame)
            return hora_expira
    else:
        resto_divisao = minutos%timeFrame
        if resto_divisao!=0:
            hora_expira = hora_entrada + timedelta(minutes=timeFrame) - timedelta(minutes=resto_divisao)
            return hora_expira
        else:
            hora_expira = hora_entrada + timedelta(minutes=timeFrame)
            return hora_expira
        
def get_melhor_payout(ativo,timeframe):
    '''
    Se o melhor payoute for Digital, retorna 1 \n
    Se for Binario retorna 2 \n
    Se não estiver ativo, retorna -1 \n
    Se o payout for menor que o mínimo retorna 0\n
    Retorna também o valor o payout para usar no martingale
    
    '''
    try:

        chamar_api.PAYOUT_MIN

        par_online_binary=LISTA_BINARIA
        par_online_digital = LISTA_DIGITAL
        payout_binary = LISTA_PAYOUT_BINARY

        if par_online_binary['binary'][ativo.upper()]['open'] == True:
            StatusB = int(payout_binary[ativo.upper()]['binary'] *100)
        else:
            StatusB = 0

        if par_online_binary['turbo'][ativo.upper()]['open'] == True:
            StatusT = int(payout_binary[ativo.upper()]['turbo'] *100)
        else:
            StatusT = 0

        if ativo in par_online_digital:
            StatusD = int(par_online_digital[ativo.upper()])
        else:
            StatusD = 0
        #SE O PAR NÃO ESTIVER ATIVO
        if StatusB==0 and StatusD ==0 and StatusT==0:
            return -1,0

        
        # Status_retorno = 0

        if StatusB > StatusD and timeframe > 5:
            id_entrada = 2
            payout_ = int(StatusB)
        elif StatusD >= StatusB and timeframe > 5 and timeframe<=15:
            id_entrada = 1
            payout_ = int(StatusD)                        
        elif StatusD >= StatusT and timeframe <=5:
            id_entrada = 1
            payout_ = int(StatusD)
        elif StatusT > StatusD and timeframe <=5 :
            id_entrada = 2
            payout_ = int(StatusT)
        elif  StatusB!=0 and timeframe>15:        
            id_entrada = 2
            payout_ = int(StatusB)
        elif StatusB==0 and timeframe>15:
            id_entrada = 0
            payout_ = 0
        
        if payout_ >= chamar_api.PAYOUT_MIN:
            return id_entrada, payout_
        else:
            return 0, payout_

    except Exception as e:
        print('Falha api_iq.py get_melhor_payout: '+ str(e))
        return 0,0


        


def payout_digital(par, tipo, timeframe = 1):

   
    # if tipo == 'turbo':
    # 	a = API.get_all_profit()
    # 	return int(100 * a[par]['turbo'])
    try:
        if tipo == 'digital':

            API_LISTA_AT.subscribe_strike_list(par, timeframe)
            for i in range(10):
                d = API_LISTA_AT.get_digital_current_profit(par, timeframe)
                if d != False:
                    d = int(d)
                    break
                time.sleep(1)
            API_LISTA_AT.unsubscribe_strike_list(par, timeframe)
            if d == False:
                return 0
            else:
                return d
    except Exception as e:
        print('Falha api.py payout_digital: ' + str(e))
        return 0


def lista_pares_ativos():
    try:
        # hora_ini= datetime.now()
        par = API_LISTA_AT.get_all_open_time()
        global LISTA_BINARIA,LISTA_DIGITAL, HORA_LISTA_PAYOUT
        LISTA_BINARIA = par
        li_dig = {}
        # payout_zero = False
        data = func.converte_data_timezone(datetime.now())
        for paridade in par['digital']:
            if par['digital'][paridade]['open'] == True:
                payout =payout_digital(paridade, 'digital')

                li_dig[paridade]= payout
                # if payout==0:
                #     payout_zero = True
        
        
        payout_bin()
        
        # LISTA_DIGITAL.clear()
        LISTA_DIGITAL = li_dig   

        data = func.converte_data_timezone(datetime.now())
        HORA_LISTA_PAYOUT = data.strftime('%Y-%m-%d %H:%M')
        # hora_fin = datetime.now()
        # dif = hora_fin - hora_ini
        # print('Tempo rotina Lista_pares_ativos: ' +str(dif))
        for i in LISTA_DIGITAL:
            if LISTA_DIGITAL[i]==0:
                API_LISTA_AT.connect()
                break
        # API_LISTA_AT.connect()
        # print(LISTA_DIGITAL)

        # if 
        
        # API.connect()
        # if payout_zero:
        #     sys.exit()

    except Exception as e:
        print('Falha api.py lista_pares_ativos : '+str(e))

    
			
	# LISTA_ATIVOS_ONLINE['turbo']= LISTA_TURBO
	# LISTA_ATIVOS_ONLINE['digital'] = LISTA_DIGITAL

    
def get_tipo_conta():
    try:
        modo= API.get_balance_mode()
        return modo
    except:
        return False


########################################
#  INICIO DAS THREADS                  #
########################################

def td_compra_op_binaria(ativo,lote,timeframe,direcao,id_tb_entrada,martingale_ativo, ciclo_marting,id_martin,id_ini_martingale):
    t1 = threading.Thread(target= compra_op_binaria,name='td_compra_op_binaria', args=(ativo,lote,timeframe,direcao,id_tb_entrada,martingale_ativo, ciclo_marting,id_martin,id_ini_martingale))
    t1.start()

def td_compra_op_digital(ativo,lote,timeframe,direcao,id_tb_entrada,martingale_ativo, ciclo_marting,id_martin,id_ini_martingale):
    t1 = threading.Thread(target= compra_op_digital,name='td_compra_op_digital',args=(ativo,lote,timeframe,direcao,id_tb_entrada,martingale_ativo, ciclo_marting,id_martin,id_ini_martingale))
    t1.start()

def td_resultado_ordem_digital(id_ordem,valor_entrada,id_tb_entrada,martingale_ativo, ciclo_marting):
    t1 = threading.Thread(target= resultado_ordem_digital,name='td_resultado_ordem_digital',args=(id_ordem,valor_entrada,id_tb_entrada,martingale_ativo, ciclo_marting))
    t1.start()

def td_resultado_ordem_binaria(id_ordem,id_tb_entrada,martingale_ativo, ciclo_marting):
    t1 = threading.Thread(target= resultado_ordem_binaria,name='td_resultado_ordem_binaria', args=(id_ordem,id_tb_entrada,martingale_ativo, ciclo_marting))
    t1.start()
# def td_saldo_do_dia():
#     t1 = threading.Thread(target=saldo_do_dia)
#     t1.start()



        
