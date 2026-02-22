from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from supabase import create_client, Client

app = FastAPI()

# --- CONEXÃO COM O BANCO ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Truque para rodar local se precisar
if not url:
    url = "https://iqdllutxyqfgqfafxrrv.supabase.co"
    key = "SUA_CHAVE_AQUI" # (Se for rodar no PC, coloque sua chave. Na Vercel não precisa)

supabase: Client = create_client(url, key)

# --- 1. A NOVA ESTRUTURA DE ENTRADA (Sem as calorias) ---
class TreinoInput(BaseModel):
    user_id: str
    tipo_atividade: str  # Novo campo que criamos no HTML
    idade: int
    nivel: str 
    km: float
    tempo: float
    esforco: int
    clima: str

# --- 2. O CÉREBRO DA IA (Com Caminhada e Corrida) ---
def gerar_prescricao(treino, historico):
    if treino.tipo_atividade == "caminhada":
        fator_calorico = 50  
        limite_lesao = 2.0  
        verbo = "Caminhar"
    else:
        fator_calorico = 70  
        limite_lesao = 1.5  
        verbo = "Correr"

    carga_aguda = treino.km
    total_historico = sum(t.get('km_percorridos', 0) for t in historico)
    divisor = 4 if len(historico) > 4 else 1 
    
    carga_cronica = (total_historico + treino.km) / divisor if total_historico > 0 else treino.km
    if carga_cronica == 0: carga_cronica = 1
    
    ratio = carga_aguda / carga_cronica

    # Ajuste de idade
    if treino.idade > 45:
        limite_lesao -= 0.2 

    status = ""
    msg = ""
    proximo_km = 0

    if ratio > limite_lesao:
        status = "🔴 ALTO RISCO (Descanse)"
        msg = f"Carga muito alta para {treino.tipo_atividade}. Risco de lesão."
        proximo_km = treino.km * 0.5 
        acao = "Descanso total ou alongamento."
    
    elif 0.8 <= ratio <= limite_lesao:
        status = "🟢 ZONA IDEAL (Evoluindo)"
        msg = f"Treino perfeito de {treino.tipo_atividade}."
        proximo_km = treino.km * 1.1 
        acao = "Descanso padrão de 24h."

    else:
        status = "🟡 CARGA BAIXA (Manutenção)"
        msg = "Treino leve. Corpo nem sentiu."
        proximo_km = treino.km * 1.2 
        acao = "Pode treinar amanhã se quiser."

    # Calcula calorias da meta futura
    calorias_previstas = int(proximo_km * fator_calorico)
    texto_final = f"{verbo} {proximo_km:.1f} km (~{calorias_previstas} kcal)" if proximo_km > 0 else "Recuperação total."

    return {
        "status": status,
        "mensagem": msg,
        "acao": acao,
        "proximo_treino": texto_final
    }

# --- 3. A ROTA DE SALVAR NO BANCO ---
@app.post("/registrar_treino")
def registrar_treino(dados: TreinoInput):
    try:
        # A) IA Calcula as Calorias do treino atual
        base_kcal = 50 if dados.tipo_atividade == "caminhada" else 70
        fator_esforco = 1 + ((dados.esforco - 5) * 0.05) 
        calorias_calculadas = round((dados.km * base_kcal) * fator_esforco)

        # B) Salva na nova tabela do Supabase
        supabase.table("treinos").insert({
            "user_id": dados.user_id.lower(),
            "tipo_atividade": dados.tipo_atividade,
            "idade": dados.idade,
            "nivel_experiencia": dados.nivel,
            "km_percorridos": dados.km,
            "tempo_gasto": dados.tempo,
            "calorias": calorias_calculadas, # O Python manda o cálculo
            "esforco_percebido": dados.esforco,
            "clima": dados.clima
        }).execute()

        # C) Busca o histórico e gera a análise
        res = supabase.table("treinos").select("*").eq("user_id", dados.user_id.lower()).order("data_hora", desc=True).limit(28).execute()
        
        analise = gerar_prescricao(dados, res.data if res.data else [])

        return {"analise": analise}

    except Exception as e:
        print(f"Erro detalhado no Python: {e}") # Isso ajuda a debugar depois
        raise HTTPException(status_code=500, detail=str(e))
