from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from supabase import create_client, Client

app = FastAPI()

# --- CONFIGURAÇÃO ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class Treino(BaseModel):
    user_id: str  # <--- NOVO CAMPO OBRIGATÓRIO
    km: float
    tempo: float
    calorias: float
    esforco: int
    clima: str

# --- INTELIGÊNCIA ARTIFICIAL (Lógica ACWR) ---
def calcular_risco_lesao(novo_treino, historico):
    historico_recente = [t for t in historico]
    
    # Carga Aguda (Treino atual + últimos 7 dias)
    carga_aguda = novo_treino.km
    for t in historico_recente[:6]: 
        carga_aguda += t.get('km_percorridos', 0)

    # Carga Crônica (Média das últimas 4 semanas)
    total_historico = sum(t.get('km_percorridos', 0) for t in historico_recente)
    carga_cronica = (total_historico + novo_treino.km) / 4 
    
    if carga_cronica == 0: carga_cronica = 1

    ratio = carga_aguda / carga_cronica

    if ratio > 1.5:
        status = "🔴 ALTO RISCO"
        msg = "Cuidado! Aumento brusco de volume."
        sugestao = f"Descanse. Teto seguro: {novo_treino.km * 0.5:.1f} km."
    elif ratio > 1.2:
        status = "🟡 MODERADO"
        msg = "Zona de atenção."
        sugestao = f"Mantenha o volume atual."
    elif ratio < 0.8:
        status = "🟢 BAIXO (Destreinando)"
        msg = "Volume baixo para sua capacidade."
        sugestao = f"Pode subir para {novo_treino.km * 1.1:.1f} km."
    else:
        status = "🟢 ZONA IDEAL"
        msg = "Evolução consistente."
        sugestao = f"Próximo alvo: {novo_treino.km * 1.05:.1f} km."

    return {
        "status": status,
        "mensagem": msg,
        "ratio": round(ratio, 2),
        "sugerido_proximo": sugestao,
        "acumulado_semana": round(carga_aguda, 1)
    }

@app.post("/registrar_treino")
def registrar_treino(treino: Treino):
    try:
        # 1. Salvar no Banco (COM O USER_ID)
        dados_novos = {
            "user_id": treino.user_id, # <--- Carimba o dono
            "km_percorridos": treino.km,
            "tempo_gasto": treino.tempo,
            "calorias": treino.calorias,
            "esforco_percebido": treino.esforco,
            "clima": treino.clima
        }
        supabase.table("treinos").insert(dados_novos).execute()

        # 2. Buscar Histórico FILTRADO (Segurança de Dados)
        # O .eq("user_id", treino.user_id) garante que eu só veja OS MEUS dados
        res_history = supabase.table("treinos")\
            .select("km_percorridos, data_hora")\
            .eq("user_id", treino.user_id)\
            .order("data_hora", desc=True)\
            .limit(28)\
            .execute()
        
        historico = res_history.data if res_history.data else []

        # 3. Rodar a IA
        analise = calcular_risco_lesao(treino, historico)

        return {"message": "Salvo", "analise": analise}

    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))
