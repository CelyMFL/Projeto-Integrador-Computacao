"""Rotas de autenticação (login e logout).

Este módulo gerencia exclusivamente o fluxo de autenticação e os redirecionamentos 
baseados no perfil (role) do usuário (Admin ou Professor).
"""

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user
from app.models.user import User, RoleEnum
from werkzeug.security import check_password_hash

auth = Blueprint('auth', __name__)



## Login route
@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Autentica o usuário e redireciona para a página correspondente ao seu perfil.
    
    Verifica se o método é POST, valida as credenciais de email e senha 
    e, em caso de sucesso, direciona o Admin para a landing page de admin 
    e o Professor para a tela normal (dashboard).
    """
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        # Busca o usuário pelo email
        user = User.query.filter_by(email=email).first()

        # Verifica se o usuário existe e se a senha está correta
        if user and check_password_hash(user.senha, senha):
            login_user(user)

            # Redirecionamento condicional com base no perfil (Role)
            if user.role == RoleEnum.ADMIN:
                # Direciona para a landing page de admin
                return redirect(url_for('admin.home'))
            else:
                # Direciona para a tela normal de professor
                return redirect(url_for('professor.dashboard'))

    # Se for requisição GET ou houver falha, renderiza o formulário de login
    return render_template('auth/login.html')




## Logout route
@auth.route('/logout')
def logout():
    """Encerra a sessão atual (logoff) e retorna para a página de login."""
    # Limpa os dados da sessão do usuário
    logout_user()
    # Redireciona à página de login conforme o requisito
    return redirect(url_for('auth.login'))