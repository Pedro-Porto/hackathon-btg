# Plataforma de Análise de Boletos e Oferta de Crédito

Esta plataforma foi desenvolvida para transformar o processo de pagamento de boletos em uma oportunidade de negócio. No momento em que um cliente envia um boleto para pagamento via assistente virtual BTG, o sistema o intercepta e analisa em tempo real. Se for identificado como um financiamento, a plataforma gera e apresenta uma oferta de crédito BTG Pactual para quitar a dívida existente, resultando em parcelas menores e economia para o cliente.

A arquitetura é composta por microserviços assíncronos que se comunicam através do Apache Kafka. O uso de tópicos garante a resiliência e a integridade dos dados: se um serviço específico falhar, a informação essencial de negócio não se perde. O dado permanece no tópico e pode ser processado assim que o serviço se recuperar, garantindo a continuidade da análise sem prejudicar totalmente a experiência do usuário.

![Arquitetura da Plataforma](/diag.svg)

## Componentes da Arquitetura

### Ingest API:

Atua como um gateway principal com o cliente, que utiliza o bot do Telegram com o objetivo de realizar um pagamento. Este serviço recebe os documentos (fotos ou PDFs), gerencia a conversa inicial e publica o documento no tópico btg.raw para análise.

### Parse Service:

Consome os documentos do tópico btg.raw e utiliza o serviço AWS Textract para realizar o reconhecimento de caracteres, extraindo todo o texto contido na imagem do pagamento. O resultado é publicado no tópico btg.parsed.

### Interpret Service:

Recebe o texto extraído do tópico btg.parsed e utiliza um Modelo de Linguagem (Ollama) para interpretar os dados. Ele é treinado para identificar informações importantes que sugiram um financiamento, como a presença de "parcela X/Y" e o valor do pagamento. As informações estruturadas são publicadas no tópico btg.interpreted.

### Verify Service:

Atua como o principal serviço de validação. Recebe os dados interpretados do tópico btg.interpreted e realiza duas checagens: primeiro, busca no extrato do cliente por pagamentos de valor similar em meses anteriores, o que reforça a hipótese de uma cobrança recorrente (financiamento). Com maior confiança, o serviço instrui o Ingest API a interagir com o cliente, perguntando se o boleto é de um financiamento e, em caso afirmativo, qual o tipo (automóvel ou imóvel). O dado validado e enriquecido com a resposta do cliente é publicado no tópico btg.verified.

### Enrich Service:
Coleta os dados confirmados do tópico btg.verified e busca o perfil financeiro completo do cliente no banco de dados, incluindo informações de conta, histórico de crédito e investimentos, para montar o perfil de risco. O perfil consolidado e enriquecido é publicado no tópico btg.enriched.

### Match Service:

O cérebro financeiro da operação. Consome os dados do btg.enriched e realiza um cálculo de engenharia reversa (usando amortização SAC ou PRICE) para descobrir a taxa de juros praticada pelo concorrente. Para isso, também utiliza um LLM (Ollama) para garantir a padronização do nome do concorrente antes de salvar a taxa descoberta. Em seguida, verifica os produtos de crédito do BTG para encontrar uma opção de quitação que resulte em uma parcela mensal menor. Este serviço calcula a economia total e salva os dados da taxa do concorrente na base de dados, que serão expostos pelo serviço 'Provide' e consumidos pela interface de 'Inteligência de Mercado' (Front). O resultado da análise é publicado no tópico btg.matched.

### Compose Service:

Recebe os resultados do tópico btg.matched e utiliza um LLM (Ollama) para gerar uma mensagem personalizada. A comunicação é adaptada para apresentar a oferta de forma clara, destacando a economia que o cliente terá ao aceitar o crédito BTG. A mensagem final é publicada no tópico btg.composed.

### Notify Service:

Conclui o ciclo. Este serviço consome a mensagem final e humanizada do tópico btg.composed. Ele então chama a Ingest (API), instruindo-a a enviar essa mensagem de oferta formatada de volta ao cliente.

### Provide API:

Atua como a API de dados dedicada à inteligência de mercado. Ele fornece um endpoint (/api/offers) que consulta o banco de dados e retorna todas as ofertas de concorrentes que foram analisadas e salvas pelo Verify e finalizadas pelo serviço Match com possíveis ofertas BTG Pactual oferecidas ao cliente.

### Front para Inteligência de Mercado:

É a interface web (Dashboard de Inteligência de Mercado) construída em React, que consome a API do Provide. Este dashboard é a principal ferramenta de visualização para gestores e analistas BTG, exibindo métricas principais, tabelas interativas de ofertas ("Market Offers") e análises gráficas por banco ("Bank Analysis").

O seu principal valor estratégico é transformar os dados coletados pelo Verify e Match em inteligência de mercado acionável. Ao detalhar as taxas de juros exatas que os concorrentes estão praticando (e com as quais estão ganhando clientes), o dashboard permite ao BTG ajustar suas próprias ofertas de crédito, criar produtos mais competitivos e monitorar em tempo real as movimentações do mercado.

## Vantagens e Infraestrutura

A separação de cada serviço por responsabilidade única traz uma vantagem operacional chave: a escalabilidade seletiva. É possível provisionar mais recursos (como CPU e memória) apenas para os serviços que realmente precisam, como o Parse Service (que usa OCR) ou o Match Service (cálculos financeiros). Isso otimiza os custos de infraestrutura e garante alta performance onde ela é mais necessária, sem sobrecarregar o restante da plataforma.

Todos os serviços da plataforma são containerizados via Docker. Para executar o ambiente completo localmente, o docker compose inicializará toda a infraestrutura necessária, incluindo os microserviços e o Kafka.
Para a implementação do protótipo inicial, foi utilizada uma máquina local exposta para a internet utilizando tunnels da cloudflare. Isso consegue tanto proteger as implementações de ataques públicos de DDOS por causa da proxy da cloudflare quanto proteger rotas privadas utilizando o zero trust.

## Configuração

### Credenciais AWS

Configure suas credenciais AWS no diretório home:

```Bash
mkdir -p ~/.aws
````

Crie o arquivo `~/.aws/credentials`:

```ini, TOML
[default]
aws_access_key_id = SUA_ACCESS_KEY
aws_secret_access_key = SUA_SECRET_KEY
```

Crie o arquivo `~/.aws/config`:

```ini, TOML
[default]
region = us-east-1
```

### Token do Bot do Telegram

```bash
export BOT_TOKEN=seu_token_do_telegram_bot
```

Para obter um token do Telegram:

1.  Fale com @BotFather no Telegram
2.  Use o comando /newbot e siga as instruções
3.  Copie o token fornecido

## Como Rodar

### Iniciar todos os serviços

```bash
docker compose up -d
```

### Parar todos os serviços

```bash
docker compose down
```