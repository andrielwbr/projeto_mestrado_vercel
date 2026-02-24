from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
from supabase import create_client, Client

app = FastAPI()

# --- CONEXÃO COM O BANCO ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url:
    url = "SUA_URL"
    key = "SUA_CHAVE"

supabase: Client = create_client(url, key)

# --- ESTRUTURA DE ENTRADA (Agora com a data do treino) ---
class TreinoInput(BaseModel):
    email: str  # <--- NOVO CAMPO OBRIGATÓRIO
    user_id: str
    data_treino: str
    tipo_atividade: str
    idade: int
    nivel: str 
    km: float
    tempo: float
    esforco: int
    clima: str

# --- O CÉREBRO DA IA ---
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
    dias_descanso = 1 # Padrão: 1 dia de descanso

    if ratio > limite_lesao:
        status = "🔴 ALTO RISCO (Descanse)"
        msg = f"Carga muito alta para {treino.tipo_atividade}. Risco de lesão."
        proximo_km = treino.km * 0.5 
        acao = "Descanso total ou alongamento."
        dias_descanso = 2 # Exige 48h de recuperação
    
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
        dias_descanso = 1 # Pode treinar logo a seguir

    # --- A MÁQUINA DO TEMPO (Cálculo da Data do Próximo Treino) ---
    # 1. Converter a string da data para matemática
    data_treino_obj = datetime.strptime(treino.data_treino, "%Y-%m-%d").date()
    
    # 2. Saber que dia é hoje
    hoje = (datetime.utcnow() - timedelta(hours=3)).date()
    
    # 3. Calcular quando o corpo estará recuperado
    data_recuperacao = data_treino_obj + timedelta(days=dias_descanso)
    
    # 4. Tradutor de dias da semana
    dias_semana = {0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira", 3: "quinta-feira", 4: "sexta-feira", 5: "sábado", 6: "domingo"}
    
    # 5. A Lógica Inteligente (Mostra a data futura ou "Hoje" se já passou)
    if data_recuperacao <= hoje:
        data_formatada = f"Hoje - {dias_semana[hoje.weekday()]}"
    else:
        data_formatada = f"{data_recuperacao.strftime('%d/%m')} - {dias_semana[data_recuperacao.weekday()]}"

    calorias_previstas = int(proximo_km * fator_calorico)
    
    # Injetamos a data perfeitamente formatada na recomendação
    texto_final = f"{data_formatada}: {verbo} {proximo_km:.1f} km (~{calorias_previstas} kcal)" if proximo_km > 0 else f"{data_formatada}: Recuperação total."

    return {
        "status": status,
        "mensagem": msg,
        "acao": acao,
        "proximo_treino": texto_final
    }

# --- A ROTA DE REGISTO NO BANCO ---
@app.post("/registrar_treino")
def registrar_treino(dados: TreinoInput):
    try:
        # --- TRAVA DE 1 TREINO POR DIA ---
        # Verifica se já existe um treino com esta data exata para este utilizador
        historico_completo = supabase.table("treinos").select("data_hora").eq("user_id", dados.user_id.lower()).execute()
        
        if historico_completo.data:
            for t in historico_completo.data:
                # O banco devolve a data assim "2026-02-21T...". Validamos se começa com a data inserida.
                if t['data_hora'] and t['data_hora'].startswith(dados.data_treino):
                    data_pt = f"{dados.data_treino[-2:]}/{dados.data_treino[5:7]}"
                    return {"erro": f"Já tem um registo no dia {data_pt}. Apenas é permitido 1 treino por dia!"}

        # -----------------------------------

        base_kcal = 50 if dados.tipo_atividade == "caminhada" else 70
        fator_esforco = 1 + ((dados.esforco - 5) * 0.05) 
        calorias_calculadas = round((dados.km * base_kcal) * fator_esforco)

        # Inserir no banco de dados, utilizando a data do calendário
        supabase.table("treinos").insert({
            "user_id": dados.user_id.lower(),
            "tipo_atividade": dados.tipo_atividade,
            "idade": dados.idade,
            "nivel_experiencia": dados.nivel,
            "km_percorridos": dados.km,
            "tempo_gasto": dados.tempo,
            "calorias": calorias_calculadas, 
            "esforco_percebido": dados.esforco,
            "clima": dados.clima,
            "data_hora": f"{dados.data_treino}T12:00:00Z" # Forçamos o meio-dia para evitar desvios de fuso horário
        }).execute()

        res = supabase.table("treinos").select("*").eq("user_id", dados.user_id.lower()).order("data_hora", desc=True).limit(28).execute()
        
        analise = gerar_prescricao(dados, res.data if res.data else [])

        return {"analise": analise}

    except Exception as e:
        print(f"Erro detalhado: {e}")
        raise HTTPException(status_code=500, detail=str(e))