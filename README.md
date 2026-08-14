# Garimpo — MVP

Site estático (HTML/CSS/JS puro, sem build, sem framework, sem backend) para
listar ofertas com links de afiliado para a Amazon. Sem área logada. Você edita
os produtos manualmente em `data/products.json`.

```
garimpo-mvp/
├── index.html
├── assets/
│   ├── style.css
│   └── app.js
├── data/
│   └── products.json   ← você edita este arquivo para incluir ofertas
└── README.md
```

## 1. Deploy no Cloudflare Pages (upload direto, sem git)

1. Acesse o dashboard do Cloudflare → **Workers & Pages** → **Create** → aba **Pages**.
2. Escolha **Upload assets** (é a opção "Upload your static files" que aparece no
   print que você mandou — ela existe na tela de criação de *Workers*, mas para
   um site estático puro use especificamente a aba **Pages**, não Workers).
3. Arraste a pasta `garimpo-mvp` inteira (ou o `.zip` anexado).
4. Cloudflare detecta que não há build step — ele só publica os arquivos como estão.
5. Pronto: você recebe uma URL tipo `garimpo-mvp.pages.dev`. Domínio próprio
   depois em **Custom domains**.

Se preferir deploy contínuo (recomendado assim que você começar a editar o
`products.json` com frequência): suba esta pasta para um repositório no GitHub
e conecte via **Continue with GitHub** na mesma tela — cada `git push` publica
uma nova versão automaticamente, sem passo de build.

## 2. Como adicionar/editar ofertas

Edite `data/products.json`. Cada objeto é um card:

| Campo | Obrigatório | Observação |
|---|---|---|
| `id` | sim | slug único, sem espaços |
| `title` | sim | título do produto |
| `category` | sim | `"promo"` ou `"cupom"` (controla as abas do topo) |
| `price` | sim | número, sem `R$` |
| `originalPrice` | não | se maior que `price`, calcula o `%` de desconto sozinho |
| `description` | sim | 1–2 linhas |
| `image` | sim | URL da imagem do produto (veja abaixo) |
| `store` | não | default `"Amazon"` |
| `affiliateLink` | sim | **precisa conter seu `?tag=SEUTAG-20`** |
| `postedAt` | sim | ISO 8601, usado para ordenar e calcular "há X min" |

**De onde tirar `image`:** na própria página do produto na Amazon, botão
direito na foto → *Copiar endereço da imagem* (normalmente um link
`m.media-amazon.com/images/...`). Não há automação nisso ainda — é manual
no MVP (ver seção 3).

Sem `id` duplicado, sem vírgula sobrando — é JSON puro, um erro de sintaxe
quebra o carregamento de todos os produtos (o `app.js` mostra um aviso no
console e no site se `products.json` falhar ao carregar).

## 3. Sobre o "cola o link e carrega foto/preço sozinho" (automação futura)

Isto é o ponto que precisa de uma correção de expectativa antes de virar
arquitetura: **não existe hoje uma forma simples e gratuita de pegar um link
de produto Amazon e puxar foto/descrição/preço automaticamente**, e a
situação piorou nos últimos meses. Resumo verificado agora (14/08/2026):

- A **Product Advertising API (PA-API) 5.0**, que era o caminho oficial,
  **foi descontinuada em 15/05/2026** e substituída pela **Creators API**.
- Para ter acesso à Creators API, a conta de Associado precisa de
  **10 vendas qualificadas nos últimos 30 dias corridos** (antes eram 3).
  Ou seja: é uma API pensada para quem já vende pelo site, não para
  bootstrapar um catálogo do zero. Sem essas vendas, a resposta da API é
  `AssociateNotEligible`.
- **Scraping direto da página da Amazon** (parsear o HTML de
  `amazon.com.br/dp/...` no seu Worker) funciona tecnicamente, mas viola os
  Termos de Uso do Amazon Associates Program e esbarra em bot-detection/CAPTCHA.
  Não vou implementar isso — é o tipo de coisa que derruba a conta de
  afiliado se for pega.
- **APIs de terceiros pagas** (ex.: Canopy API e similares) oferecem esse
  dado via key própria, cobrando por request, sem depender do seu volume de
  vendas. É a alternativa mais realista para automação antes de bater as
  10 vendas/mês — mas é custo recorrente e é uma dependência de terceiro
  fora do seu controle, então verifique os termos de uso e o SLA antes de
  se comprometer.

**Caminho honesto para o MVP → automação:**

1. Agora: cadastro manual em `products.json` (como está).
2. Quando o site gerar tráfego e você bater as 10 vendas/30 dias: pede
   acesso à Creators API e troca o passo manual por uma Cloudflare Function
   que consulta a API e escreve no JSON (ou num KV namespace).
3. Se quiser automação *antes* disso: avalie uma API paga de terceiro como
   ponte, sabendo que é custo e dependência externa — não é decisão técnica
   trivial, é decisão de custo/risco que só você pode bater o martelo.

Não incluí nenhum código de scraping ou de chamada à Creators API neste MVP
porque nenhum dos dois é o que você pediu agora — cadastro manual, deploy
simples. Quando você tiver 10 vendas/mês e quiser migrar, chame de novo que
implemento a Function.

## 4. Disclosure obrigatório

O `index.html` já traz o texto de divulgação exigido pelo Amazon Associates
Operating Agreement ("Como Associado Amazon, ganho com compras
qualificadas..."). Não remova — é condição do programa, não frescura de
design.

## 5. O que este MVP deliberadamente NÃO tem

- Login/cadastro de usuário.
- Backend, banco de dados, contagem de cliques.
- Comentários (o print de referência tinha; ficou fora do escopo que você
  pediu).
- Scraping ou API automática — ver seção 3.

Qualquer um desses é uma conversa separada quando você decidir que precisa.
