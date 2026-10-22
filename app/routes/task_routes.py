"""Task completion routes used by professors and admins."""

from flask import Blueprint, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import RoleEnum
from app.services.task_service import TaskService
from app.services.professor_checklist_service import ProfessorChecklistService


tasks = Blueprint('tasks', __name__)


def _wants_json_response():
    """Prefer JSON for JSON requests or clients that explicitly prefer JSON."""
    return (
        request.is_json
        or request.accept_mimetypes['application/json']
        > request.accept_mimetypes['text/html']
    )


def _payload():
    """Read JSON or form data and return a plain dictionary."""
    # Keep route behavior identical for browser forms and API calls.
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    return data


def _serialize_task(task):
    """Convert a task instance into a compact dictionary."""
    return {
        'id': task.id,
        'descricao': task.descricao,
        'ordem': task.ordem,
        'checklist_id': task.checklist_id,
        'material_apoio': task.material_apoio,
        'link_apoio': task.link_apoio,
        'documento_apoio': task.documento_apoio,
    }


@tasks.route('/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Mark a task as completed for the current professor."""
    if current_user.role != RoleEnum.PROFESSOR:
        return jsonify({'error': 'Acesso negado'}), 403

    try:
        completion = ProfessorChecklistService.mark_task_complete(current_user.id, task_id)
        if not _wants_json_response():
            return redirect(url_for('professor.task_detail', task_id=task_id))
        return jsonify({
            'message': 'Tarefa concluída com sucesso',
            'task_id': completion.task_id,
            'concluido': completion.concluido,
        })
    except ValueError as error:
        return jsonify({'error': str(error)}), 400


@tasks.route('/<int:task_id>/incomplete', methods=['POST'])
@login_required
def incomplete_task(task_id):
    """Mark a task as pending again for the current professor."""
    if current_user.role != RoleEnum.PROFESSOR:
        return jsonify({'error': 'Acesso negado'}), 403

    try:
        completion = ProfessorChecklistService.mark_task_incomplete(current_user.id, task_id)
        if not _wants_json_response():
            return redirect(url_for('professor.task_detail', task_id=task_id))
        return jsonify({
            'message': 'Tarefa marcada como pendente',
            'task_id': completion.task_id,
            'concluido': completion.concluido,
        })
    except ValueError as error:
        return jsonify({'error': str(error)}), 400


@tasks.route('/<int:task_id>/status', methods=['GET'])
@login_required
def task_status(task_id):
    """Return completion status for one task and professor."""
    if current_user.role != RoleEnum.PROFESSOR:
        return jsonify({'error': 'Acesso negado'}), 403

    completion = ProfessorChecklistService.get_professor_task_status(current_user.id, task_id)
    if not completion:
        return jsonify({'task_id': task_id, 'concluido': False})

    return jsonify({
        'task_id': task_id,
        'concluido': completion.concluido,
        'data_conclusao': completion.data_conclusao,
    })


@tasks.route('/<int:task_id>', methods=['PUT', 'PATCH'])
@login_required
def update_task(task_id):
    """Update task details; restricted to admin users."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    data = _payload()
    try:
        task = TaskService.update_task(
            task_id=task_id,
            descricao=data.get('descricao'),
            ordem=int(data['ordem']) if data.get('ordem') not in (None, '') else None,
            material_apoio=data.get('material_apoio') if 'material_apoio' in data else None,
            link_apoio=data.get('link_apoio') if 'link_apoio' in data else None,
            documento_apoio=data.get('documento_apoio') if 'documento_apoio' in data else None,
        )
        return jsonify(_serialize_task(task))
    except (ValueError, TypeError) as error:
        return jsonify({'error': str(error)}), 400


@tasks.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Delete one task; restricted to admin users."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    try:
        TaskService.delete_task(task_id)
        return jsonify({'message': 'Tarefa removida com sucesso'})
    except ValueError as error:
        return jsonify({'error': str(error)}), 400


@tasks.route('/trilhas/<int:trilha_id>/reorder', methods=['POST'])
@login_required
def reorder_tasks(trilha_id):
    """Reorder tasks inside one trilha; restricted to admin users."""
    if current_user.role != RoleEnum.ADMIN:
        return jsonify({'error': 'Acesso negado'}), 403

    data = _payload()
    # Allow both list input and comma-separated strings for easier integration.
    task_ids = data.get('task_ids', [])
    if isinstance(task_ids, str):
        task_ids = [int(value) for value in task_ids.split(',') if value.strip()]

    try:
        TaskService.reorder_tasks(trilha_id, [int(task_id) for task_id in task_ids])
        return jsonify({'message': 'Tarefas reordenadas com sucesso'})
    except (ValueError, TypeError) as error:
        return jsonify({'error': str(error)}), 400
