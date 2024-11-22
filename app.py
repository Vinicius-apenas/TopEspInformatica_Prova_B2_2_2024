# from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import *
from peewee import *
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "segredo123"  # Chave para sessões (troque por algo mais seguro)

# Banco de dados
db = SqliteDatabase('projeto.db')

# Modelos
class BaseModel(Model):
    class Meta:
        database = db

class Usuario(BaseModel):
    nome = CharField(max_length=100)
    email = CharField(max_length=100, unique=True)
    senha = CharField(max_length=100)

class Grupo(BaseModel):
    nome = CharField()
    descricao = TextField(null=True)
    criador = ForeignKeyField(Usuario, backref='grupos_criados', on_delete='CASCADE')

class GrupoUsuario(BaseModel):
    grupo = ForeignKeyField(Grupo, backref='usuarios', on_delete='CASCADE')
    usuario = ForeignKeyField(Usuario, backref='grupos', on_delete='CASCADE')


class Tarefa(BaseModel):
    titulo = CharField(max_length=200)
    descricao = TextField(null=True)
    concluida = BooleanField(default=False)
    usuario = ForeignKeyField(Usuario, backref='tarefas', on_delete='CASCADE')
    grupo = ForeignKeyField(Grupo, backref='tarefas', null=True, on_delete='SET NULL')
    criador = ForeignKeyField(Usuario, backref='tarefas_criadas', on_delete='CASCADE')

# Inicialização do banco
def criar_tabelas():
    with db:
        db.create_tables([Usuario, Grupo, Tarefa,GrupoUsuario])

criar_tabelas()

# Rotas

# Tela de Login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.get_or_none(Usuario.email == email)
        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            return redirect(url_for('dashboard'))
        else:
            flash("Credenciais inválidas!")
    return render_template('login.html')

# Cadastrar Novo Usuário
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        try:
            Usuario.create(
                nome=nome,
                email=email,
                senha=generate_password_hash(senha)
            )
            flash("Usuário cadastrado com sucesso!")
            return redirect(url_for('login'))
        except IntegrityError:
            flash("Erro: Email já cadastrado.")
    return render_template('cadastrar.html')

# Trocar Senha
@app.route('/trocar_senha', methods=['GET', 'POST'])
def trocar_senha():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        senha_atual = request.form['senha_atual']
        nova_senha = request.form['nova_senha']
        usuario = Usuario.get_by_id(session['usuario_id'])
        if check_password_hash(usuario.senha, senha_atual):
            usuario.senha = generate_password_hash(nova_senha)
            usuario.save()
            flash("Senha alterada com sucesso!")
        else:
            flash("Senha atual incorreta.")
    return render_template('trocar_senha.html')

# Dashboard do Usuário
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', nome=session['usuario_nome'])

# Criar Grupo
@app.route('/criar_grupo', methods=['GET', 'POST'])
def criar_grupo():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        
        # Obter o usuário logado
        criador = Usuario.get_or_none(Usuario.id == session['usuario_id'])
        if not criador:
            flash("Usuário não encontrado.")
            return redirect(url_for('login'))
        
        # Criar o grupo
        grupo = Grupo.create(nome=nome, descricao=descricao, criador=criador)
        
        # Associar o criador ao grupo
        GrupoUsuario.create(grupo=grupo, usuario=criador)
        
        flash("Grupo criado com sucesso!")
        return redirect(url_for('ver_grupos'))
    
    return render_template('criar_grupo.html')

#ver grupo
@app.route('/ver_grupos')
def ver_grupos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.get_or_none(Usuario.id == session['usuario_id'])
    if not usuario:
        flash("Usuário não encontrado.")
        return redirect(url_for('login'))
    
    # Obter os grupos associados ao usuário
    grupos = [gu.grupo for gu in GrupoUsuario.select().where(GrupoUsuario.usuario == usuario)]
    
    return render_template('ver_grupos.html', grupos=grupos)

#ver tarefas de grupo
@app.route('/ver_tarefas_grupo/<int:grupo_id>')
def ver_tarefas_grupo(grupo_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Obter o grupo
    grupo = Grupo.get_or_none(Grupo.id == grupo_id)
    if not grupo:
        flash("Grupo não encontrado.")
        return redirect(url_for('ver_grupos'))
    
    # Verificar se o usuário faz parte do grupo
    usuario = Usuario.get_or_none(Usuario.id == session['usuario_id'])
    if not GrupoUsuario.get_or_none(grupo=grupo, usuario=usuario):
        flash("Você não tem permissão para acessar este grupo.")
        return redirect(url_for('ver_grupos'))
    
    # Buscar tarefas do grupo com os relacionamentos carregados
    tarefas = Tarefa.select(Tarefa, Usuario).where(Tarefa.grupo == grupo).join(Usuario, on=(Tarefa.criador == Usuario.id))
    
    return render_template('ver_tarefas_grupo.html', grupo=grupo, tarefas=tarefas)

# Editar grupo
@app.route('/editar_grupo/<int:grupo_id>', methods=['GET', 'POST'])
def editar_grupo(grupo_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    grupo = Grupo.get_or_none(Grupo.id == grupo_id)
    if not grupo:
        flash("Grupo não encontrado.")
        return redirect(url_for('ver_grupos'))
    
    if grupo.criador.id != session['usuario_id']:
        flash("Você não tem permissão para editar este grupo.")
        return redirect(url_for('ver_grupos'))
    
    if request.method == 'POST':
        grupo.nome = request.form['nome']
        grupo.descricao = request.form['descricao']
        grupo.save()
        
        # Adicionar usuários ao grupo pelo e-mail
        emails = request.form.get('emails', '').split(',')
        for email in emails:
            email = email.strip()
            if email:
                usuario = Usuario.get_or_none(Usuario.email == email)
                if usuario:
                    GrupoUsuario.get_or_create(grupo=grupo, usuario=usuario)
                else:
                    flash(f"Usuário com o e-mail {email} não encontrado.")
        
        flash("Grupo atualizado com sucesso!")
        return redirect(url_for('ver_grupos'))
    
    # Obter os e-mails dos usuários no grupo
    usuarios_no_grupo = [gu.usuario.email for gu in grupo.usuarios]
    return render_template('editar_grupo.html', grupo=grupo, usuarios_no_grupo=usuarios_no_grupo)



#apagar grupo
@app.route('/excluir_grupo/<int:grupo_id>', methods=['POST'])
def excluir_grupo(grupo_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    grupo = Grupo.get_or_none(Grupo.id == grupo_id)
    if not grupo:
        flash("Grupo não encontrado.")
        return redirect(url_for('ver_grupos'))
    
    if grupo.criador.id != session['usuario_id']:  # Verificar se o usuário é o criador do grupo
        flash("Você não tem permissão para excluir este grupo.")
        return redirect(url_for('ver_grupos'))
    
    grupo.delete_instance()  # Excluir o grupo
    flash("Grupo excluído com sucesso!")
    return redirect(url_for('ver_grupos'))

# Criar Tarefa
@app.route('/criar_tarefa', methods=['GET', 'POST'])
def criar_tarefa():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuario_id = session['usuario_id']
    grupos = Grupo.select().where(Grupo.criador == usuario_id)
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        grupo_id = request.form['grupo'] if request.form['grupo'] else None
        prazo = request.form['prazo'] if request.form['prazo'] else None
        criador= usuario_id
        
        Tarefa.create(
            titulo=titulo,
            descricao=descricao,
            usuario=usuario_id,
            grupo=grupo_id,
            prazo=prazo,
            criador=criador
        )
        flash("Tarefa criada com sucesso!")
        return redirect(url_for('ver_tarefas'))
    
    return render_template('criar_tarefa.html', grupos=grupos)


@app.route('/sobre')
def sobre():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('sobre.html')

#ver tarefas
@app.route('/tarefas')
def ver_tarefas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuario_id = session['usuario_id']
    tarefas = Tarefa.select().where(Tarefa.usuario == usuario_id)
    return render_template('ver_tarefas.html', tarefas=tarefas)


#excluir tarefa
@app.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
def excluir_tarefa(tarefa_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    tarefa = Tarefa.get_or_none(Tarefa.id == tarefa_id)
    if not tarefa or tarefa.usuario.id != session['usuario_id']:
        flash("Acesso negado!")
        return redirect(url_for('ver_tarefas'))
    
    tarefa.delete_instance()
    flash("Tarefa excluída com sucesso!")
    return redirect(url_for('ver_tarefas'))

#editar tarefa
@app.route('/editar_tarefa/<int:tarefa_id>', methods=['GET', 'POST'])
def editar_tarefa(tarefa_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    tarefa = Tarefa.get_or_none(Tarefa.id == tarefa_id)
    if not tarefa or tarefa.usuario.id != session['usuario_id']:
        flash("Acesso negado!")
        return redirect(url_for('ver_tarefas'))
    
    grupos = Grupo.select().where(Grupo.criador == session['usuario_id'])
    
    if request.method == 'POST':
        tarefa.titulo = request.form['titulo']
        tarefa.descricao = request.form['descricao']
        grupo_id = request.form['grupo']
        tarefa.grupo = Grupo.get_by_id(grupo_id) if grupo_id else None
        tarefa.prazo = request.form['prazo'] if request.form['prazo'] else None
        tarefa.save()
        
        flash("Tarefa atualizada com sucesso!")
        return redirect(url_for('ver_tarefas'))
    
    return render_template('editar_tarefa.html', tarefa=tarefa, grupos=grupos)


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)