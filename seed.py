from app import create_app, db
from app.models.user import User, RoleEnum
from app.models.task import Task
from app.models.checklist import Checklist, TipoEnum
from app.models.professor_trilha import ProfessorTrilha, StatusEnum
from app.models.professor_checklist import ProfessorChecklist
from app.models.feedback import Feedback
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from datetime import datetime, timedelta

app = create_app()

SENHA_PADRAO = "123"

PROFESSORES = [
    ("Professor Teste", "prof@test.com"),
    ("Ricardo Silva", "ricardo.silva@email.com"),
    ("Ana Paula", "ana.paula@email.com"),
    ("João Mendes", "joao.mendes@email.com"),
    ("Maria Souza", "maria.souza@email.com"),
    ("Carlos Oliveira", "carlos.oliveira@email.com"),
]

# Cada tarefa: (descricao, material_apoio, link_apoio). Material e link são opcionais.
TRILHAS = [
    {
        "nome": "Trilha Pedagógica",
        "descricao": "Orientações sobre práticas pedagógicas, critérios de avaliação e rotina em sala.",
        "tipo": TipoEnum.PEDAGOGICA,
        "obrigatoria": True,
        "tarefas": [
            ("Ler o projeto político-pedagógico da escola", "Projeto político-pedagógico (PPP)", None),
            ("Conhecer o currículo e a base curricular do seu componente", "Documento curricular do estado", None),
            ("Elaborar o plano de ensino do bimestre", "Modelo de plano de ensino", None),
            ("Conhecer os critérios e instrumentos de avaliação", "Guia de avaliação da aprendizagem", None),
            ("Registrar frequência e notas no diário de classe", "Manual do diário de classe", None),
            ("Participar da reunião de alinhamento pedagógico", None, None),
        ],
    },
    {
        "nome": "Trilha Institucional",
        "descricao": "Normas, calendário, canais internos e funcionamento geral da instituição.",
        "tipo": TipoEnum.INSTITUCIONAL,
        "obrigatoria": True,
        "tarefas": [
            ("Ler o regimento escolar", "Regimento escolar", None),
            ("Consultar o calendário letivo e as datas de conselho de classe", "Calendário letivo", None),
            ("Conhecer os canais de comunicação com a coordenação e a secretaria", None, None),
            ("Conhecer o protocolo de ocorrências e acolhimento de estudantes", "Protocolo de convivência escolar", None),
        ],
    },
    {
        "nome": "Trilha Tecnológica",
        "descricao": "Acesso aos sistemas acadêmicos e ferramentas digitais.",
        "tipo": TipoEnum.TECNOLOGICA,
        "obrigatoria": False,
        "tarefas": [
            ("Ativar o e-mail institucional e trocar a senha inicial", None, None),
            ("Acessar o sistema de secretaria digital", "Tutorial da secretaria digital", None),
            ("Criar uma turma e publicar uma atividade na plataforma de ensino", "Guia da plataforma de ensino", None),
        ],
    },
    {
        "nome": "Comunicação Assertiva",
        "descricao": "Desenvolvimento de habilidades interpessoais para líderes e docentes.",
        "tipo": TipoEnum.PEDAGOGICA,
        "obrigatoria": False,
        "tarefas": [
            ("Entender os estilos de comunicação: passivo, agressivo e assertivo", "Texto: estilos de comunicação", None),
            ("Praticar a escuta ativa em uma conversa com um colega", None, None),
            ("Dar e receber feedback de forma construtiva", "Roteiro de feedback", None),
            ("Conduzir uma conversa difícil com estudante ou responsável", None, None),
        ],
    },
    {
        "nome": "Introdução ao Azure",
        "descricao": "Fundamentos de nuvem e arquitetura para projetos educacionais.",
        "tipo": TipoEnum.TECNOLOGICA,
        "obrigatoria": False,
        "tarefas": [
            ("Entender o que é computação em nuvem e seus modelos de serviço", None,
             "https://learn.microsoft.com/pt-br/training/azure/"),
            ("Conhecer os principais serviços do Azure: computação, rede e armazenamento", None,
             "https://learn.microsoft.com/pt-br/azure/architecture/"),
            ("Criar uma conta gratuita e publicar um primeiro recurso", None,
             "https://azure.microsoft.com/pt-br/free/"),
        ],
    },
]

# Quantidade de tarefas concluídas por professor em cada trilha, na ordem da trilha.
# 0 = matriculado sem iniciar; igual ao total de tarefas = trilha concluída.
# O status da trilha é derivado desse número, então os dados ficam sempre coerentes.
PROGRESSO = {
    "prof@test.com": {
        "Trilha Pedagógica": 2,
        "Trilha Institucional": 1,
        "Trilha Tecnológica": 0,
    },
    "ricardo.silva@email.com": {
        "Trilha Pedagógica": 5,
        "Trilha Institucional": 3,
        "Trilha Tecnológica": 1,
    },
    "ana.paula@email.com": {
        "Trilha Pedagógica": 6,
        "Introdução ao Azure": 2,
    },
    "joao.mendes@email.com": {
        "Trilha Institucional": 1,
    },
    "maria.souza@email.com": {
        "Trilha Institucional": 4,
        "Comunicação Assertiva": 2,
    },
    "carlos.oliveira@email.com": {
        "Trilha Tecnológica": 3,
        "Introdução ao Azure": 0,
    },
}

# (e-mail do professor, nome da trilha ou None, comentário)
FEEDBACKS = [
    ("ana.paula@email.com", "Introdução ao Azure",
     "Os módulos de Azure ajudaram a entender como funciona a hospedagem de sistemas na nuvem."),
    ("ana.paula@email.com", "Trilha Pedagógica",
     "Excelente material de apoio nas atividades pedagógicas, principalmente o modelo de plano de ensino."),
    ("ricardo.silva@email.com", "Trilha Institucional",
     "Seria útil incluir o contato direto de cada setor na trilha institucional."),
    ("maria.souza@email.com", "Comunicação Assertiva",
     "A atividade de escuta ativa foi muito boa para aplicar com a turma."),
    ("carlos.oliveira@email.com", None,
     "Gostaria de sugerir mais trilhas sobre Inteligência Artificial na educação."),
]


def recriar_banco():
    try:
        engine_name = db.engine.dialect.name
    except Exception:
        engine_name = None

    if engine_name == 'mysql':
        with db.engine.begin() as conn:
            conn.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
            conn.execute(text('DROP TABLE IF EXISTS user_tasks;'))
            db.metadata.drop_all(bind=conn)
            db.metadata.create_all(bind=conn)
            conn.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
    else:
        db.drop_all()
        db.create_all()


def criar_usuarios():
    admin = User(
        nome="Administrador Geral",
        email="admin@test.com",
        senha=generate_password_hash(SENHA_PADRAO),
        role=RoleEnum.ADMIN,
    )
    db.session.add(admin)

    professores = {}
    for nome, email in PROFESSORES:
        professores[email] = User(
            nome=nome,
            email=email,
            senha=generate_password_hash(SENHA_PADRAO),
            role=RoleEnum.PROFESSOR,
        )
        db.session.add(professores[email])

    db.session.commit()
    return professores


def criar_trilhas():
    trilhas = {}
    tarefas = {}
    for dados in TRILHAS:
        trilha = Checklist(
            nome=dados["nome"],
            descricao=dados["descricao"],
            tipo=dados["tipo"],
            obrigatoria=dados["obrigatoria"],
        )
        db.session.add(trilha)
        db.session.flush()

        tarefas[trilha.nome] = []
        for ordem, (descricao, material, link) in enumerate(dados["tarefas"], start=1):
            tarefa = Task(
                descricao=descricao,
                ordem=ordem,
                material_apoio=material,
                link_apoio=link,
                checklist_id=trilha.id,
            )
            db.session.add(tarefa)
            tarefas[trilha.nome].append(tarefa)
        trilhas[trilha.nome] = trilha

    db.session.commit()
    return trilhas, tarefas


def criar_progresso(professores, trilhas, tarefas):
    agora = datetime.utcnow()

    for email, matriculas in PROGRESSO.items():
        professor = professores[email]
        for nome_trilha, concluidas in matriculas.items():
            lista = tarefas[nome_trilha]
            total = len(lista)

            if concluidas == 0:
                status = StatusEnum.NAO_INICIADO
            elif concluidas >= total:
                status = StatusEnum.CONCLUIDO
            else:
                status = StatusEnum.EM_ANDAMENTO

            inicio = None if status == StatusEnum.NAO_INICIADO else agora - timedelta(days=concluidas * 3 + 2)
            fim = agora - timedelta(days=1) if status == StatusEnum.CONCLUIDO else None
            db.session.add(ProfessorTrilha(
                professor_id=professor.id,
                trilha_id=trilhas[nome_trilha].id,
                status=status,
                data_inicio=inicio,
                data_conclusao=fim,
            ))

            for posicao, tarefa in enumerate(lista[:concluidas]):
                db.session.add(ProfessorChecklist(
                    professor_id=professor.id,
                    task_id=tarefa.id,
                    concluido=True,
                    data_conclusao=agora - timedelta(days=(concluidas - posicao) * 2),
                ))

    db.session.commit()


def criar_feedbacks(professores, trilhas):
    agora = datetime.utcnow()
    for indice, (email, nome_trilha, comentario) in enumerate(FEEDBACKS):
        db.session.add(Feedback(
            professor_id=professores[email].id,
            trilha_id=trilhas[nome_trilha].id if nome_trilha else None,
            comentario=comentario,
            data_envio=agora - timedelta(days=len(FEEDBACKS) - indice),
        ))
    db.session.commit()


with app.app_context():
    recriar_banco()

    print("Iniciando a criação de dados...")

    professores = criar_usuarios()
    trilhas, tarefas = criar_trilhas()
    criar_progresso(professores, trilhas, tarefas)
    criar_feedbacks(professores, trilhas)

    print("Banco de dados populado com sucesso!")
