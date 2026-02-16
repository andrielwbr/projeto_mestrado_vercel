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

# --- CÉREBRO DA IA (Com Estimativa de Calorias) ---
def gerar_prescricao(treino_atual, historico):
    # 1. Calcula a Eficiência Metabólica do Usuário (Kcal por KM)
    # Se o usuário não informou calorias, usamos 70kcal/km como padrão média
    fator_calorico = 70 
    if treino_atual.km > 0 and treino_atual.calorias > 0:
        fator_calorico = treino_atual.calorias / treino_atual.km

    # 2. Analisa Histórico (Carga Crônica)
    if not historico:
        if treino_atual.nivel == 'iniciante':
            # Previsão para treino de 3km
            calorias_previstas = int(3.0 * fator_calorico)
            return {
                "status": "🟢 INÍCIO DE JORNADA",
                "mensagem": "Bem-vindo! O segredo é a consistência.",
                "acao": "Descanso de 24h",
                "proximo_treino": f"Caminhada/Corrida leve de 3km (~{calorias_previstas} kcal)",
                "ratio": 0.0
            }
    
    # Cálculo ACWR
    carga_aguda = treino_atual.km
    for t in historico[:6]: carga_aguda += t.get('km_percorridos', 0)
    
    total_historico = sum(t.get('km_percorridos', 0) for t in historico)
    divisor = 4 if len(historico) > 4 else 1 
    carga_cronica = (total_historico + treino_atual.km) / divisor
    
    if carga_cronica == 0: carga_cronica = 1
    ratio = carga_aguda / carga_cronica

    # 3. Ajuste por Idade e Nível
    fator_recuperacao = 1.0
    if treino_atual.idade > 45: fator_recuperacao = 1.2
    if treino_atual.nivel == 'iniciante': fator_recuperacao += 0.1

    # 4. Tomada de Decisão & Previsão de Calorias
    
    # CENÁRIO A: Sobrecarga
    if ratio > (1.5 / fator_recuperacao):
        km_seguro = 3.0
        calorias_previstas = int(km_seguro * (fator_calorico * 0.8)) # Gasta menos andando
        return {
            "status": "🔴 RISCO ELEVADO (Overreaching)",
            "mensagem": "Volume aumentou muito rápido. Risco de lesão.",
            "acao": "Descanso OBRIGATÓRIO de 48h.",
            "proximo_treino": f"Caminhada regenerativa de {km_seguro}km (~{calorias_previstas} kcal)",
            "ratio": round(ratio, 2)
        }

    # CENÁRIO B: Zona Ideal
    elif 0.8 <= ratio <= 1.3:
        proximo_km = treino_atual.km * 1.1
        calorias_previstas = int(proximo_km * fator_calorico)
        tipo = "Moderado" if treino_atual.nivel == 'avancado' else "Leve"
        
        return {
            "status": "🟢 ZONA DE EVOLUÇÃO",
            "mensagem": "Carga perfeita. Evolução segura.",
            "acao": "Descanso de 24h ou Cross-training.",
            "proximo_treino": f"Correr {proximo_km:.1f} km (~{calorias_previstas} kcal) - Ritmo {tipo}.",
            "ratio": round(ratio, 2)
        }

    # CENÁRIO C: Destreinamento
    else:
        proximo_km = treino_atual.km * 1.2
        calorias_previstas = int(proximo_km * fator_calorico)
        return {
            "status": "🟡 CARGA BAIXA (Manutenção)",
            "mensagem": "Volume baixo. Pouco estímulo para evoluir.",
            "acao": "Treinar amanhã se estiver sem dor.",
            "proximo_treino": f"Aumentar para {proximo_km:.1f} km (~{calorias_previstas} kcal) na próxima.",
            "ratio": round(ratio, 2)
        }

@app.post("/registrar_treino")
def registrar_treino(dados: TreinoInput):
    try:
        # Salva no Supabase
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

        # Busca Histórico
        res = supabase.table("treinos")\
            .select("*")\
            .eq("user_id", dados.user_id.lower())\
            .order("data_hora", desc=True)\
            .limit(28)\
            .execute()
        
        historico = res.data if res.data else []

        # Gera Análise
        prescricao = gerar_prescricao(dados, historico)

        return {"message": "Salvo", "analise": prescricao}

    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))
