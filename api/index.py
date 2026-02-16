from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from supabase import create_client, Client

app = FastAPI()

# --- CONFIGURAÇÃO ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class TreinoInput(BaseModel):
    user_id: str
    idade: int
    nivel: str 
    km: float
    tempo: float
    calorias: float
    esforco: int
    clima: str

# --- LÓGICA DO TREINADOR (ACWR + CALORIAS) ---
def gerar_prescricao(treino_atual, historico):
    fator_calorico = 70 # Padrão médio
    if treino_atual.km > 0 and treino_atual.calorias > 0:
        fator_calorico = treino_atual.calorias / treino_atual.km

    carga_aguda = treino_atual.km
    for t in historico[:6]: carga_aguda += t.get('km_percorridos', 0)
    
    total_historico = sum(t.get('km_percorridos', 0) for t in historico)
    divisor = 4 if len(historico) > 4 else 1 
    carga_cronica = (total_historico + treino_atual.km) / divisor
    
    if carga_cronica == 0: carga_cronica = 1
    ratio = carga_aguda / carga_cronica

    # Ajustes de Segurança
    fator_recuperacao = 1.2 if treino_atual.idade > 45 else 1.0
    if treino_atual.nivel == 'iniciante': fator_recuperacao += 0.1

    if ratio > (1.5 / fator_recuperacao):
        km_seguro = 3.0
        cal_prev = int(km_seguro * (fator_calorico * 0.8))
        return {
            "status": "🔴 RISCO ELEVADO",
            "mensagem": "Volume muito alto para seu histórico recente.",
            "acao": "Descanso OBRIGATÓRIO de 48h.",
            "proximo_treino": f"Caminhada leve de {km_seguro}km (~{cal_prev} kcal)",
            "ratio": round(ratio, 2)
        }
    elif 0.8 <= ratio <= 1.3:
        proximo_km = treino_atual.km * 1.1
        cal_prev = int(proximo_km * fator_calorico)
        return {
            "status": "🟢 ZONA IDEAL",
            "mensagem": "Excelente evolução. Carga controlada.",
            "acao": "Descanso de 24h.",
            "proximo_treino": f"Correr {proximo_km:.1f} km (~{cal_prev} kcal).",
            "ratio": round(ratio, 2)
        }
    else:
        proximo_km = treino_atual.km * 1.2
        cal_prev = int(proximo_km * fator_calorico)
        return {
            "status": "🟡 CARGA BAIXA",
            "mensagem": "Volume abaixo da sua capacidade atual.",
            "acao": "Pode treinar amanhã.",
            "proximo_treino": f"Subir para {proximo_km:.1f} km (~{cal_prev} kcal).",
            "ratio": round(ratio, 2)
        }

@app.post("/registrar_treino")
def registrar_treino(dados: TreinoInput):
    try:
        supabase.table("treinos").insert({
            "user_id": dados.user_id.lower(),
            "idade": dados.idade,
            "nivel_experiencia": dados.nivel,
            "km_percorridos": dados.km,
            "tempo_gasto": dados.tempo,
            "calorias": dados.calorias,
            "esforco_percebido": dados.esforco,
            "clima": dados.clima
        }).execute()

        res = supabase.table("treinos").select("*").eq("user_id", dados.user_id.lower()).order("data_hora", desc=True).limit(28).execute()
        
        return {"analise": gerar_prescricao(dados, res.data if res.data else [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
