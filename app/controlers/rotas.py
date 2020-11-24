from app import application as app, db
from flask import render_template,url_for, redirect, request, flash
from app.models import tabelas
from datetime import date, datetime, timedelta
import json, threading,time
#REGISTRO DE SESSÕ
from flask_login import login_required, login_user, logout_user, LoginManager, logout_user

from app.api_iq import api_iq as api
from app.api_iq import chamar_api as chamar

#IMPORTANDO AS FUNÇÕES ÚTEISP
from app.controlers import funcoes_uteis as func

#ESSES IMPORTES FORAM USADOS PARA IMPORTAR ARQUIVO
from werkzeug.utils import secure_filename
import os, requests

login_manager= LoginManager(app)

#RETORN O USUÁRIO CORRENTE
@login_manager.user_loader
def current_user(user_id):
    return tabelas.Usuario.query.get(user_id)


@app.route("/")
def rota():
    return redirect("/login")

@app.route('/termo_uso/')
def termo_uso():
    return render_template("termo_uso.html")


@app.route("/login", methods=['GET','POST'])
def login():

    if request.method == 'POST':
        email=request.form['email']
        senha =request.form['senha']

        #CONTROLE DE LINCEÇA
        licenca = consultar_email_licenca(email)
        # print('licenca:'+ str(licenca))
        print('licenca: ' + str(licenca))
        resultado,vencimento = licenca
        if resultado == 0:
            #SE O RESULTADO FOR ZERO SEGNIFICA QUE A LICENÇA ESTÁ VENCIDA
            flash('A sua licença venceu, entre em contado com a nossa equipe para reativar sua licença!')
            return redirect(url_for('login'))
        
        if resultado == -1:
            #SE O EMAIL NÃO FOR CADASTRADO
            flash('A licença do robô não está liberada para este email!')
            return redirect(url_for('login'))

        conectado = api.get_status_conexao()
        LOGADO = False
        if not conectado:
            LOGADO = api.conectar(email,senha)
            if LOGADO:
                func.acesso(email,senha)
        else:
            LOGADO = func.acesso(email,senha)
        
        if LOGADO:
            #FUNÇÃO QUE CRIA O PRIMEIRO E TAMBÉM MODIFICA OS ATRIBUTOS NOS ACESSOS SEGUINTES
            
            user = tabelas.Usuario.query.filter_by(email = request.form['email']).first()
            # print(tabelas.Usuario.get_id(user))
            login_user(user,remember=True, duration= timedelta(days=180))
            api.ATIVO=True
            #FAZ O PREENCHIMENTO DA LISTA DA ATIVOS ONLINE
            # api.lista_pares_ativos()
            # api.get_info_conta()
            # chamar.info_conta()
            ger = tabelas.Gerencia.query.get(1)
            chamar.PAYOUT_MIN = ger.pay_out_min
            chamar.STOPGAIN = ger.stop_gain
            chamar.STOPLOSS = ger.stop_loss

            # chamar.listar_ativos_online()
            # chamar.inicia_bot()
            if not conectado:
                # chamar.thread_info_conta()
                chamar.thread_ativos_online()

            chamar.thread_ini_bot()
            
            return redirect(url_for('bot_iq'))

        else:
            flash('Credenciais Incorretas! Tente novamente!')
            return redirect(request.url)
    
    else:

        #VERIFICA SE JÁ EXISTE USUÁRIO NA TABELA        
        user = tabelas.Usuario.query.get(1)      
        if  user:
            #verifica se o usuário já está conectado
            if user.conectado:
                #HABILITA A SESSÃO DO USUÁRIO
                login_user(user)
                return redirect(url_for('bot_iq'))
            #caso não esteja conectado abre a tela de login mostrando o email no campo correspondente    
            else:
                return render_template("Login.html", user = user)
        #caso não exita usuário na tabela abre a tela de login com os campos vazios
        else:            
            return render_template("Login.html")

 
@app.route('/logout')
@login_required
def logout():
    try:
        user = tabelas.Usuario.query.get(1)
        user.conectado = False
        db.session.commit()
        func.deletar_lista()
        # print(api.API.check_connect())
        api.ATIVO = False
        # api.desconectar()
        # api.restart_program()
        # print(api.API.check_connect())
        logout_user()
       
        
    finally:
        user = tabelas.Usuario.query.get(1)
        user.conectado = False
        api.ATIVO = False
        db.session.commit()
        logout_user()

    
    return redirect(url_for('login'))

@app.route("/bot_iq")
# @login_required
def bot_iq():
    
    user = tabelas.Usuario.query.get(1)

    #CONTROLE DE LINCEÇA
    licenca = consultar_email_licenca(user.email)
    
    resultado,vencimento = licenca

    if resultado == 0:
        #SE O RESULTADO FOR ZERO SEGNIFICA QUE A LICENÇA ESTÁ VENCIDA
        flash('A sua licença venceu, entre em contado com a nossa equipe para reativar sua licença!')
        return redirect(url_for('logout'))

    if resultado == -1:
        #SE O EMAIL NÃO FOR CADASTRADO
        flash('A licença do robô não está liberada para este email!')
        return redirect(url_for('logout'))
    if resultado == 1:        
        #SE A LICENÇA FOR VÁLIDA
        diferenca = (vencimento -datetime.now()).days
        palavra_dias = ' dia!' if diferenca==1 else ' dias!'
        
        if diferenca>= 0 and diferenca<=5:
            flash('Sua Licença Expira em : '+ str(diferenca) +palavra_dias)
    

    if user:
        if user.conectado == False:
            return redirect(url_for('login'))
        else:
            # if login_user()
            login_user(user,remember=True, duration= timedelta(days=180))
            # print(login_user(user))

    else:
        return redirect(url_for('login'))
    
    #FUNCAO QUE FORMATA OS VALORES FLOAT PARA EXIBIR NOS CAMPOS COM MASCARA

    def float_to_string(valor):

        valor_string = str(valor)        
        if valor_string[-3]=='.':
            return valor_string
        else:
            return  valor_string+'0'

    gerencia = tabelas.Gerencia.query.get(1)
    
    gerencia.stop_loss=float_to_string(gerencia.stop_loss)
    gerencia.stop_gain = float_to_string(gerencia.stop_gain)
    gerencia.lote = float_to_string(gerencia.lote)
    gerencia.martingale_retorno = float_to_string(gerencia.martingale_retorno)
    
    # print(api.LISTA_INFO_CONTA)
    balanco= None
    saldo_dia= None
    conectado = None
    # api.get_info_conta()

    # conta = 'demo' if gerencia.tipo_conta=='DEMO' else 'real'
    
    # for i in range(8):
    #     if str(conta).lower() in api.LISTA_INFO_CONTA:
    #         break
        
    #     time.sleep(1)       
    

    try:
        # api.API.check_connect()               
        balanco=api.get_balanco()
        saldo_dia=chamar.get_saldo_dia()
        conectado=api.get_status_conexao()
        # chamar.SALDO_DIA = saldo_dia        
    except :
        balanco= 0
        saldo_dia= 0
        conectado = False
        # chamar.SALDO_DIA = saldo_dia

   
    
        
    #entradas =tabelas.Entrada.query.order_by(tabelas.Entrada.hora(tabelas.Entrada.query.filter(tabelas.Entrada.data=='2020-08-21').all())).all()
    # data_atual = datetime.strptime(str(datetime.fromtimestamp(api.API.get_server_timestamp())),'%Y-%m-%d')
    data_atual = func.converte_data_timezone(datetime.now())
    entradas = tabelas.Entrada.query.filter(tabelas.Entrada.data>=data_atual.strftime('%Y-%m-%d')).all()                
    return render_template("bot_iq.html", ger = gerencia, entradas = entradas, balanco = balanco, saldo_dia = saldo_dia, conectado = conectado)


@app.route('/desativar_ordem/<int:id>')
@login_required
def desativar_ordem(id):
    
    entrada = tabelas.Entrada.query.get(id)   
         
    #VERIFICA SE A ORDEM JÁ FOI ENVIADA OU SE É UMA ORDEM EXPIRADA
    if entrada.enviada == True or entrada.expirado==True:
        flash('O Status desta Ordem não pode mais ser alterado!')
        return redirect(url_for('bot_iq'))
    #verifica se o booleano executar está ativo

    if entrada.executar:
        entrada.observacoes='Ignorado pelo usuário'
        entrada.executar = False
        print('aqui')
    else:
        hora = entrada.hora
        data_atual = func.converte_data_timezone(datetime.now())
        data = entrada.data
        hora_entrada = data_atual.replace(year=int(data[:4]),month=int(data[5:7]),day=int(data[8:]), hour=int(hora[:2]), minute=int(hora[3:]),second=0)
        hora_atual = func.converte_data_timezone(datetime.now()) - timedelta(seconds=30)
        print('hora atual: ' + str(hora_atual))
        print('hora entrada: ' + str(hora_entrada))
        #VERIFICA SE O HORÁRIO JÁ ESTÁ EXPIRADO
        if hora_entrada < hora_atual:
            entrada.observacoes='Horário Já Expirado!'
            entrada.executar= False
            entrada.expirado = True
        else:
            entrada.observacoes = ''
            entrada.executar = True
    
    db.session.commit()
   
    return redirect(url_for('bot_iq'))
    
#

@app.route("/upload/", methods=['GET','POST'])
@login_required
def upload():

    PASTA_UPLOAD = os.path.join(os.getcwd(),'app/upload')
    EXTENCOES_PERMITIDAS= ('txt')

    #FUÇÃO PARA VERIFICAR SE O É DO TIPO TXT
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENCOES_PERMITIDAS

    if request.method == 'POST':        
        arquivo = request.files['arquivo']
        #nome_arquivo= arquivo.filename
        print(allowed_file(arquivo.filename))
        if allowed_file(arquivo.filename):
            arquivo.filename = 'lista_entradas.txt'
            salvar_Em = os.path.join(PASTA_UPLOAD,secure_filename(arquivo.filename))        
            arquivo.save(salvar_Em)
            usar_lista_em = 0 if request.form['usolista']=='NA DATA ATUAL' else 1
            if not func.importar_lista(usar_lista_em):

                flash("A lista que você está tentando importar é inválida. Favor fornecer uma lista válida, conforme o Exemplo: 00:40;GBP/JPY;CALL;5 ")
                return redirect(url_for('bot_iq'))

            
            
        else:
            flash(' Erro na importação do Arquivo,a extensão é inválida. Selecione um arquivo com extensão .txt ')
            return redirect(url_for('bot_iq'))
        
        chamar.desat_ordens_horario_expirado()
    return redirect(url_for('bot_iq'))
            

@app.route('/editar_gerencia/', methods=['GET','POST'])
@login_required
def editar_gerencia():

    gerencia = tabelas.Gerencia.query.get(1)

    #SUBSTITUINDO A VIRGULA E REMOMENDO OS PONTOS DOS CAMPOS COM MASCARA
    def format_float(valor):
        novo = str(valor)
        #REMOVENDO OS PONTOS
        novo = novo.replace('.','')
        #SUBSTITUINDO A VIRGULA POR PONTO
        novo = novo.replace(',','.')
        novo = float(novo)

        return(novo) 
    
    if request.method=='POST':    
        gerencia.tipo_conta =request.form['inputTipoConta']
        gerencia.pay_out_min =request.form['payoutmin']
        gerencia.stop_loss = format_float(request.form['stoploss'])
        gerencia.stop_gain = format_float(request.form['stopgain'])
        gerencia.delay =request.form['delay']
        gerencia.lote = format_float( request.form['lote'])
        gerencia.martingale_retorno = format_float(request.form['inpMartingRetorno'])
        gerencia.martingale_tipo = 1 if  request.form['inputTipoMarting']=='PADRÃO' else 2


        #ESSE REQUEST FORM DE MANEIRA DIFERENTE, É PARA EVITAR PROBLEMAS E ERROS
        # NO RECEBIMENTO DOS REQUESTS VINDOS DE UM CHEK BOX
        check_filtro_tred=request.form.get("checkFiltroTend", False)

        check_blok_ord_todas = request.form.get("blocktodasordens", False)
        
        check_blok_ord_mesmo_par = request.form.get("blockOdMesmoPar", False)
        
        check_vela_cor_oposta = request.form.get("VelaCorOposta", False)
                
        gerencia.fil_entrada_sma=True if  check_filtro_tred != False else False
      
        gerencia.periodo_sma =request.form['SMA']
        gerencia.block_ord_todas = True if  check_blok_ord_todas!= False else False
        
        gerencia.block_ord_mesmo_par = True if  check_blok_ord_mesmo_par!= False else False
        gerencia.vela_cor_oposta = True if  check_vela_cor_oposta!= False else False
        
        db.session.commit()
        #ATBUIBUI VALORES AS VARIÁVEIS GLOBAIS DO MÓDULO CHAMAR_API
        chamar.PAYOUT_MIN = gerencia.pay_out_min
        chamar.STOPGAIN = gerencia.stop_gain
        chamar.STOPLOSS = gerencia.stop_loss

        #MUDA O TIPO DE CONTA DA API
        ger = tabelas.Gerencia.query.get(1)
        if ger.tipo_conta == 'DEMO':
            api.set_tipo_conta('PRACTICE')
        else:
            api.set_tipo_conta('REAL')
    
    return redirect("/bot_iq")

@app.route("/add_entra_manual/", methods=['GET','POST'])
@login_required
def add_entrada_manual():

    if request.method == 'POST':
        hora = request.form['hora']
        #validando a hora
        if not func.string_to_datetime(hora):
            flash('O horário informado é inválido, favor informar um horário válido!')
            return redirect('/bot_iq')

        entrada = tabelas.Entrada()
        ger = tabelas.Gerencia.query.get(1)
        ativo = request.form['ativo']
        entrada.hora = hora
        data_atual = func.converte_data_timezone(datetime.now())
        entrada.data = data_atual.strftime('%Y-%m-%d')
        entrada.ativo = ativo if request.form['tipoativo']=='NORMAL' else ativo+'-OTC'
        entrada.duracao = request.form['duracao']
        entrada.tipo_ordem = request.form['tipoentrada']
        entrada.observacoes=''
        entrada.executar = True
        entrada.enviada = False
        entrada.expirado = False
        entrada.id_ini_martingale = 0
        # entrada.block_todas = False
        # entrada.block_mesmo_par = False
        entrada.ciclo = 0
        entrada.martingale_ativo = False
        entrada.lote = 0
        entrada.id_user = 1
        entrada.resultado_op = 0
        entrada.tipo_conta = ''
        db.session.add(entrada)
        db.session.commit()
        chamar.desat_ordens_horario_expirado()  
    

    return redirect('/bot_iq')

@app.route('/lista_at')
def lista_ativos_online():
    listabin = api.LISTA_BINARIA
    listadig = api.LISTA_DIGITAL
    hora = api.HORA_LISTA_PAYOUT
    td_ativas = threading.enumerate()
    return render_template('info_conta.html',lbin = listabin,ldig = listadig, td = td_ativas, hora = hora)

def consultar_email_licenca(email):
    try:
        # print('aqui')
        resp = requests.get('http://appcontolelicenca-env.eba-mtpri2sp.us-east-2.elasticbeanstalk.com/consultar_email?email='+str(email).lower().strip(), timeout=3)
        
        # print('resp:' + str(resp))
        resultado = resp.json()['resultado']
        vencimento = resp.json()['vencto']
        # print('resultado: ' + str(resultado))
        
        if vencimento!=0:
            vencto_format = datetime.strptime(str(vencimento),'%Y-%m-%d %H:%M:%S')

            return resultado,vencto_format
        else:
            return resultado, vencimento

    except Exception as e:
        print('Erro : '+ str(e))
        return -2,0
        

       
        
      

    

    








