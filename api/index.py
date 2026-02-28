from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # <--- SEGURANÇA: IMPORTAÇÃO
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
from supabase import create_client, Client

app = FastAPI()

# --- 🛡️ SEGURANÇA (CORS) ---
# Isso impede que sites falsos mandem dados para o seu banco
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # DICA: Quando o site estiver pronto, troque ["*"] pela sua URL da Vercel
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# --- CONEXÃO COM O BANCO ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url:
    url = "URL_FALSA"
    key = "KEY_FALSA"

supabase: Client = create_client(url, key)

# --- ESTRUTURAS DE DADOS ---
class TreinoInput(BaseModel):
    email: str
    user_id: str
    data_treino: str
    tipo_atividade: str
    idade: int
    nivel: str 
    km: float
    tempo: float
    esforco: int
    clima: str

class FeedbackInput(BaseModel): # <--- NOVA ESTRUTURA PARA A NOTA DA PROVA
    email: str
    data_treino: str
    feedback: str

# --- CÉREBRO DA IA ---
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
    if treino.idade > 45: limite_lesao -= 0.2 

    status = ""
    msg = ""
    proximo_km = 0
    dias_descanso = 1 

    if ratio > limite_lesao:
        status = "🔴 ALTO RISCO (Descanse)"
        msg = f"Carga muito alta para {treino.tipo_atividade}. Risco de lesão."
        proximo_km = treino.km * 0.5 
        acao = "Descanso total ou alongamento."
        dias_descanso = 2 
    elif 0.8 <= ratio <= limite_lesao:
        status = "🟢 ZONA IDEAL (Evoluindo)"
        msg = f"Treino perfeito de {treino.tipo_atividade}."
        proximo_km = treino.km * 1.1 
        acao = "Descanso padrão de 24h."
        dias_descanso = 1
    else:
        status = "🟡 CARGA BAIXA (Manutenção)"
        msg = "Treino leve. Corpo nem sentiu."
        proximo_km = treino.km * 1.2 
        acao = "Pode treinar amanhã se quiser."
        dias_descanso = 1 

    data_treino_obj = datetime.strptime(treino.data_treino, "%Y-%m-%d").date()
    hoje = (datetime.utcnow() - timedelta(hours=3)).date()
    data_recuperacao = data_treino_obj + timedelta(days=dias_descanso)
    
    dias_semana = {0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira", 3: "quinta-feira", 4: "sexta-feira", 5: "sábado", 6: "domingo"}
    
    if data_recuperacao <= hoje:
        data_formatada = f"Hoje - {dias_semana[hoje.weekday()]}"
    else:
        data_formatada = f"{data_recuperacao.strftime('%d/%m')} - {dias_semana[data_recuperacao.weekday()]}"

    calorias_previstas = int(proximo_km * fator_calorico)
    texto_final = f"{data_formatada}: {verbo} {proximo_km:.1f} km (~{calorias_previstas} kcal)" if proximo_km > 0 else f"{data_formatada}: Recuperação total."

    return {
        "status": status,
        "mensagem": msg,
        "acao": acao,
        "proximo_treino": texto_final
    }

# --- ROTA 1: REGISTRAR O TREINO ---
@app.post("/registrar_treino")
def registrar_treino(dados: TreinoInput):
    try:
        historico_completo = supabase.table("treinos").select("data_hora").eq("email", dados.email).execute()
        if historico_completo.data:
            for t in historico_completo.data:
                if t['data_hora'] and t['data_hora'].startswith(dados.data_treino):
                    data_pt = f"{dados.data_treino[-2:]}/{dados.data_treino[5:7]}"
                    return {"erro": f"Já existe um treino registrado nesta data ({data_pt}) para este e-mail!"}

        base_kcal = 50 if dados.tipo_atividade == "caminhada" else 70
        fator_esforco = 1 + ((dados.esforco - 5) * 0.05) 
        calorias_calculadas = round((dados.km * base_kcal) * fator_esforco)

        supabase.table("treinos").insert({
            "email": dados.email,
            "user_id": dados.user_id,      
            "tipo_atividade": dados.tipo_atividade,
            "idade": dados.idade,
            "nivel_experiencia": dados.nivel,
            "km_percorridos": dados.km,
            "tempo_gasto": dados.tempo,
            "calorias": calorias_calculadas,
            "esforco_percebido": dados.esforco,
            "clima": dados.clima,
            "data_hora": f"{dados.data_treino}T12:00:00Z"
        }).execute()

        res = supabase.table("treinos").select("*").eq("email", dados.email).order("data_hora", desc=True).limit(28).execute()
        analise = gerar_prescricao(dados, res.data if res.data else [])
        return {"analise": analise}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ROTA 2: REGISTRAR O FEEDBACK (A NOTA DA PROVA) ---
@app.post("/registrar_feedback")
def registrar_feedback(dados: FeedbackInput):
    try:
        # 1. Acha qual é o ID do treino de hoje
        registros = supabase.table("treinos").select("id, data_hora").eq("email", dados.email).execute()
        treino_id = None
        
        if registros.data:
            for t in registros.data:
                if t['data_hora'] and t['data_hora'].startswith(dados.data_treino):
                    treino_id = t['id']
                    break
                    
        if not treino_id:
            return {"erro": "Treino não encontrado."}

        # 2. Atualiza a coluna de feedback
        supabase.table("treinos").update({"feedback_treino": dados.feedback}).eq("id", treino_id).execute()
        return {"sucesso": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))