from flask import Flask, render_template, request, redirect, url_for, session, flash
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
    nome = CharField(max_length=100)
    descricao = TextField(null=True)

class Tarefa(BaseModel):
    titulo = CharField(max_length=200)
    descricao = TextField(null=True)
    concluida = BooleanField(default=False)
    usuario = ForeignKeyField(Usuario, backref='tarefas', on_delete='CASCADE')
    grupo = ForeignKeyField(Grupo, backref='tarefas', null=True, on_delete='SET NULL')

# Inicialização do banco
def criar_tabelas():
    with db:
        db.create_tables([Usuario, Grupo, Tarefa])

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
        Grupo.create(nome=nome, descricao=descricao)
        flash("Grupo criado com sucesso!")
    return render_template('criar_grupo.html')

# Criar Tarefa
@app.route('/criar_tarefa', methods=['GET', 'POST'])
def criar_tarefa():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        usuario = Usuario.get_by_id(session['usuario_id'])
        Tarefa.create(titulo=titulo, descricao=descricao, usuario=usuario)
        flash("Tarefa criada com sucesso!")
    return render_template('criar_tarefa.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)