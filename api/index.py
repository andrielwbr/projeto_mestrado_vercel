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
    url = "URL_FALSA"
    key = "KEY_FALSA"

supabase: Client = create_client(url, key)

# --- ESTRUTURAS DE DADOS ---
class TreinoInput(BaseModel):
    email: str
    user_id: str
    data_treino: str
    tipo_atividade: str
    idade: str      # 👈 A CORREÇÃO: Mudamos de 'int' para 'str' para aceitar "25-29"
    sexo: str    
    nivel: str 
    km: float
    tempo: float
    esforco: int


class FeedbackInput(BaseModel):
    email: str
    data_treino: str
    feedback: str

# --- CÉREBRO DA IA (Intacto) ---
# --- CÉREBRO DA IA (Intacto) ---
# --- CÉREBRO DA IA (Atualizado e Seguro) ---
def gerar_prescricao(treino, historico):
    # 1. DEFINIÇÃO DE PERFIS BIOFÍSICOS (Diferenciando Caminhada vs Corrida)
    if treino.tipo_atividade == "caminhada":
        fator_calorico = 50  
        limite_lesao = 2.2      # Caminhantes suportam um Ratio maior (baixo impacto)
        trava_volume_alto = 15.0 # O alerta de perigo na caminhada só começa nos 15km
        verbo = "Caminhar"
    else: # Corrida
        fator_calorico = 70  
        limite_lesao = 1.5      
        trava_volume_alto = 10.0 # O alerta de perigo na corrida começa nos 10km
        verbo = "Correr"

    carga_aguda = treino.km
    total_historico = sum(t.get('km_percorridos', 0) for t in historico)
    divisor = 4 if len(historico) > 4 else 1 
    
    carga_cronica = (total_historico + treino.km) / divisor if total_historico > 0 else treino.km
    if carga_cronica == 0: carga_cronica = 1
    
    ratio = carga_aguda / carga_cronica

    # 2. AJUSTE PARA VETERANOS (Sêniors)
    is_senior = treino.idade in ["45-49", "50-54", "55-59", "60+"]
    if is_senior: 
        limite_lesao -= 0.2  
        trava_volume_alto *= 0.8 # Reduz o teto de volume seguro em 20% para proteger as articulações

    status = ""
    msg = ""
    proximo_km = 0
    dias_descanso = 1 

    # =================================================================
    # A NOVA ÁRVORE DE DECISÃO INTELIGENTE
    # =================================================================
    
    # 1. Trava de Segurança por Volume ou Esforço Alto
    if treino.km >= trava_volume_alto or treino.esforco >= 7:
        status = "🟡 RECUPERAÇÃO OBRIGATÓRIA"
        tipo_msg = "impacto articular" if treino.tipo_atividade == "corrida" else "desgaste sistêmico"
        msg = f"Treino forte ({treino.km}km - Esforço {treino.esforco}/10). Risco de {tipo_msg}."
        # Regenerativo de 30%, travado num máximo de 5km
        proximo_km = min(treino.km * 0.3, 5.0) 
        acao = "Repouso absoluto ou atividade muito leve sem impacto para soltar a musculatura."
        dias_descanso = 2 if treino.km >= (trava_volume_alto * 1.5) else 1
        
    # 2. Trava de Risco pelo Histórico (Pico de Carga)
    elif ratio > limite_lesao:
        status = "🔴 ALTO RISCO (Pico de Carga)"
        msg = f"Aumento muito brusco comparado à sua média recente de {treino.tipo_atividade}."
        proximo_km = treino.km * 0.5 
        acao = "Reduza drasticamente o volume no próximo treino para evitar lesões."
        dias_descanso = 2 
        
    # 3. A Zona Ideal de Evolução
    elif 0.8 <= ratio <= limite_lesao:
        status = "🟢 ZONA IDEAL (Evoluindo)"
        msg = f"Carga excelente e segura para o seu condicionamento atual."
        # Caminhada permite evoluir um pouco mais rápido que corrida
        fator_progresso = 1.15 if treino.tipo_atividade == "caminhada" else 1.1 
        proximo_km = treino.km * fator_progresso 
        acao = "Mantenha a consistência. O corpo está a adaptar-se bem."
        dias_descanso = 1
        
    # 4. Treinos Base (Abaixo do perigo e Esforço Leve)
    else:
        status = "🟢 CARGA DE MANUTENÇÃO"
        msg = f"Treino base (Esforço {treino.esforco}/10). Ótimo para resistência."
        fator_progresso = 1.2 if treino.tipo_atividade == "caminhada" else 1.15
        proximo_km = treino.km * fator_progresso
        acao = "Pronto para o próximo. Pode tentar aumentar levemente a distância."
        dias_descanso = 1 
    # =================================================================

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

@app.post("/registrar_treino")
def registrar_treino(dados: TreinoInput):
    try:
        # MUDANÇA FUNCIONAL: Trava de 7 dias, 50km e 5h. Garante que a IA não receba dados absurdos.
        data_treino_obj = datetime.strptime(dados.data_treino, "%Y-%m-%d").date()
        hoje = datetime.utcnow().date()
        diferenca_dias = (hoje - data_treino_obj).days
        
        if diferenca_dias < 0 or diferenca_dias > 7:
            return {"erro": "O treino deve ser de hoje ou de até 7 dias atrás."}
        if dados.km <= 0 or dados.km > 50:
            return {"erro": "A distância limite para registo é de 50 km."}
        if dados.tempo <= 0 or dados.tempo > 300:
            return {"erro": "O tempo limite para registo é de 300 minutos (5 horas)."}

        historico_completo = supabase.table("treinos").select("data_hora").eq("email", dados.email).execute()
        if historico_completo.data:
            for t in historico_completo.data:
                if t['data_hora'] and t['data_hora'].startswith(dados.data_treino):
                    data_pt = f"{dados.data_treino[-2:]}/{dados.data_treino[5:7]}"
                    return {"erro": f"Já existe um treino registado nesta data ({data_pt}) para este e-mail!"}

        base_kcal = 50 if dados.tipo_atividade == "caminhada" else 70
        fator_esforco = 1 + ((dados.esforco - 5) * 0.05) 
        calorias_calculadas = round((dados.km * base_kcal) * fator_esforco)

        supabase.table("treinos").insert({
            "email": dados.email,
            "user_id": dados.user_id,      
            "tipo_atividade": dados.tipo_atividade,
            "idade": dados.idade,
            "sexo": dados.sexo,    # <--- ADICIONE ESTA LINHA COM A VÍRGULA
            "nivel_experiencia": dados.nivel,
            "km_percorridos": dados.km,
            "tempo_gasto": dados.tempo,
            "calorias": calorias_calculadas,
            "esforco_percebido": dados.esforco,
            # MUDANÇA FUNCIONAL: O campo 'clima' foi apagado daqui.
            "data_hora": f"{dados.data_treino}T12:00:00Z"
        }).execute()

        res = supabase.table("treinos").select("*").eq("email", dados.email).order("data_hora", desc=True).limit(28).execute()
        analise = gerar_prescricao(dados, res.data if res.data else [])
        return {"analise": analise}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- MUDANÇA FUNCIONAL: Rota do Feedback colocada no final ---
# Função para atualizar o banco de dados com a nota de esforço real do utilizador.
@app.post("/registrar_feedback")
def registrar_feedback(dados: FeedbackInput):
    try:
        registros = supabase.table("treinos").select("id, data_hora").eq("email", dados.email).execute()
        treino_id = None
        
        if registros.data:
            for t in registros.data:
                if t['data_hora'] and t['data_hora'].startswith(dados.data_treino):
                    treino_id = t['id']
                    break
                    
        if not treino_id:
            return {"erro": "Treino não encontrado."}

        supabase.table("treinos").update({"feedback_treino": dados.feedback}).eq("id", treino_id).execute()
        return {"sucesso": True}
        
    except Exception as e:
        return {"erro": str(e)}
    
    
class HistoricoInput(BaseModel):
    email: str

@app.post("/historico_grafico")
def historico_grafico(dados: HistoricoInput):
    try:
        # Busca os últimos 7 treinos do atleta, ordenados do mais antigo para o mais novo
        res = supabase.table("treinos").select("data_hora, km_percorridos").eq("email", dados.email).order("data_hora", desc=False).limit(7).execute()
        
        if not res.data:
            return {"erro": "Nenhum treino encontrado."}

        datas = []
        aguda = []
        cronica = []
        
        historico_acumulado = []
        
        for t in res.data:
            # Formata a data para DD/MM
            data_formatada = t['data_hora'][8:10] + "/" + t['data_hora'][5:7]
            km = t['km_percorridos']
            
            # Calcula a Média Crônica (o que o corpo estava acostumado antes deste treino)
            total_hist = sum(historico_acumulado)
            divisor = len(historico_acumulado) if len(historico_acumulado) > 0 else 1
            media_cronica = total_hist / divisor if total_hist > 0 else km
            
            datas.append(data_formatada)
            aguda.append(km)
            cronica.append(round(media_cronica, 1))
            
            historico_acumulado.append(km)
            
        return {"sucesso": True, "datas": datas, "aguda": aguda, "cronica": cronica}
    except Exception as e:
        return {"erro": str(e)}


class ConsultaInput(BaseModel):
    email: str

@app.post("/consultar_hoje")
def consultar_hoje(dados: ConsultaInput):
    try:
        # Busca o histórico ordenado do mais recente para o mais antigo
        res = supabase.table("treinos").select("*").eq("email", dados.email).order("data_hora", desc=True).execute()
        historico = res.data if res.data else []
        
        if not historico:
            return {
                "status": "⚪ BEM-VINDO(A)", 
                "mensagem": "Não encontramos histórico de treinos para este e-mail.", 
                "sugestao": "Faça o seu primeiro treino leve de reconhecimento e registre os dados aqui!"
            }
            
        ultimo_treino = historico[0]
        
        # Calcula os dias desde o último treino
        data_ultimo_obj = datetime.strptime(ultimo_treino['data_hora'][:10], "%Y-%m-%d").date()
        hoje = (datetime.utcnow() - timedelta(hours=3)).date()
        dias_descanso = (hoje - data_ultimo_obj).days

        feedback = ultimo_treino.get('feedback_treino', '')
        if not feedback: feedback = "Sem feedback"
        
        # Calcula a média crônica para sugerir a distância ideal
        total_hist = sum(t.get('km_percorridos', 0) for t in historico)
        media_cronica = total_hist / len(historico)

        # A Árvore de Decisão da IA (Regras de Negócio)
        if "Dor" in feedback and dias_descanso < 3:
            status = "🔴 RECUPERAÇÃO ATIVA"
            msg = f"Você relatou DOR no último treino há {dias_descanso} dia(s). O risco de lesão articular é muito alto."
            sugestao = "Descanso total ou, no máximo, exercícios de mobilidade e alongamento."
        elif dias_descanso == 0:
            status = "🟡 VOCÊ JÁ TREINOU HOJE"
            msg = "O nosso banco indica que você já registrou um treino no dia de hoje."
            sugestao = "Foque na hidratação e descanse. O seu próximo treino deve ser amanhã."
        elif "Cansado" in feedback and dias_descanso < 2:
            status = "🟡 RECUPERAÇÃO"
            msg = f"Você relatou fadiga acentuada no último treino ({dias_descanso} dia atrás)."
            sugestao = f"Treino regenerativo: Caminhada leve ou um trote de no máximo {round(media_cronica * 0.5, 1)} km."
        else:
            status = "🟢 SINAL VERDE"
            msg = f"Você descansou por {dias_descanso} dia(s) e o seu último feedback foi positivo."
            sugestao = f"O corpo está pronto! Sugerimos um treino na casa dos {round(media_cronica * 1.1, 1)} km num ritmo confortável."

        return {"status": status, "mensagem": msg, "sugestao": sugestao}
    except Exception as e:
        return {"erro": str(e)}
    

class DeletarInput(BaseModel):
    email: str

@app.delete("/deletar_ultimo_treino")
def deletar_ultimo_treino(dados: DeletarInput):
    try:
        # 1. Busca qual é o ID do treino mais recente deste utilizador
        res = supabase.table("treinos").select("id").eq("email", dados.email).order("data_hora", desc=True).limit(1).execute()
        
        if not res.data:
            return {"erro": "Não há treinos registrados para apagar."}
            
        treino_id = res.data[0]['id']
        
        # 2. Deleta a linha exata no Supabase usando o ID
        supabase.table("treinos").delete().eq("id", treino_id).execute()
        
        return {"sucesso": True, "mensagem": "O seu último treino foi apagado do histórico."}
        
    except Exception as e:
        return {"erro": str(e)}