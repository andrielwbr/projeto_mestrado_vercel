from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from supabase import create_client, Client

app = FastAPI()

# --- CONEXÃO COM O BANCO ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class TreinoInput(BaseModel):
    user_id: str
    tipo_atividade: str = "corrida"
    idade: int
    nivel: str 
    km: float
    tempo: float
    esforco: int
    clima: str
    # Removemos as 'calorias' daqui

# --- CÉREBRO DA IA (Com Cálculo de Calorias) ---
def gerar_prescricao(treino, historico):
    # 1. Descobre quantas calorias você gasta por KM (Eficiência)
    fator_calorico = 70 # Média padrão humana
    if treino.km > 0 and treino.calorias > 0:
        fator_calorico = treino.calorias / treino.km

    # 2. Cálculo de Carga (ACWR)
    carga_aguda = treino.km
    for t in historico[:6]: carga_aguda += t.get('km_percorridos', 0)
    
    total_historico = sum(t.get('km_percorridos', 0) for t in historico)
    divisor = 4 if len(historico) > 4 else 1 
    carga_cronica = (total_historico + treino.km) / divisor
    
    if carga_cronica == 0: carga_cronica = 1
    ratio = carga_aguda / carga_cronica

    # 3. Definição do Próximo Treino
    # Ajuste para idade
    limite = 1.5 if treino.idade < 45 else 1.3
    
    status = ""
    msg = ""
    proximo_km = 0

    if ratio > limite:
        status = "🔴 ALTO RISCO (Descanse)"
        msg = "Carga muito alta. Risco de lesão iminente."
        proximo_km = 0 # Descanso
        acao = "Descanso total de 48h."
    
    elif 0.8 <= ratio <= limite:
        status = "🟢 ZONA IDEAL (Evoluindo)"
        msg = "Treino perfeito. Seu corpo aceitou bem a carga."
        proximo_km = treino.km * 1.1 # Aumenta 10%
        acao = "Descanso de 24h."

    else:
        status = "🟡 CARGA BAIXA (Manutenção)"
        msg = "Treino leve. Pouco estímulo para evoluir."
        proximo_km = treino.km * 1.2 # Pode aumentar 20%
        acao = "Pode treinar amanhã."

    # 4. CÁLCULO FINAL DAS CALORIAS PREVISTAS
    # Se for descanso, caloria é 0. Se for treino, calcula baseada na sua eficiência.
    calorias_previstas = int(proximo_km * fator_calorico)
    
    if proximo_km > 0:
        texto_final = f"Correr {proximo_km:.1f} km (Gasto est: ~{calorias_previstas} kcal)"
    else:
        texto_final = "Apenas caminhada leve ou alongamento (Recuperação)"

    return {
        "status": status,
        "mensagem": msg,
        "acao": acao,
        "proximo_treino": texto_final # AQUI ESTÁ A MÁGICA
    }

@app.post("/registrar_treino")
def registrar_treino(dados: TreinoInput):
    try:
        # --- NOVO: CÁLCULO DE CALORIAS AUTOMÁTICO ---
        # Caminhada gasta ~50 kcal por km, Corrida ~70 kcal.
        base_kcal = 50 if dados.tipo_atividade == "caminhada" else 70
        
        # Ajuste de Esforço: Se o cara fez esforço 10, queima mais. Esforço 1, queima menos.
        fator_esforco = 1 + ((dados.esforco - 5) * 0.05) 
        calorias_finais = round((dados.km * base_kcal) * fator_esforco)
        # ---------------------------------------------

        # Salva no banco de dados com a caloria calculada pelo sistema
        supabase.table("treinos").insert({
            "user_id": dados.user_id.lower(),
            "idade": dados.idade,
            "nivel_experiencia": dados.nivel,
            "km_percorridos": dados.km,
            "tempo_gasto": dados.tempo,
            "calorias": calorias_finais, # AQUI ENTRA O CÁLCULO MÁGICO
            "esforco_percebido": dados.esforco,
            "clima": dados.clima
        }).execute()

        # ... (restante do código igual)

        # Busca Histórico
        res = supabase.table("treinos").select("*").eq("user_id", dados.user_id.lower()).order("data_hora", desc=True).limit(28).execute()
        
        # Analisa
        analise = gerar_prescricao(dados, res.data if res.data else [])

        return {"analise": analise}

    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))
