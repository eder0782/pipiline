from app.api_iq import api_iq as api
import time, sqlite3
from datetime import datetime,date,timedelta

from app.models import tabelas
from app import db
import threading
import sys, pytz
from app.controlers import funcoes_uteis as func

################################
# VARIÁVEIS GLOBAIS            #
################################

PAYOUT_MIN = None
STOPLOSS = None
STOPGAIN = None
SALDO_DIA =0

VENCIMENTO_LICENCA = None

#VARIÁVEL QUE VERIFICA SE A ROTINA QUE LISTA OS PARES ATIVOS ESTÁ EM USO
LISTA_PARES_RODANDO = False

# @api.threaded
def inicia_bot():
    
    while True:
        # print('Total trheads Ativas: ' + str(threading.active_count()))
        #CASO A VARIÁVEL API NÃO ESTEJA ATIVA EXCERRA O LAÇO
        # print('ativo')
        global LISTA_PARES_RODANDO
        try:
            

            if not api.ATIVO:
                # t = threading.currentThread()
                
                break
            #VERIFICA SE A ROTINA QUE LISTA OS PARES ATIVOS ESTÁ RODANDO
            if not LISTA_PARES_RODANDO:
                thread_ativos_online()
            # print('rodando')
            # desat_ordens_horario_expirado()
        
            lista_ordens = ordens_para_exetucar()
            if lista_ordens:
                # print('recebendo lista')

                for li in lista_ordens:
                    id_tab_entrada,hora,ativo,duracao,tipo_ordem = li
                    #JÁ ALTERA O CAMPO ENVIADA PARA TRUE EVITANDO QUE SEJAM ENVIADAS ORDENS EM DUPLICIDADE
                    entrada = tabelas.Entrada.query.get(int(id_tab_entrada))
                    ger = tabelas.Gerencia.query.get(1)
                    entrada.enviada = True
                    entrada.tipo_conta = ger.tipo_conta
                    # entrada.executar = False
                    if stops()==1:
                        entrada.observacoes= 'Ignorado....Stop Gain Já Alcançado!'
                        entrada.executar = False
                        db.session.commit()
                        continue
                    elif stops()==-1:
                        entrada.executar = False
                        entrada.observacoes= 'Ignorado....Stop Loss Já Alcançado!'
                        
                        db.session.commit()
                        continue
                    db.session.commit()
                    
                    
                    #SE A ORDEM FOI BLOQUEADA POR CONTA DE TER OUTRAS NO MESMO HORÁRIO       
                    retorno,mensagem =set_bloquear_ordens_juntas(id_tab_entrada,ativo,hora)
                    # print(retorno)
                    if retorno :                        
                        entrada2 = tabelas.Entrada.query.get(int(id_tab_entrada))
                        entrada2.executar = False                        
                        entrada2.observacoes= mensagem
                        db.session.commit()
                        continue
                    
                    
                        #REMOVEMENDO A / DO NOME DO ATIVO
                    ativo =str(ativo).replace('/','')
                    lote = get_tabela_gerencia('lote')
                    duracao =str(duracao).replace('M','')
                    #VERIFICA SE O TIMEFRAM É EM HORA
                    if 'H' in duracao:
                        duracao= duracao.replace('H','')
                        duracao= int(duracao)*60
                    
                    ger = tabelas.Gerencia.query.get(1)
                    #VERIFICA SE O CAMPO DE VELA_COR_OPOSTA ESTÁ MARCADO
                    if ger.vela_cor_oposta:
                        if  get_candle_anterior_is_oposto(ativo,int(duracao),tipo_ordem):
                                entrada2 = tabelas.Entrada.query.get(int(id_tab_entrada))
                                entrada2.executar = False
                                entrada2.observacoes= 'Ignorado...Vela anterior é de cor oposta à ordem!'
                                db.session.commit()
                                continue
                    #VERIFICAR A TENDENCIA DA MEDIA MÓVEL SE O FILTRO ESTIVER MARCADO NA TABELA DE GERENCIA
                    if ger.fil_entrada_sma:
                        periodo = ger.periodo_sma
                        tendencia_ma = get_tendencia_media_movel(ativo,int(duracao),periodo,tipo_ordem)
                        if tendencia_ma ==False:
                            entrada3 = tabelas.Entrada.query.get(int(id_tab_entrada))
                            entrada3.executar = False
                            entrada3.observacoes= 'Ignorado...Tendência Atual é diferente da ordem!'
                            db.session.commit()
                            continue

                    #ESTA PARTE FOI REMOVIDA, POIS O MARTINGALE AGORA SERÁ FEITO DE MANEIRA DIFERENTE    
                    #VERIFICA SE TEM ORDENS EM ABERTO PARA O HORÁRIO ATUAL
                    #CASO TENHA, AGUARDA ATÉ QUE A ORDEM SEJA CONCLUÍDA
                    # hora_entrada = func.converte_data_timezone(datetime.now()) + timedelta(seconds=15)
                    # hora_entrada = hora_entrada.replace(second=0,microsecond=0)
                    # for i in range(15):
                    #     if (hora_entrada not in api.ORDEM_BIN_ABERTA) and (hora_entrada  not in api.ORDEM_DIG_ABERTA):
                    #         break
                    #     print('tem ordem pendente')
                    #     time.sleep(0.5)


                    melho_payout, valor_payout= get_melhor_payout(ativo.upper(),int(duracao))
                    #VARIÁVEL QUE AVISA SE O MARTINGALE ESTÁ ATIVO
                    #ESTA INFORMAÇÃO É SOMENTE PARA SER GRAVADA NO CAMPO DE OBSERVAÇÕES E SER MOSTRADA AO USUÁRIO
                    # martingale_ativo = False
                    # id_martin, lote_martin,ciclo_martin ,id_ini_martingale = get_martingales_ativos()
                    # entrada =tabelas.Entrada.query.get(int(id_tab_entrada))
                    # print('id_martin: ' + str(id_martin))
                    # if id_martin !=0 and (melho_payout==1 or melho_payout==2):
                    #     id = id_martin if id_ini_martingale==0 else id_ini_martingale
                    #     lote_atual = get_lote_martingale(id,valor_payout)
                    #     martingale_ativo = True
                    #     #ESSE IF É USADO, PARA CASO DÊ ALGUM ERRO NO CALCULO DO LOTE MARTING
                    #     if lote_atual!=0:
                    #         print(lote_atual)
                    #         lote = lote_atual
                    #         entrada4 = tabelas.Entrada.query.get(int(id_martin))
                    #         entrada4.martingale_ativo = False                            
                    #         db.session.commit()
                    #     else:
                    #         id_martin=0
                    #         lote_martin=0
                    #         ciclo_martin =0
                    #         id_ini_martingale=0

                    # O MARTINGALE SERÁ SETADO SEMPRE COMO FALSE
                    #POIS AGORA ELE SERÁ REALIZADO DE POR OUTRA FUNÇÃO
                    #NÃO MAIS POR AQUI
                    #MODIFIQUEI APENAS AS VARIÁVEIS PARA EVITAR ERROS
                    martingale_ativo = False
                    id_martin=0
                    lote_martin=0
                    ciclo_martin =0
                    id_ini_martingale=0


                    #MODIFICA O VALOR DO LOTE NO RESPECTIVO CAMPO DA OPERAÇÃO ATUAL
                    
                    entrada.lote = lote
                    db.session.commit()

                    # VERIFICANDO SE O SALDO DA BANCA É SUFICIENTE PARA O LOTE ATUAL
                    balanco_atual,status_balanc_at = get_balanco_atual()
                    # print('balanco_atual: ' + str(balanco_atual))
                    # print('lote:' + str(lote))

                    if status_balanc_at ==True:
                        if balanco_atual< lote:
                            print('saldo atual insuficiente')
                            entrada3 = tabelas.Entrada.query.get(int(id_tab_entrada))
                            entrada3.executar = False
                            entrada3.observacoes= 'Ignorado...Saldo Atual é Insuficiente!'
                            db.session.commit()
                        #SE TIVER MARTINGALE ATIVO VOLTA A SER TRUE
                            if id_martin!=0:
                                entrada4 = tabelas.Entrada.query.get(int(id_martin))
                                entrada4.martingale_ativo = True                            
                                db.session.commit()
                        
                            continue                    
                    else:
                        entrada3 = tabelas.Entrada.query.get(int(id_tab_entrada))
                        entrada3.executar = False
                        entrada3.observacoes= 'Falha na conxeção com a IQ Option!'
                        db.session.commit()

                        #SE TIVER MARTINGALE ATIVO VOLTA A SER TRUE
                        if id_martin!=0:
                            entrada4 = tabelas.Entrada.query.get(int(id_martin))
                            entrada4.martingale_ativo = True                            
                            db.session.commit()

                        continue




                
                    # print(melho_payout)

                    mensagem = 'None'
                    if melho_payout == 1:
                        api.td_compra_op_digital(ativo.upper(),float(lote),int(duracao),str(tipo_ordem).lower(),int(id_tab_entrada),martingale_ativo,ciclo_martin,id_martin,id_ini_martingale)
                    elif melho_payout ==2:
                        api.td_compra_op_binaria(ativo.upper(),float(lote),int(duracao),str(tipo_ordem).lower(),int(id_tab_entrada),martingale_ativo,ciclo_martin,id_martin,id_ini_martingale)
                    elif melho_payout == 0:
                        mensagem ='Ignorado...Payout Atual é menor que o mínimo permitido!'
                        entrada = tabelas.Entrada.query.get(int(id_tab_entrada))
                        entrada.executar = False
                        entrada.observacoes = mensagem
                        db.session.commit()                        
                    elif melho_payout == -1:
                        mensagem ='Ignorado...Paridade/TimeFrame Inativo!'
                        entrada = tabelas.Entrada.query.get(int(id_tab_entrada))
                        entrada.executar = False
                        entrada.observacoes = mensagem
                        db.session.commit()
                    else:
                        pass
                    
                    # if mensagem != 'None':
                    #     entrada = tabelas.Entrada.query.get(int(id_tab_entrada))
                    #     entrada.observacoes = mensagem
                    #     db.session.commit()
                        
                

                    #(ativo,lote,timeframe,direcao,id_tb_entrada)

            time.sleep(1)
            
        except Exception as e:
            print('Falha no laço principal: ' + str(e))
            continue

        finally:
            pass

                
# @api.threaded
# def info_conta():
#     while True:
#         # if not api.ATIVO:
#         #     # t = threading.currentThread()
#         #     # t.join()
#         #     break
#         try:
#             api.get_info_conta()
#             # print(api.LISTA_INFO_CONTA)
#             time.sleep(1)
#         except Exception as e:
#             print('Falha ao atualizar info conta:' + str(e))
#             continue
#         finally:
#             pass
        

# @api.threaded
def listar_ativos_online():
    # while True:
        # if not api.ATIVO:
        #     # t = threading.currentThread()
        #     # t.join()
        #     break
    global LISTA_PARES_RODANDO
    try:
        LISTA_PARES_RODANDO = True
        api.lista_pares_ativos()

        time.sleep(60)
        LISTA_PARES_RODANDO = False
    except Exception  as e :
        print('falha ao listar ativos online: ' + str(e))

        time.sleep(15)
        LISTA_PARES_RODANDO = False
        # continue
    # finally:
    #     pass

  
def desat_ordens_horario_expirado():
    try:
        con = sqlite3.connect('app/banco.db',timeout=10)
        cur = con.cursor()
        data_atual = func.converte_data_timezone(datetime.now()) #datetime.fromtimestamp(api.API.get_server_timestamp())
        # print('data_atual: '+ str(data_atual))
        select = cur.execute("select id, hora, ativo, duracao, tipo_ordem from entrada where data=? "+
        "and executar=1 and enviada = 0 order by hora", (data_atual.strftime('%Y-%m-%d'),))
        li = select.fetchall()
        if li!=[(None,)]:
            for i in li:
                hora_entrada = data_atual.replace(hour=int(i[1][:2]), minute=int(i[1][3:]),second=0)
                # print('hora_entrada: ' + str(hora_entrada))
                hora_servidor = func.converte_data_timezone(datetime.now()) # datetime.fromtimestamp(api.API.get_server_timestamp())
                # print('hora_servidor: ' + str(hora_servidor))
                hora_referencia =hora_servidor-timedelta(seconds=30)
                # print('hora_referencia: ' + str(hora_referencia))            
            
                if hora_entrada< hora_referencia:
                    id = i[0]
                    cur.execute("UPDATE entrada set executar = 0, expirado = 1, observacoes = 'Horário já expirado!' where id = ? ",(id,))


            con.commit()

        con.close()
        
    except Exception as e:
        print('Falha chamar.py desat_ordens_horario_expirado: ' + str(e))
        con.close()
    finally:
        
        con.close()

               
def get_melhor_payout(ativo,timeframe):
    '''
    Se o melhor payoute for Digital, retorna 1 \n
    Se for Binario retorna 2 \n
    Se não estiver ativo, retorna -1 \n
    Se o payout for menor que o mínimo retorna 0\n
    Retorna também o valor o payout para usar no martingale
    
    '''
    try:

        global PAYOUT_MIN

        par_online_binary=api.LISTA_BINARIA
        par_online_digital = api.LISTA_DIGITAL
        payout_binary = api.LISTA_PAYOUT_BINARY

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
        
        if payout_ >= PAYOUT_MIN:
            return id_entrada, payout_
        else:
            return 0, payout_

    except Exception as e:
        print('Falha chamar.py get_melhor_payout: '+ str(e))
        return 0,0

     

def ordens_para_exetucar():
    try:
        con = sqlite3.connect('app/banco.db',timeout=10)
        lista_total=[]
        cur = con.cursor()
        data_atual = func.converte_data_timezone(datetime.now()) #datetime.fromtimestamp(api.API.get_server_timestamp())
        select = cur.execute("select id, hora, ativo, duracao, tipo_ordem from entrada where data= ?"+
        "and executar=1 and enviada = 0 order by hora, id", (data_atual.strftime('%Y-%m-%d'),))
        
        if select:
            for sel in select:
                
                hora_entrada = data_atual.replace(hour=int(sel[1][:2]), minute=int(sel[1][3:]), second=int(get_tabela_gerencia('delay')), microsecond=0) #+ timedelta(seconds=int(get_tabela_gerencia('delay')))
                #print(hora_entrada)
                hora_servidor = func.converte_data_timezone(datetime.now()) #datetime.fromtimestamp(api.API.get_server_timestamp())
                if hora_entrada<= hora_servidor:
                
                    lista_total.append(sel)   
        
            
        return lista_total
    except Exception as e:
        print('Falha chamar.py ordens_para_exetucar: '+ str(e))
        return lista_total
        
def get_tabela_gerencia(campo):
    gerencia = tabelas.Gerencia.query.get(1)
    if campo == 'delay':
        return gerencia.delay
    elif campo == 'lote':
        return gerencia.lote
    else:
        pass

def stops():
    '''
    Se atingir o StopLoss retorna -1\n
    Se atingir o StopGain retorna 1 \n
    Se não retorna 0
    '''    
    global STOPLOSS,STOPGAIN,SALDO_DIA    
    try:
        # if api.get_tipo_conta()=='PRACTICE':
        #     # balanco=api.LISTA_INFO_CONTA['demo']['banca']
        #     SALDO_DIA=api.LISTA_INFO_CONTA['demo']['saldo_dia']
        #     # conectado=api.LISTA_INFO_CONTA['demo']['conectado']
        #     # chamar.SALDO_DIA = saldo_dia
        # else:
        #     # balanco=api.LISTA_INFO_CONTA['real']['banca']
        #     SALDO_DIA=api.LISTA_INFO_CONTA['real']['saldo_dia']
        #     # conectado=api.LISTA_INFO_CONTA['real']['conectado'] 
        #     # chamar.SALDO_DIA = saldo_dia
        SALDO_DIA = get_saldo_dia()
    except Exception as e :
        # balanco= 0
        print('Falha chamar.py stops: '+ str(e))
        SALDO_DIA= 0
        # conectado = False
        # chamar.SALDO_DIA = saldo_dia
            
    # print(SALDO_DIA)

    if SALDO_DIA>= STOPGAIN:
        return 1
    elif SALDO_DIA <= STOPLOSS*-1:
        return -1
    else:
        return 0

def set_bloquear_ordens_juntas(id_tb_entrada, ativo, hora):
    '''
    Função que bloqueia as ordems que tenham sido colocadas no mesmo horário.\n
    Se a ordem for bloqueada retorna true, senão retorna false
    '''
    try:

        con = sqlite3.connect('app/banco.db',timeout=10)
        cur = con.cursor()
        data_atual = func.converte_data_timezone(datetime.now()) #datetime.fromtimestamp(api.API.get_server_timestamp())
        select = None
        mensagem = ''
        ger = tabelas.Gerencia.query.get(1)

        if ger.block_ord_todas:
            select = cur.execute("select id from entrada where data=? "+
            "and executar=1  and hora=? and id< ?  order by hora", 
            (data_atual.strftime('%Y-%m-%d'),hora,id_tb_entrada,))
            mensagem = 'Ignorado..Bloqueio de Ordens Juntas(todas)'

        elif not ger.block_ord_todas and ger.block_ord_mesmo_par:
            select = cur.execute("select id from entrada where data=? "+
            "and executar=1 and hora=? and ativo = ? and id<?  order by hora", 
            (data_atual.strftime('%Y-%m-%d'),hora,ativo, id_tb_entrada,))
            mensagem = 'Ignorado..Bloqueio de Ordens Juntas do Mesmo Par'

        li = select.fetchall()
        # print(li)

        if li:      

            entrada = tabelas.Entrada.query.get(id_tb_entrada)
            entrada.executar = False
            entrada.observacoes = mensagem
            db.session.commit()
            cur.execute("UPDATE entrada set executar = 0,  observacoes = ? where id = ? ",(mensagem,id_tb_entrada,))
            con.commit()
            con.close()
            return True,mensagem
        else:
            con.close()
            return False, mensagem
      
    except Exception as e:
        print('Falha chamar.py set_bloquear_ordens_juntas: ' + str(e))
        con.close()
        return False,mensagem
    finally:
        con.close()
    
def get_candle_anterior_is_oposto(par,timeframe,direcao):
    '''
    Verifica se o candle anterior está no sentido oposto da ordem. \n
    Retorna True se verdadeito e False se Falso.
    '''
    try:
        velas = api.API.get_candles(par,timeframe*60,2,time.time())
        direcao_candle= 0
        #MUDA O O VALOR DA VARIAVEL PARA 1 INDICANDO QUE É UM CANDLE DE ALTA
        if velas[0]['open']< velas[0]['close']:
            direcao_candle =1
        #MUDA O O VALOR DA VARIAVEL PARA -1 INDICANDO QUE É UM CANDLE BAIXA
        elif velas[0]['open']> velas[0]['close']:
            direcao_candle =-1

        if (direcao_candle==1 or direcao_candle == 0) and direcao.upper() == 'PUT':
            return True
        elif (direcao_candle==-1 or direcao_candle == 0) and direcao.upper() == 'CALL':
            return True
        elif direcao_candle == 1 and direcao.upper() == 'CALL':
            return False
        elif direcao_candle == -1 and direcao.upper() == 'PUT':
            return False      
     
    except Exception as e:
        print(' Falha Chamar.py get_candle_anterior_is_oposto: ' + str(e))
        return True

def get_tendencia_media_movel(par,timeframe, periodo, direcao):
    '''
    Retorna a tendência da Média Móvel.\n
    Caso a ordem esteja na mesma direção da tendência retorna True, senão retorna False
    '''
    try:       
        indicator = api.API.get_technical_indicators(par)
        #VERIFICA SE O CAMPO CODE NÃO ESTÁ NA VARIÁVEL INDICADOR, SINALZANDO QUE O PAR TEM INDICADOR TÉCNICO
        # POIS OS PARES OTC NÃO TEM INDICADOR TÉCNICO
        if 'cod'not in indicator:
            for ind in indicator:
                if ind['group'] == 'MOVING AVERAGES' and ind['candle_size']==int(timeframe)*60 and ind['name']== 'Simple Moving Average ('+str(periodo)+')':
                    tendencia= ind['action']
                    if tendencia == 'sell' and direcao.upper() =='PUT':
                        return True
                    elif tendencia == 'buy' and direcao.upper() =='CALL':
                        return True
                    else:
                        return False
        #CASO SEJA UM PAR OTC, RETORNA TRUE, POIS ESSE TIPO DE ATIVO NÃO TEM INDICADOR TÉCNICO 
        else:
            return True
                    
    except Exception as e:
        print('Falha chamar.py get_tendencia_media_movel: ' + str(e))
        return False

def get_martingales_ativos():
    '''
    Verifica se tem ordens com o campo martingale_ativo = True./n
    Caso tenha, retorna o id, lote, ciclo e id_ini_martingale  em forma de tupla.
    Caso contrário retorna 0,0,0
    '''
    try:
     
        con = sqlite3.connect('app/banco.db',timeout=10)
        cur = con.cursor()
        ger = tabelas.Gerencia.query.get(1)
        data_atual = func.converte_data_timezone(datetime.now()) #datetime.fromtimestamp(api.API.get_server_timestamp())
        select = cur.execute('select id,lote, ciclo,id_ini_martingale  from entrada where martingale_ativo = 1'+
                ' and data = ? and tipo_conta = ? ',(data_atual.strftime('%Y-%m-%d'),ger.tipo_conta,))
        li = select.fetchall()
        if li:
            return li[0][0],li[0][1], li[0][2], li[0][3]   
            
                
        else:
            return 0,0,0,0
        
        con.close()

    except Exception as e:
        print(' Falha chamar.py get_martingales_ativos: ' + str(e))


        return 0,0,0,0
    finally:
        con.close()
        

def get_saldo_dia():
    try:
        con = sqlite3.connect('app/banco.db',timeout=10)
        cur = con.cursor()
        data_atual = func.converte_data_timezone(datetime.now()) #datetime.fromtimestamp(api.API.get_server_timestamp())
        ger = tabelas.Gerencia.query.get(1)

        select = cur.execute('select sum(resultado_op) from entrada where enviada= 1'+
                ' and data = ? and tipo_conta = ?',(data_atual.strftime('%Y-%m-%d'),ger.tipo_conta,))
        # print(select)
        saldo_do_dia = select.fetchall()
        if saldo_do_dia:
            con.close()
            return round(saldo_do_dia[0][0],2)
        else:
            con.close()
            return 0
        
    except Exception as e:
        print('Falha chamar.py get_saldo_dia: ' + str(e))
        con.close()
        return 0
        # con.close()
    finally:
        con.close()

def get_lote_martingale(id_martin,payout):
    '''
    Retorna o lote no martingale. Caso ocorra algum erro, retorna 0
    '''
    try:
        con = sqlite3.connect('app/banco.db',timeout=10)
        ger = tabelas.Gerencia.query.get(1)
        cur = con.cursor()
        data_atual = func.converte_data_timezone(datetime.now()) #datetime.fromtimestamp(api.API.get_server_timestamp())
        select = cur.execute('select sum(resultado_op) from entrada where id = ? or id_ini_martingale = ?'+
                ' and data = ? and tipo_conta = ?',(id_martin,id_martin,data_atual.strftime('%Y-%m-%d'),ger.tipo_conta,))
        # print(select)
        perca_acumulada = select.fetchall()
        
        # print(perca_acumulada[0][0])
        
        if perca_acumulada:
            #O RESULTADO OBTIDO É NEGATIVO, POR ISSO MUTIPLICA POR -1
                   
            ger = tabelas.Gerencia.query.get(1)
            valor= 0
            lucro_esperado = ger.martingale_retorno
                
            #SE FOR O MARTINGALE DO TIPO PADRÃO
            if ger.martingale_tipo ==1: 
                valor = (perca_acumulada[0][0]*-1)/payout*100

            else:
                valor = (perca_acumulada[0][0]*-1 + lucro_esperado)/payout*100
            
            return round(valor,2)
        else:
            return 0
        con.close()

    except Exception as e:
        print(' Falha chamar.py get_lote_martingale: ' + str(e))

        return 0
    finally:
        con.close()
    
def get_balanco_atual():
    '''
    FUNÇÃO USADA PARA RETORNAR O SALDO DA CONTA,
    CASO OCORRA ERRO NA CONEXÃO, RETORNA ZERO E FALSO, CASO OCORRA NORMAL RETORNA O SALDO E TRUE. 
    ESTA FUNÇÃO FOI CRIADA PARA EVITAR ERROS QUANDO O SALDO DA CONTA É MENOR QUE O 
    VALOR DO LOTE.
    '''
    try:
        return api.API.get_balance(),True
    except :
        return 0,False
            




########################
#INICIO DAS THREADS
########################


def thread_ini_bot():
    t1 = threading.Thread(target=inicia_bot, name='td_ini_bot',daemon=False)
    t1.start()

# def thread_info_conta():
#     t1 = threading.Thread(target=info_conta)
#     t1.start()
def thread_ativos_online():
    t1 = threading.Thread(target=listar_ativos_online, name='td_ativos_online',daemon=False)
    t1.start()


    



    
    



