# Publicação e implantação no Azure

O script `deploy_acr.py`, na raiz do repositório, constrói a imagem da aplicação
e publica uma nova versão no Azure Container Registry (ACR). Ele não altera nem
reinicia o Azure App Service.

## Configuração padrão

| Item | Valor |
| --- | --- |
| ACR | `projetointegrador2` |
| Servidor do registry | `projetointegrador2.azurecr.io` |
| Repositório da imagem | `projeto_integrador_2` |
O `Dockerfile` na raiz é usado para construir a imagem. O nome completo publicado
segue o formato:

```text
projetointegrador2.azurecr.io/projeto_integrador_2:<versão>
```

## Pré-requisitos

- Docker instalado e em execução.
- Azure CLI instalado e disponível no `PATH`.
- Conta autenticada no Azure CLI (`az login`) e assinatura correta selecionada.
- Permissão para listar e publicar imagens no ACR.

O script verifica se `az`, `docker`, `Dockerfile` e `requirements.txt` estão
disponíveis. A aplicação precisa ser atualizada separadamente para usar a tag
publicada, caso desejado.

No Windows, o Azure CLI é normalmente instalado como `az.cmd`. O script chama
esse arquivo por meio do interpretador de comandos do Windows; não é necessário
adicionar ou renomear arquivos do Azure CLI.

## Versões e tags

As tags são versões estáveis no formato `MAJOR.MINOR.PATCH` (por exemplo,
`1.0.0`). O script consulta as tags no ACR, encontra a versão válida mais alta
e incrementa o patch: depois de `1.0.9`, a próxima tag é `1.0.10`.

Se o repositório ainda não existir no ACR, a primeira tag será `1.0.0`. Se já
houver tags, mas nenhuma seguir o formato `X.Y.Z`, o script encerra com erro
para evitar escolher uma versão arbitrária. Tags adicionais que não sejam
SemVer são ignoradas quando o repositório também possui tags `X.Y.Z`.

## Simular

Execute na raiz do projeto:

```bash
python deploy_acr.py --dry-run
```

A simulação consulta o ACR para calcular a próxima tag e imprime os comandos que
seriam executados; ela não constrói nem envia uma imagem. Por consultar o ACR,
ainda exige Azure CLI autenticado e acesso de leitura ao registry.

## Publicar no ACR

Confirme a assinatura ativa e autentique-se:

```bash
az login
az account show
```

Em seguida, execute o script:

```bash
python deploy_acr.py
```

O script executa, nesta ordem:

1. Consulta o ACR e calcula a próxima versão.
2. Autentica o Docker no ACR por meio do Azure CLI.
3. Constrói `projeto_integrador_2:<versão>` com o `Dockerfile` da raiz.
4. Marca a imagem como `projetointegrador2.azurecr.io/projeto_integrador_2:<versão>`.
5. Publica essa tag no ACR.

Para conferir as opções disponíveis:

```bash
python deploy_acr.py --help
```

O script para no primeiro comando que falhar e apresenta o comando que retornou
erro. O App Service não é atualizado pelo script; selecione a nova imagem no
serviço separadamente quando quiser implantá-la.
