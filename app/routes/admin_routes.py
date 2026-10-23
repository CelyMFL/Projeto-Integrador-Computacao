"""Rotas do administrador para telas de gestão e dashboard."""

from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import RoleEnum
from app.models.user import User
from app.models.checklist import Checklist, TipoEnum
from app.models.feedback import Feedback
from app.models.professor_trilha import ProfessorTrilha, StatusEnum
from app.models.professor_checklist import ProfessorChecklist
from app.models.task import Task
from app import db
from werkzeug.security import generate_password_hash

admin = Blueprint('admin', __name__)


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

        status = StatusEnum.NAO_INICIADO.value
        if any(item.status == StatusEnum.CONCLUIDO for item in enrollments):
            status = StatusEnum.CONCLUIDO.value
        elif any(item.status == StatusEnum.EM_ANDAMENTO for item in enrollments):
            status = StatusEnum.EM_ANDAMENTO.value

        payload.append({
            'id': professor.id,
            'nome': professor.nome,
            'email': professor.email,
            'status': status,
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
    trilhas_data = [
        {
            'id': trilha.id,
            'nome': trilha.nome,
            'tipo': trilha.tipo.value if trilha.tipo else None,
            'obrigatoria': trilha.obrigatoria,
            'descricao': trilha.descricao,
            'total_tarefas': len(trilha.tasks),
        }
        for trilha in trilhas
    ]
    return render_template('admin/admin_trilhas.html', user=current_user, trilhas=trilhas_data)


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