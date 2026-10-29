"""Rotas do administrador para telas de gestão e dashboard."""

from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, render_template, jsonify, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.models.user import RoleEnum
from app.models.user import User
from app.models.checklist import Checklist, TipoEnum
from app.models.feedback import Feedback
from app.models.professor_trilha import ProfessorTrilha, StatusEnum
from app.models.professor_checklist import ProfessorChecklist
from app.models.task import Task
from app import db
from app.services.professor_trilha_service import ProfessorTrilhaService
from werkzeug.security import generate_password_hash

admin = Blueprint('admin', __name__)

STATUS_LABELS = {
    StatusEnum.NAO_INICIADO.value: 'Não iniciado',
    StatusEnum.EM_ANDAMENTO.value: 'Em andamento',
    StatusEnum.CONCLUIDO.value: 'Concluído',
}


@admin.context_processor
def inject_status_labels():
    return {'status_labels': STATUS_LABELS}


def _professor_or_404(user_id):
    professor = User.query.get(user_id)
    if not professor or professor.role != RoleEnum.PROFESSOR:
        abort(404)
    return professor


def _trilha_or_404(trilha_id):
    trilha = Checklist.query.get(trilha_id)
    if not trilha:
        abort(404)
    return trilha


def _parse_assignments(data, key):
    """Converte {'atribuicoes': [{<key>: id, 'status': ...}]} em {id: status}."""
    items = data.get('atribuicoes')
    if not isinstance(items, list):
        raise ValueError('atribuicoes deve ser uma lista')

    desired = {}
    for item in items:
        try:
            desired[int(item.get(key))] = item.get('status') or StatusEnum.NAO_INICIADO.value
        except (TypeError, ValueError, AttributeError):
            raise ValueError(f'{key} inválido')
    return desired


def _professor_trilha_rows(professor):
    """Todas as trilhas, indicando a atribuição (se houver) deste professor."""
    enrollments = {
        item.trilha_id: item
        for item in ProfessorTrilha.query.filter_by(professor_id=professor.id).all()
    }
    rows = []
    for trilha in Checklist.query.order_by(Checklist.nome).all():
        enrollment = enrollments.get(trilha.id)
        total = len(trilha.tasks)
        concluidas = (
            ProfessorTrilhaService.count_completed_tasks(professor.id, trilha.id) if enrollment else 0
        )
        rows.append({
            'id': trilha.id,
            'nome': trilha.nome,
            'tipo': trilha.tipo.value if trilha.tipo else None,
            'obrigatoria': trilha.obrigatoria,
            'total_tarefas': total,
            'atribuida': enrollment is not None,
            'status': enrollment.status.value if enrollment else None,
            'concluidas': concluidas,
            'percentual': int(concluidas / total * 100) if total else 0,
        })
    return rows


def _trilha_professor_rows(trilha):
    """Todos os professores, indicando a atribuição (se houver) a esta trilha."""
    enrollments = {
        item.professor_id: item
        for item in ProfessorTrilha.query.filter_by(trilha_id=trilha.id).all()
    }
    rows = []
    for professor in User.query.filter_by(role=RoleEnum.PROFESSOR).order_by(User.nome).all():
        enrollment = enrollments.get(professor.id)
        concluidas = (
            ProfessorTrilhaService.count_completed_tasks(professor.id, trilha.id) if enrollment else 0
        )
        rows.append({
            'id': professor.id,
            'nome': professor.nome,
            'email': professor.email,
            'atribuida': enrollment is not None,
            'status': enrollment.status.value if enrollment else None,
            'concluidas': concluidas,
        })
    return rows


def _payload():
    """Extrai os dados da requisição suportando JSON ou form-data para manter 
    consistência em todos os endpoints de administração."""
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    return data


def _month_bucket(date_value):
    if not date_value:
        return None
    return date_value.strftime('%Y-%m')


def _safe_percentage(part, whole):
    if not whole:
        return 0.0
    return round((part / whole) * 100, 1)


def build_dashboard_metrics():
    """Constrói um conjunto de métricas para exibição no dashboard do admin."""
    total_users = User.query.count()
    total_professores = User.query.filter_by(role=RoleEnum.PROFESSOR).count()
    total_trilhas = Checklist.query.count()
    total_obrigatorias = Checklist.query.filter_by(obrigatoria=True).count()
    total_feedbacks = Feedback.query.count()
    trilhas_concluidas = ProfessorTrilha.query.filter_by(status=StatusEnum.CONCLUIDO).count()
    trilhas_em_andamento = ProfessorTrilha.query.filter_by(status=StatusEnum.EM_ANDAMENTO).count()
    total_jornadas = ProfessorTrilha.query.count()
    concluidas_com_data = ProfessorTrilha.query.filter(
        ProfessorTrilha.status == StatusEnum.CONCLUIDO,
        ProfessorTrilha.data_inicio.isnot(None),
        ProfessorTrilha.data_conclusao.isnot(None),
    ).all()
    if concluidas_com_data:
        tempo_medio = sum(
            max((item.data_conclusao - item.data_inicio).days, 0)
            for item in concluidas_com_data
        ) / len(concluidas_com_data)
    else:
        tempo_medio = 0

    limite_30_dias = datetime.utcnow() - timedelta(days=30)
    feedbacks_recentes = Feedback.query.filter(Feedback.data_envio >= limite_30_dias).count()
    ativacoes_recentes = ProfessorTrilha.query.filter(
        ProfessorTrilha.data_inicio.isnot(None),
        ProfessorTrilha.data_inicio >= limite_30_dias,
    ).count()

    return {
        'total_users': total_users,
        'total_professores': total_professores,
        'total_trilhas': total_trilhas,
        'total_obrigatorias': total_obrigatorias,
        'total_feedbacks': total_feedbacks,
        'trilhas_concluidas': trilhas_concluidas,
        'trilhas_em_andamento': trilhas_em_andamento,
        'conclusao_global_percentual': _safe_percentage(trilhas_concluidas, total_jornadas),
        'tempo_medio_conclusao_dias': round(tempo_medio, 1),
        'feedbacks_ultimos_30_dias': feedbacks_recentes,
        'ativacoes_ultimos_30_dias': ativacoes_recentes,
    }


def build_dashboard_analytics():
    """Produz payload analítico detalhado para gráficos e insights do dashboard."""
    status_counts = {
        'Não iniciado': ProfessorTrilha.query.filter_by(status=StatusEnum.NAO_INICIADO).count(),
        'Em andamento': ProfessorTrilha.query.filter_by(status=StatusEnum.EM_ANDAMENTO).count(),
        'Concluído': ProfessorTrilha.query.filter_by(status=StatusEnum.CONCLUIDO).count(),
    }

    tipo_map = {
        TipoEnum.PEDAGOGICA: 'Pedagógica',
        TipoEnum.INSTITUCIONAL: 'Institucional',
        TipoEnum.TECNOLOGICA: 'Tecnológica',
    }
    trilhas_tipo_counts = {}
    for tipo_enum, tipo_label in tipo_map.items():
        trilhas_tipo_counts[tipo_label] = Checklist.query.filter_by(tipo=tipo_enum).count()

    feedbacks = Feedback.query.order_by(Feedback.data_envio.asc()).all()
    feedback_by_month = defaultdict(int)
    for feedback in feedbacks:
        month = _month_bucket(feedback.data_envio)
        if month:
            feedback_by_month[month] += 1

    enrollments = ProfessorTrilha.query.all()
    starts_by_month = defaultdict(int)
    for enrollment in enrollments:
        month = _month_bucket(enrollment.data_inicio)
        if month:
            starts_by_month[month] += 1

    completion_by_trilha_labels = []
    completion_by_trilha_values = []
    trilhas = Checklist.query.order_by(Checklist.nome).all()
    for trilha in trilhas:
        related_tasks = [task.id for task in trilha.tasks]
        related_enrollments = ProfessorTrilha.query.filter_by(trilha_id=trilha.id).all()
        if not related_enrollments or not related_tasks:
            completion_by_trilha_labels.append(trilha.nome)
            completion_by_trilha_values.append(0)
            continue

        percentages = []
        for enrollment in related_enrollments:
            completed = ProfessorChecklist.query.filter(
                ProfessorChecklist.professor_id == enrollment.professor_id,
                ProfessorChecklist.task_id.in_(related_tasks),
                ProfessorChecklist.concluido == True,
            ).count()
            percentages.append(_safe_percentage(completed, len(related_tasks)))

        completion_by_trilha_labels.append(trilha.nome)
        completion_by_trilha_values.append(round(sum(percentages) / len(percentages), 1) if percentages else 0)

    all_months = sorted(set(list(feedback_by_month.keys()) + list(starts_by_month.keys())))
    if len(all_months) > 6:
        all_months = all_months[-6:]

    feedback_values = [feedback_by_month.get(month, 0) for month in all_months]
    starts_values = [starts_by_month.get(month, 0) for month in all_months]

    summary = build_dashboard_metrics()
    insights = [
        f"Taxa global de conclusão em {summary['conclusao_global_percentual']}%.",
        f"Tempo médio de conclusão estimado em {summary['tempo_medio_conclusao_dias']} dias.",
        f"{summary['feedbacks_ultimos_30_dias']} feedbacks coletados nos últimos 30 dias.",
        f"{summary['ativacoes_ultimos_30_dias']} ativações recentes sinalizam interesse de acesso e continuidade.",
    ]

    if completion_by_trilha_values:
        max_index = completion_by_trilha_values.index(max(completion_by_trilha_values))
        min_index = completion_by_trilha_values.index(min(completion_by_trilha_values))
        insights.append(
            f"Maior desempenho em '{completion_by_trilha_labels[max_index]}' com {completion_by_trilha_values[max_index]}% médio de conclusão."
        )
        insights.append(
            f"Oportunidade de melhoria em '{completion_by_trilha_labels[min_index]}' com {completion_by_trilha_values[min_index]}% médio de conclusão."
        )

    return {
        'status_distribution': {
            'labels': list(status_counts.keys()),
            'values': list(status_counts.values()),
        },
        'trilhas_por_tipo': {
            'labels': list(trilhas_tipo_counts.keys()),
            'values': list(trilhas_tipo_counts.values()),
        },
        'feedback_timeline': {
            'labels': all_months,
            'values': feedback_values,
        },
        'ativacoes_timeline': {
            'labels': all_months,
            'values': starts_values,
        },
        'completion_by_trilha': {
            'labels': completion_by_trilha_labels,
            'values': completion_by_trilha_values,
        },
        'insights': insights,
    }

@admin.route('/')
@login_required
def home():
    """Renderiza a landing page de administração.
    
    Apenas usuários com perfil de Admin têm acesso a esta rota."""
    if current_user.role != RoleEnum.ADMIN:
        return "Acesso negado", 403

    summary = build_dashboard_metrics()
    analytics_data = build_dashboard_analytics()
    return render_template(
        'admin/admin_dashboard.html',
        user=current_user,
        summary=summary,
        analytics=analytics_data,
    )


@admin.route('/analytics')
@login_required
def analytics():
    """Expõe as métricas do dashboard em formato JSON.
    
    Útil para eventuais integrações frontend (UI)."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    payload = {
        'summary': build_dashboard_metrics(),
        'analytics': build_dashboard_analytics(),
    }
    return jsonify(payload)


@admin.route('/professores', methods=['GET'])
@login_required
def professores():
    """Recupera e lista os professores cadastrados e o andamento em suas respectivas trilhas."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    professores_data = User.query.filter_by(role=RoleEnum.PROFESSOR).order_by(User.nome).all()
    payload = []

    for professor in professores_data:
        # Collect enrollment and task progress used by the admin list screen.
        enrollments = ProfessorTrilha.query.filter_by(professor_id=professor.id).all()
        trilha_ids = [item.trilha_id for item in enrollments]
        trilhas = Checklist.query.filter(Checklist.id.in_(trilha_ids)).all() if trilha_ids else []

        total_tasks = Task.query.filter(Task.checklist_id.in_(trilha_ids)).count() if trilha_ids else 0
        completed_tasks = 0
        if trilha_ids:
            task_ids = [task.id for task in Task.query.filter(Task.checklist_id.in_(trilha_ids)).all()]
            if task_ids:
                completed_tasks = ProfessorChecklist.query.filter(
                    ProfessorChecklist.professor_id == professor.id,
                    ProfessorChecklist.task_id.in_(task_ids),
                    ProfessorChecklist.concluido == True,
                ).count()

        payload.append({
            'id': professor.id,
            'nome': professor.nome,
            'email': professor.email,
            'trilhas_atribuidas': [{'id': trilha.id, 'nome': trilha.nome} for trilha in trilhas],
            'andamento': {
                'total_tarefas': total_tasks,
                'tarefas_concluidas': completed_tasks,
                'percentual': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            },
        })

    return render_template('admin/admin_professores.html', user=current_user, professores=payload)


@admin.route('/professores', methods=['POST'])
@login_required
def create_professor():
    """Realiza o cadastro de um novo usuário com perfil de professor."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    data = _payload()
    nome = (data.get('nome') or '').strip()
    email = (data.get('email') or '').strip().lower()
    senha = data.get('senha')

    if not nome or not email or not senha:
        return jsonify({'error': 'nome, email e senha são obrigatórios'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email já cadastrado'}), 400

    user = User(nome=nome, email=email, senha=generate_password_hash(senha), role=RoleEnum.PROFESSOR)
    db.session.add(user)
    db.session.commit()

    if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
        return redirect(url_for('admin.professores'))

    return jsonify({'id': user.id, 'nome': user.nome, 'email': user.email, 'role': user.role.value}), 201


@admin.route('/professores/novo', methods=['GET'])
@login_required
def new_professor_page():
    """Exibe a tela de cadastro (jornada em passos) de um novo professor."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    return render_template('admin/admin_professor_novo.html', user=current_user)


@admin.route('/professores/<int:user_id>', methods=['GET'])
@login_required
def professor_detail(user_id):
    """Ficha do professor: dados, trilhas atribuídas com progresso e feedbacks enviados."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    professor = _professor_or_404(user_id)
    trilhas = [row for row in _professor_trilha_rows(professor) if row['atribuida']]
    feedbacks = Feedback.query.filter_by(professor_id=professor.id).order_by(Feedback.data_envio.desc()).all()

    return render_template(
        'admin/admin_professor_ficha.html',
        user=current_user,
        professor=professor,
        trilhas=trilhas,
        feedbacks=feedbacks,
    )


@admin.route('/professores/<int:user_id>/trilhas', methods=['GET'])
@login_required
def professor_trilhas_page(user_id):
    """Tela para atribuir ou remover trilhas de um professor."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    professor = _professor_or_404(user_id)
    return render_template(
        'admin/admin_atribuir_trilhas.html',
        user=current_user,
        professor=professor,
        rows=_professor_trilha_rows(professor),
    )


@admin.route('/professores/<int:user_id>/trilhas', methods=['PUT'])
@login_required
def sync_professor_trilhas(user_id):
    """Sincroniza as trilhas atribuídas a um professor com a lista enviada."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    _professor_or_404(user_id)
    try:
        desired = _parse_assignments(_payload(), 'trilha_id')
        summary = ProfessorTrilhaService.sync_professor_trilhas(user_id, desired)
        return jsonify({'message': 'Trilhas atualizadas com sucesso', **summary})
    except ValueError as error:
        return jsonify({'error': str(error)}), 400


@admin.route('/trilhas/<int:trilha_id>/professores', methods=['GET'])
@login_required
def trilha_professores_page(trilha_id):
    """Tela para atribuir ou remover professores de uma trilha."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    trilha = _trilha_or_404(trilha_id)
    return render_template(
        'admin/admin_trilha_professores.html',
        user=current_user,
        trilha=trilha,
        rows=_trilha_professor_rows(trilha),
    )


@admin.route('/trilhas/<int:trilha_id>/professores', methods=['PUT'])
@login_required
def sync_trilha_professores(trilha_id):
    """Sincroniza os professores atribuídos a uma trilha com a lista enviada."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    _trilha_or_404(trilha_id)
    try:
        desired = _parse_assignments(_payload(), 'professor_id')
        summary = ProfessorTrilhaService.sync_trilha_professores(trilha_id, desired)
        return jsonify({'message': 'Professores atualizados com sucesso', **summary})
    except ValueError as error:
        return jsonify({'error': str(error)}), 400


@admin.route('/trilhas/<int:trilha_id>/conteudo', methods=['GET'])
@login_required
def trilha_content_page(trilha_id):
    """Tela de conteúdo da trilha: tarefas em ordem, com edição, exclusão e reordenação."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    trilha = _trilha_or_404(trilha_id)
    tasks = sorted(trilha.tasks, key=lambda item: item.ordem)
    return render_template('admin/admin_trilha_conteudo.html', user=current_user, trilha=trilha, tasks=tasks)


@admin.route('/trilhas/<int:trilha_id>/tarefas/nova', methods=['GET'])
@login_required
def new_task_page(trilha_id):
    """Tela (jornada em passos) para criar uma tarefa dentro de uma trilha."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    trilha = _trilha_or_404(trilha_id)
    return render_template('admin/admin_tarefa_nova.html', user=current_user, trilha=trilha, total=len(trilha.tasks) + 1)


@admin.route('/professores/<int:user_id>/editar', methods=['GET'])
@login_required
def edit_professor_page(user_id):
    """Exibe a tela de edição (jornada em passos) de um professor."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    professor = User.query.get(user_id)
    if not professor or professor.role != RoleEnum.PROFESSOR:
        abort(404)

    return render_template('admin/admin_professor_editar.html', user=current_user, professor=professor)


@admin.route('/trilhas/<int:trilha_id>/editar', methods=['GET'])
@login_required
def edit_trilha_page(trilha_id):
    """Exibe a tela de edição (jornada em passos) de uma trilha."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    trilha = Checklist.query.get(trilha_id)
    if not trilha:
        abort(404)

    return render_template(
        'admin/admin_trilha_editar.html',
        user=current_user,
        trilha=trilha,
        tipos=[tipo.value for tipo in TipoEnum],
    )


@admin.route('/tarefas/<int:task_id>/editar', methods=['GET'])
@login_required
def edit_task_page(task_id):
    """Exibe a tela de edição (jornada em passos) de uma tarefa."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    task = Task.query.get(task_id)
    if not task:
        abort(404)

    ordered_ids = [item.id for item in sorted(task.checklist.tasks, key=lambda item: (item.ordem, item.id))]
    return render_template(
        'admin/admin_tarefa_editar.html',
        user=current_user,
        task=task,
        trilha=task.checklist,
        posicao=ordered_ids.index(task.id) + 1,
        total=len(ordered_ids),
    )


@admin.route('/professores/<int:user_id>', methods=['PUT', 'PATCH'])
@login_required
def update_professor(user_id):
    """Atualiza as informações de cadastro (nome, email ou senha) de um professor específico."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    user = User.query.get(user_id)
    if not user or user.role != RoleEnum.PROFESSOR:
        return jsonify({'error': 'Professor não encontrado'}), 404

    data = _payload()
    if 'nome' in data:
        nome = (data.get('nome') or '').strip()
        if not nome:
            return jsonify({'error': 'Nome não pode ser vazio'}), 400
        user.nome = nome

    if 'email' in data:
        email = (data.get('email') or '').strip().lower()
        if not email:
            return jsonify({'error': 'Email não pode ser vazio'}), 400
        existing = User.query.filter(User.email == email, User.id != user_id).first()
        if existing:
            return jsonify({'error': 'Email já cadastrado'}), 400
        user.email = email

    if 'senha' in data and data.get('senha'):
        user.senha = generate_password_hash(data.get('senha'))

    db.session.commit()
    return jsonify({'id': user.id, 'nome': user.nome, 'email': user.email, 'role': user.role.value})


@admin.route('/trilhas', methods=['GET'])
@login_required
def trilhas_management():
    """Lista todas as trilhas disponíveis para o sistema."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    trilhas = Checklist.query.order_by(Checklist.nome).all()
    trilhas_data = []
    for trilha in trilhas:
        counts = {value: 0 for value in STATUS_LABELS}
        for enrollment in ProfessorTrilha.query.filter_by(trilha_id=trilha.id).all():
            counts[enrollment.status.value] += 1
        trilhas_data.append({
            'id': trilha.id,
            'nome': trilha.nome,
            'tipo': trilha.tipo.value if trilha.tipo else None,
            'obrigatoria': trilha.obrigatoria,
            'descricao': trilha.descricao,
            'total_tarefas': len(trilha.tasks),
            'status_counts': counts,
        })

    status_filter = request.args.get('status')
    if status_filter not in STATUS_LABELS:
        status_filter = ''

    return render_template(
        'admin/admin_trilhas.html',
        user=current_user,
        trilhas=trilhas_data,
        status_filter=status_filter,
    )


@admin.route('/tarefas-feedbacks', methods=['GET'])
@login_required
def tasks_feedbacks_management():
    """Fornece um catálogo das tarefas e o fluxo contínuo de feedbacks submetidos."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    # This response feeds two admin views: task catalog and submitted feedback stream.
    trilhas = Checklist.query.order_by(Checklist.nome).all()
    feedbacks = Feedback.query.order_by(Feedback.data_envio.desc()).all()

    data = {
        'tarefas_por_trilha': [
            {
                'trilha_id': trilha.id,
                'trilha_nome': trilha.nome,
                'tarefas': [
                    {
                        'id': task.id,
                        'descricao': task.descricao,
                        'ordem': task.ordem,
                        'material_apoio': task.material_apoio,
                        'link_apoio': task.link_apoio,
                        'documento_apoio': task.documento_apoio,
                    }
                    for task in sorted(trilha.tasks, key=lambda item: item.ordem)
                ],
            }
            for trilha in trilhas
        ],
        'feedbacks': [
            {
                'id': item.id,
                'professor_id': item.professor_id,
                'trilha_id': item.trilha_id,
                'comentario': item.comentario,
                'data_envio': item.data_envio.isoformat() if item.data_envio else None,
                'professor_nome': User.query.get(item.professor_id).nome if item.professor_id else "Desconhecido"
            }
            for item in feedbacks
        ],
    }
    return render_template('admin/admin_tarefas.html', user=current_user, **data)