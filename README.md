# NHL Draft ML Project

## Objetivo
Prever se um jogador draftado na NHL terá uma carreira com mais de 100 jogos, utilizando apenas dados pré-draft.

## Tipo de problema
Classificação binária com Random Forest.

## Dataset
Dados de jogadores draftados na NHL entre 2015 e 2025, contendo estatísticas pré-draft como liga amadora, pontos por jogo, temporadas antes da NHL e minutos de penalidade.

Fonte: [Elite Prospects](https://www.eliteprospects.com/) — coletados via web scraping com o script `scripts/scraper_nhl_predraft.py`.

## Target
- 1 = jogador com mais de 100 jogos na NHL
- 0 = jogador com 100 jogos ou menos

## Features utilizadas
- `amateur_league` — liga amadora do jogador (categórica)
- `seasons_pre_nhl` — temporadas jogadas antes da NHL
- `points_per_game` — pontos por jogo no pré-draft
- `penalty_minutes` — minutos de penalidade no pré-draft

## Modelo
- Random Forest Classifier com threshold de 0.3
- Pré-processamento com OneHotEncoder para variáveis categóricas

## Estrutura do projeto
```
nhl-ml-project/
├── data/
│   ├── nhl_draft_predraft_stats.csv   # Dados originais
│   └── nhl_draft_clean.csv            # Dados limpos (sem goleiros e sem nulos)
├── notebooks/
│   ├── clean.ipynb                    # Limpeza dos dados
│   ├── final_model.ipynb              # Modelo final treinado com toda a base
│   ├── final_tests.ipynb              # Testes com threshold e análise de erros
│   └── training.ipynb                 # Treino e avaliação inicial
├── output/
│   └── nhl_predictions.csv            # Saída final com previsões
├── scripts/
│   └── scraper_nhl_predraft.py        # Script de coleta dos dados
├── .gitignore
├── README.md
└── requirements.txt
```

## Como rodar
1. Crie um ambiente virtual e instale as dependências:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
2. Execute os notebooks na ordem: `clean.ipynb` → `training.ipynb` → `final_tests.ipynb` → `final_model.ipynb`