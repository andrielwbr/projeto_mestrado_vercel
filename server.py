from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # <--- Importante
from fastapi.responses import FileResponse  # <--- Importante
from pydantic import BaseModel
import pandas as pd
from sklearn.linear_model import LogisticRegression
import os

app = FastAPI()

# --- Configuração CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAÇÃO DO SITE ---
# 1. Diz onde está a pasta "static"
app.mount("/static", StaticFiles(directory="static"), name="static")

ARQUIVO_DADOS = 'dados_corridas_diarias.csv'
API_KEY_SECRETA = "mestrado_andriel_2026"

class TreinoInput(BaseModel):
    km_treino: float
    intensidade: int
    horas_sono: float
    sentiu_dor: int 

async def verificar_token(x_token: str = Header(...)):
    if x_token != API_KEY_SECRETA:
        raise HTTPException(status_code=400, detail="Token inválido")

# --- ROTA PRINCIPAL (Onde o erro estava) ---
# Quando acessar http://192.168... entrega o index.html automaticamente
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.post("/registrar_treino")
async def registrar_treino(treino: TreinoInput, token: str = Depends(verificar_token)):
    # 1. Carregar CSV
    if os.path.exists(ARQUIVO_DADOS):
        df = pd.read_csv(ARQUIVO_DADOS)
    else:
        df = pd.DataFrame(columns=['km_treino', 'intensidade', 'horas_sono', 'sentiu_dor'])

    # 2. Salvar novo dado
    novo_dado = pd.DataFrame([treino.dict()])
    df = pd.concat([df, novo_dado], ignore_index=True)
    df.to_csv(ARQUIVO_DADOS, index=False)

    # 3. Lógica da IA (simplificada para evitar erros se tiver poucos dados)
    if len(df) < 5 or len(df['sentiu_dor'].unique()) < 2:
        return {
            "mensagem": "Treino Salvo! (IA coletando dados...)",
            "acumulado_semana": 0, "sugerido_proximo": 0
        }

    # Calcular acumulado
    df['acumulado_semana'] = df['km_treino'].rolling(window=7, min_periods=1).sum().fillna(0)
    
    # Treinar
    X = df[['acumulado_semana', 'intensidade', 'horas_sono']]
    y = df['sentiu_dor']
    modelo = LogisticRegression()
    modelo.fit(X, y)

    # Prever Futuro
    acumulado_hoje = df.iloc[-1]['acumulado_semana']
    distancia_segura = 0
    
    for km_teste in range(1, 40):
        entrada_teste = pd.DataFrame([[acumulado_hoje + km_teste, 7, 7]], 
                                     columns=['acumulado_semana', 'intensidade', 'horas_sono'])
        risco = modelo.predict_proba(entrada_teste)[0][1] * 100
        if risco > 45:
            break
        distancia_segura = km_teste

    return {
        "mensagem": "Análise Concluída",
        "acumulado_semana": float(round(acumulado_hoje, 1)),
        "sugerido_proximo": int(distancia_segura)
    }
