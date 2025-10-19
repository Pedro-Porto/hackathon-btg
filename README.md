# Hackathon BTG


### Serviços

- **API**: Interface com Telegram Bot
- **Textract**: Extração de texto de imagens usando AWS Textract
- **Interpreter**: Interpretação de dados extraídos usando LLM
- **Verify**: Validação e verificação de dados
- **Enrich**: Enriquecimento com dados do banco
- **Match**: Matching de ofertas e cálculo de juros
- **Compose**: Composição de mensagens de resposta
- **Notify**: Envio de notificações via Telegram
- **Provide**: API REST para consulta de ofertas
- **Front**: Dashboard web React + Vite

## 🔧 Pré-requisitos

- Docker e Docker Compose
- Credenciais AWS (com acesso ao Textract)
- Token do Bot do Telegram

## ⚙️ Configuração

### 1. Credenciais AWS

Configure suas credenciais AWS no diretório home:

```bash
mkdir -p ~/.aws
```

Crie o arquivo `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = SUA_ACCESS_KEY
aws_secret_access_key = SUA_SECRET_KEY
```

Crie o arquivo `~/.aws/config`:

```ini
[default]
region = us-east-1
```

### 2. Token do Bot do Telegram


```bash
export BOT_TOKEN=seu_token_do_telegram_bot
```

Para obter um token do Telegram:
1. Fale com [@BotFather](https://t.me/botfather) no Telegram
2. Use o comando `/newbot` e siga as instruções
3. Copie o token fornecido



## 🚀 Como Rodar

### Iniciar todos os serviços

```bash
docker compose up -d
```


### Parar todos os serviços

```bash
docker compose down
```

Desenvolvido durante o Hackathon semcomp BTG 2025.
