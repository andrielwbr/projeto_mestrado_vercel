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
    nivel: str  # 'iniciante' ou 'avancado'
    km: float
    tempo: float
    calorias: float
    esforco: int
    clima: str

# --- LÓGICA DE TREINADOR PROFISSIONAL ---
def gerar_prescricao(treino_atual, historico):
    # 1. Analisa Histórico (Carga Crônica)
    if not historico:
        # Se é o PRIMEIRO treino da vida no app
        if treino_atual.nivel == 'iniciante':
            return {
                "status": "🟢 INÍCIO DE JORNADA",
                "mensagem": "Bem-vindo! O segredo é a consistência.",
                "acao": "Descanso de 24h",
                "proximo_treino": "Caminhada/Corrida leve de 3km",
                "ratio": 0.0
            }
    
    # Cálculo ACWR (Razão Aguda:Crônica)
    carga_aguda = treino_atual.km
    for t in historico[:6]: carga_aguda += t.get('km_percorridos', 0)
    
    total_historico = sum(t.get('km_percorridos', 0) for t in historico)
    divisor = 4 if len(historico) > 4 else 1 # Evita distorção no começo
    carga_cronica = (total_historico + treino_atual.km) / divisor
    
    if carga_cronica == 0: carga_cronica = 1
    ratio = carga_aguda / carga_cronica

    # 2. Ajuste por Idade e Nível (Fatores de Segurança)
    fator_recuperacao = 1.0
    if treino_atual.idade > 45: fator_recuperacao = 1.2 # Precisa de 20% mais descanso
    if treino_atual.nivel == 'iniciante': fator_recuperacao += 0.1

    # 3. Tomada de Decisão (A Lógica do Treinador)
    
    # CENÁRIO A: Sobrecarga (Risco de Lesão)
    if ratio > (1.5 / fator_recuperacao):
        return {
            "status": "🔴 RISCO ELEVADO (Overreaching)",
            "mensagem": "Você aumentou o volume rápido demais para seu perfil.",
            "acao": "Descanso OBRIGATÓRIO de 48h a 72h.",
            "proximo_treino": "Apenas caminhada ou trote leve (Max 3km) para soltar.",
            "ratio": round(ratio, 2)
        }

    # CENÁRIO B: Zona Ideal de Evolução
    elif 0.8 <= ratio <= 1.3:
        # Regra dos 10% de progressão
        proximo_km = treino_atual.km * 1.1
        tipo = "Moderado" if treino_atual.nivel == 'avancado' else "Leve"
        
        return {
            "status": "🟢 ZONA DE EVOLUÇÃO",
            "mensagem": "Carga perfeita. Seu corpo está absorvendo bem o treino.",
            "acao": "Descanso de 24h ou Cross-training (Bike/Natação).",
            "proximo_treino": f"Correr {proximo_km:.1f} km - Ritmo {tipo}.",
            "ratio": round(ratio, 2)
        }

    # CENÁRIO C: Destreinamento (Carga Baixa)
    else:
        return {
            "status": "🟡 CARGA BAIXA (Manutenção)",
            "mensagem": "Volume baixo. Seguro, mas pouco estímulo para evoluir.",
            "acao": "Pode treinar amanhã se não houver dores.",
            "proximo_treino": f"Tente aumentar para {treino_atual.km * 1.2:.1f} km ou fazer Tiros Curtos.",
            "ratio": round(ratio, 2)
        }

@app.post("/registrar_treino")
def registrar_treino(dados: TreinoInput):
    try:
        # 1. Salvar no Supabase
        novo_registro = {
            "user_id": dados.user_id.lower(),
            "idade": dados.idade,
            "nivel_experiencia": dados.nivel,
            "km_percorridos": dados.km,
            "tempo_gasto": dados.tempo,
            "calorias": dados.calorias,
            "esforco_percebido": dados.esforco,
            "clima": dados.clima
        }
        supabase.table("treinos").insert(novo_registro).execute()

        # 2. Buscar Histórico do Usuário
        res = supabase.table("treinos")\
            .select("*")\
            .eq("user_id", dados.user_id.lower())\
            .order("data_hora", desc=True)\
            .limit(28)\
            .execute()
        
        historico = res.data if res.data else []

        # 3. Gerar Análise Profissional
        prescricao = gerar_prescricao(dados, historico)

        return {"message": "Salvo", "analise": prescricao}

    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))
