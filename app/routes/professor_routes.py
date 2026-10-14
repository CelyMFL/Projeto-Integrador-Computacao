"""Rotas voltadas ao perfil Professor, mapeadas diretamente para as telas do frontend."""

from flask import Blueprint, jsonify, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models import RoleEnum, Checklist, Task, ProfessorTrilha, StatusEnum, ProfessorChecklist
from app.services.feedback_service import FeedbackService


professor = Blueprint('professor', __name__)


def _payload():
    """Aceita tanto JSON quanto form-data para que clientes web e APIs compartilhem o mesmo endpoint."""
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    return data


def _serialize_task(task, completed_ids=None):
    """Serializa os dados de uma tarefa individual, identificando se foi concluída."""
    completed_ids = completed_ids or set()
    return {
        'id': task.id,
        'descricao': task.descricao,
        'ordem': task.ordem,
        'status': 'concluido' if task.id in completed_ids else 'pendente',
        'material_apoio': task.material_apoio,
        'link_apoio': task.link_apoio,
        'documento_apoio': task.documento_apoio,
    }


def _serialize_trilha(trilha, enrollment=None, completed_ids=None):
    """Serializa uma trilha completa e seu progresso baseado nas tarefas do professor."""
    completed_ids = completed_ids or set()
    # Mantém a ordem das tarefas determinística para a renderização da timeline no frontend.
    tasks = sorted(trilha.tasks, key=lambda item: item.ordem)
    completed_tasks = sum(1 for task in tasks if task.id in completed_ids)
    total_tasks = len(tasks)
    completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    return {
        'id': trilha.id,
        'nome': trilha.nome,
        'tipo': trilha.tipo.value if trilha.tipo else None,
        'descricao': trilha.descricao,
        'obrigatoria': trilha.obrigatoria,
        'status': enrollment.status.value if enrollment else StatusEnum.NAO_INICIADO.value,
        'progresso': {
            'total_tarefas': total_tasks,
            'tarefas_concluidas': completed_tasks,
            'percentual': completion_percentage,
        },
        'tasks': [_serialize_task(task, completed_ids) for task in tasks],
    }


@professor.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Renderiza a tela de Dashboard / Minha integração do professor."""
    if current_user.role != RoleEnum.PROFESSOR:
        return jsonify({'error': 'Acesso negado'}), 403

    # Enrollment is the source of truth for which trilhas are assigned to this professor.
    enrollments = ProfessorTrilha.query.filter_by(professor_id=current_user.id).all()
    trilha_ids = [item.trilha_id for item in enrollments]

    completed_records = ProfessorChecklist.query.filter_by(
        professor_id=current_user.id,
        concluido=True,
    ).all()
    completed_ids = {item.task_id for item in completed_records}

    trilhas = Checklist.query.filter(Checklist.id.in_(trilha_ids)).all() if trilha_ids else []
    enrollment_map = {item.trilha_id: item for item in enrollments}

    trilhas_payload = [
        _serialize_trilha(trilha, enrollment_map.get(trilha.id), completed_ids)
        for trilha in trilhas
    ]

    all_tasks = [task for trilha in trilhas for task in trilha.tasks]
    total_tasks = len(all_tasks)
    completed_tasks = sum(1 for task in all_tasks if task.id in completed_ids)
    progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    pending_tasks = sorted(
        [task for task in all_tasks if task.id not in completed_ids],
        key=lambda item: (item.checklist_id, item.ordem),
    )

    data = {
        'user': {
            'id': current_user.id,
            'nome': current_user.nome,
            'email': current_user.email,
            'role': current_user.role.value,
        },
        'trilhas_atribuidas': trilhas_payload,
        'progresso_geral': {
            'total_tarefas': total_tasks,
            'tarefas_concluidas': completed_tasks,
            'percentual': progress,
        },
        'proximas_tarefas': [
            {
                'task_id': task.id,
                'descricao': task.descricao,
                'trilha_id': task.checklist_id,
            }
            for task in pending_tasks[:5]
        ],
        'trilhas_obrigatorias': [
            {
                'id': trilha.id,
                'nome': trilha.nome,
                'status': enrollment_map.get(trilha.id).status.value
                if enrollment_map.get(trilha.id)
                else StatusEnum.NAO_INICIADO.value,
            }
            for trilha in trilhas
            if trilha.obrigatoria
        ],
    }

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(data)
        
    return render_template('professor/dashboard.html', data=data)


@professor.route('/trilhas/<int:trilha_id>', methods=['GET'])
@login_required
def trilha_detail(trilha_id):
    """Exibe os detalhes e o progresso de uma Trilha específica."""
    if current_user.role != RoleEnum.PROFESSOR:
        return jsonify({'error': 'Acesso negado'}), 403

    trilha = Checklist.query.get(trilha_id)
    if not trilha:
        return jsonify({'error': 'Trilha não encontrada'}), 404

    enrollment = ProfessorTrilha.query.filter_by(
        professor_id=current_user.id,
        trilha_id=trilha_id,
    ).first()

    completed_ids = {
        item.task_id
        for item in ProfessorChecklist.query.filter_by(
            professor_id=current_user.id,
            concluido=True,
        ).all()
    }

    data = _serialize_trilha(trilha, enrollment, completed_ids)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(data)
    return render_template('professor/trilha.html', trilha=data)


@professor.route('/tarefas/<int:task_id>', methods=['GET'])
@login_required
def task_detail(task_id):
    """Recupera os detalhes e status de uma Tarefa específica."""
    if current_user.role != RoleEnum.PROFESSOR:
        return jsonify({'error': 'Acesso negado'}), 403

    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Tarefa não encontrada'}), 404

    completion = ProfessorChecklist.query.filter_by(
        professor_id=current_user.id,
        task_id=task_id,
    ).first()

    data = {
        'id': task.id,
        'descricao': task.descricao,
        'status': 'concluido' if completion and completion.concluido else 'pendente',
        'checklist_id': task.checklist_id,
        'material_apoio': task.material_apoio,
        'link_apoio': task.link_apoio,
        'documento_apoio': task.documento_apoio,
    }
    
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(data)
        
    return render_template('professor/tarefa.html', task=data)


@professor.route('/feedback', methods=['GET'])
@login_required
def feedback_form_context():
    """Retorna os dados necessários para popular o formulário de envio de Feedback."""
    if current_user.role != RoleEnum.PROFESSOR:
        return jsonify({'error': 'Acesso negado'}), 403

    data = {
        'message': 'Formulário de feedback disponível',
        'campos': ['comentario', 'trilha_id (opcional)'],
        'trilhas_disponiveis': [
            {'id': item.id, 'nome': item.nome}
            for item in Checklist.query.order_by(Checklist.nome).all()
        ],
    }
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(data)
    return render_template('professor/feedback.html', data=data)


@professor.route('/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Recebe e salva um novo feedback submetido pelo professor."""
    if current_user.role != RoleEnum.PROFESSOR:
        return jsonify({'error': 'Acesso negado'}), 403

    # The same payload contract is used by form screens and pure JSON clients.
    data = _payload()
    try:
        item = FeedbackService.submit_feedback(
            professor_id=current_user.id,
            comentario=data.get('comentario'),
            trilha_id=int(data['trilha_id']) if data.get('trilha_id') not in (None, '') else None,
        )
        if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
            return redirect(url_for('professor.dashboard'))
        return jsonify({
            'id': item.id,
            'comentario': item.comentario,
            'trilha_id': item.trilha_id,
            'data_envio': item.data_envio.isoformat() if item.data_envio else None,
        }), 201
    except (ValueError, TypeError) as error:
        return jsonify({'error': str(error)}), 400
