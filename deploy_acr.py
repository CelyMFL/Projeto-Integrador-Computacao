"""Build, publish, and deploy the project image to Azure Container Registry."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ACR_NAME = "projetointegrador2"
ACR_LOGIN_SERVER = f"{ACR_NAME}.azurecr.io"
IMAGE_NAME = "projeto_integrador_2"
INITIAL_VERSION = (1, 0, 0)
VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class DeploymentError(Exception):
    """Raised when a deployment prerequisite or command fails."""


def run_command(command: list[str], *, capture_output: bool = False) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=capture_output,
            shell=os.name == "nt" and command[0] == "az",
            text=True,
        )
    except FileNotFoundError as error:
        raise DeploymentError(f"Comando não encontrado: {command[0]}") from error

    if result.returncode != 0:
        if capture_output and result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise DeploymentError(
            f"Comando falhou com código {result.returncode}: {' '.join(command)}"
        )
    return result.stdout.strip() if capture_output else ""


def parse_version(tag: str) -> tuple[int, int, int] | None:
    match = VERSION_PATTERN.fullmatch(tag)
    if match is None:
        return None
    return tuple(map(int, match.groups()))


def next_version(tags: list[str]) -> str:
    versions = [version for tag in tags if (version := parse_version(tag))]
    if not versions:
        if tags:
            raise DeploymentError(
                "O repositório já possui tags, mas nenhuma segue o padrão X.Y.Z."
            )
        return ".".join(map(str, INITIAL_VERSION))

    major, minor, patch = max(versions)
    return f"{major}.{minor}.{patch + 1}"


def get_registry_tags() -> list[str]:
    repositories_output = run_command(
        ["az", "acr", "repository", "list", "--name", ACR_NAME, "--output", "json"],
        capture_output=True,
    )
    try:
        repositories = json.loads(repositories_output)
    except json.JSONDecodeError as error:
        raise DeploymentError("O Azure CLI retornou uma lista de repositórios inválida.") from error
    if not isinstance(repositories, list) or not all(
        isinstance(repository, str) for repository in repositories
    ):
        raise DeploymentError("O Azure CLI retornou uma lista de repositórios inválida.")
    if IMAGE_NAME not in repositories:
        return []

    output = run_command(
        [
            "az",
            "acr",
            "repository",
            "show-tags",
            "--name",
            ACR_NAME,
            "--repository",
            IMAGE_NAME,
            "--output",
            "json",
        ],
        capture_output=True,
    )
    try:
        tags = json.loads(output)
    except json.JSONDecodeError as error:
        raise DeploymentError("O Azure CLI retornou uma lista de tags inválida.") from error
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise DeploymentError("O Azure CLI retornou uma lista de tags inválida.")
    return tags


def check_prerequisites() -> None:
    missing = [name for name in ("az", "docker") if shutil.which(name) is None]
    if missing:
        raise DeploymentError(
            f"Instale e disponibilize no PATH os comandos: {', '.join(missing)}."
        )
    if not (PROJECT_ROOT / "Dockerfile").is_file():
        raise DeploymentError(f"Dockerfile não encontrado em {PROJECT_ROOT}.")
    if not (PROJECT_ROOT / "requirements.txt").is_file():
        raise DeploymentError(f"requirements.txt não encontrado em {PROJECT_ROOT}.")


def publish_image(version: str, *, dry_run: bool) -> None:
    local_image = f"{IMAGE_NAME}:{version}"
    registry_image = f"{ACR_LOGIN_SERVER}/{IMAGE_NAME}:{version}"
    commands = [
        ["az", "acr", "login", "--name", ACR_NAME],
        ["docker", "build", "--tag", local_image, "."],
        ["docker", "tag", local_image, registry_image],
        ["docker", "push", registry_image],
    ]

    if dry_run:
        print("Simulação: nenhum comando de build ou publicação foi executado.")
        for command in commands:
            print("  " + " ".join(command))
        return

    run_command(["az", "account", "show", "--output", "none"])
    for command in commands:
        run_command(command)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera uma tag e publica a imagem no Azure Container Registry."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra os comandos sem construir ou publicar a imagem.",
    )
    args = parser.parse_args()

    try:
        check_prerequisites()
        if not args.dry_run:
            run_command(["az", "account", "show", "--output", "none"])
        version = next_version(get_registry_tags())
        print(f"Nova tag: {version}")
        publish_image(version, dry_run=args.dry_run)
    except DeploymentError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    if not args.dry_run:
        print(f"Imagem publicada: {ACR_LOGIN_SERVER}/{IMAGE_NAME}:{version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
