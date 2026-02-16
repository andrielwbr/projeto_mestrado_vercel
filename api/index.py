from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from supabase import create_client, Client
from datetime import datetime, timedelta
import math

app = FastAPI()

# --- CONFIGURAÇÃO ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class Treino(BaseModel):
    km: float
    tempo: float
    calorias: float
    esforco: int
    clima: str

# --- INTELIGÊNCIA ARTIFICIAL (Lógica ACWR) ---
def calcular_risco_lesao(novo_treino, historico):
    """
    Calcula o risco baseado na Razão Aguda:Crônica (ACWR).
    Se você aumentar o volume muito rápido (> 1.5x), o risco explode.
    """
    # 1. Adiciona o treino atual ao histórico para cálculo
    historico_recente = [t for t in historico] # Copia lista
    
    # 2. Calcula Carga Aguda (Últimos 7 dias - Fadiga)
    # Consideramos o treino de hoje + passados
    carga_aguda = novo_treino.km
    for t in historico_recente[:6]: # Pega até 6 treinos anteriores
        carga_aguda += t.get('km_percorridos', 0)

    # 3. Calcula Carga Crônica (Média das últimas 4 semanas - Condicionamento)
    # Se tiver pouco histórico, assumimos uma base mínima para não dividir por zero
    total_historico = sum(t.get('km_percorridos', 0) for t in historico_recente)
    carga_cronica = (total_historico + novo_treino.km) / 4 
    
    if carga_cronica == 0: carga_cronica = 1 # Evitar divisão por zero

    ratio = carga_aguda / carga_cronica

    # 4. Definição do Risco e Sugestão
    if ratio > 1.5:
        status = "🔴 ALTO RISCO"
        msg = "Cuidado! Você aumentou o volume muito rápido."
        sugestao = f"Descanse 2 dias ou faça no máximo {novo_treino.km * 0.5:.1f} km leve."
    elif ratio > 1.2:
        status = "🟡 MODERADO"
        msg = "Zona de atenção. Seu corpo está sentindo a carga."
        sugestao = f"Mantenha o volume. Próximo treino: {novo_treino.km:.1f} km."
    elif ratio < 0.8:
        status = "🟢 BAIXO (Destreinando)"
        msg = "Você está treinando menos do que aguenta."
        sugestao = f"Pode aumentar. Tente {novo_treino.km * 1.1:.1f} km na próxima."
    else:
        status = "🟢 ZONA IDEAL"
        msg = "Evolução perfeita! Risco de lesão baixo."
        sugestao = f"Continue assim. Próximo alvo: {novo_treino.km * 1.05:.1f} km."

    return {
        "status": status,
        "mensagem": msg,
        "ratio": round(ratio, 2),
        "sugerido_proximo": sugestao,
        "acumulado_semana": round(carga_aguda, 1)
    }

# --- ROTA PRINCIPAL ---
@app.post("/registrar_treino")
def registrar_treino(treino: Treino):
    if not url or not key:
        raise HTTPException(status_code=500, detail="Erro de Configuração no Servidor")

    try:
        # 1. Salvar no Banco
        dados_novos = {
            "km_percorridos": treino.km,
            "tempo_gasto": treino.tempo,
            "calorias": treino.calorias,
            "esforco_percebido": treino.esforco,
            "clima": treino.clima
        }
        res_insert = supabase.table("treinos").insert(dados_novos).execute()

        # 2. Buscar Histórico para Análise (Últimos 28 registros)
        res_history = supabase.table("treinos")\
            .select("km_percorridos, data_hora")\
            .order("data_hora", desc=True)\
            .limit(28)\
            .execute()
        
        historico = res_history.data if res_history.data else []

        # 3. Rodar a IA
        analise = calcular_risco_lesao(treino, historico)

        return {
            "message": "Treino salvo!",
            "analise": analise
        }

    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))
