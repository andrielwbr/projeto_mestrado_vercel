from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from supabase import create_client, Client

app = FastAPI()

# 1. Conexão com o Supabase (Lê as senhas da Vercel)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 2. Modelo de dados (O que o site manda)
class Treino(BaseModel):
    km: float
    tempo: float
    calorias: float
    esforco: int
    clima: str

@app.post("/registrar_treino")
def registrar_treino(treino: Treino):
    try:
        # Preparar os dados
        dados_para_salvar = {
            "km_percorridos": treino.km,
            "tempo_gasto": treino.tempo,
            "calorias": treino.calorias,
            "esforco_percebido": treino.esforco,
            "clima": treino.clima
        }

        # 3. ENVIAR PARA O SUPABASE (Aqui é a mágica)
        response = supabase.table("treinos").insert(dados_para_salvar).execute()

        # Retorna sucesso para o site
        return {"message": "Treino salvo na Nuvem com sucesso!", "dados": response.data}

    except Exception as e:
        print(f"Erro ao salvar: {e}")
        raise HTTPException(status_code=500, detail=str(e))
