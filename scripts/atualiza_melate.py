import os
import json
import requests
import pandas as pd
from io import StringIO

def main():
    # URL oficial com os últimos resultados do Melate
    url_resultados = "https://www.loterianacional.gob.mx/Melate/Resultados"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print("Buscando resultados...")
    try:
        response = requests.get(url_resultados, headers=headers)
        response.raise_for_status()
        
        # O Pandas varre o HTML e coleta todas as tabelas. A primeira é a dos 15 últimos sorteios.
        tabelas = pd.read_html(StringIO(response.text))
        df_recentes = tabelas[0] 
        
    except Exception as e:
        print(f"Erro ao acessar ou extrair dados da página: {e}")
        return

    novos_resultados = []
    
    # As colunas padrão da tabela do Melate são: "Sorteo", "Fecha", "Combinación Ganadora"
    for index, row in df_recentes.iterrows():
        try:
            concurso = str(row.iloc[0]).strip()
            data = str(row.iloc[1]).strip()
            combinacao = str(row.iloc[2]).strip()
            
            novos_resultados.append({
                "concurso": concurso,
                "data": data,
                "numeros": combinacao
            })
        except Exception:
            continue

    # Caminhos para salvar no repositório do LotoLab
    caminho_historico = "data/historico_mexico.json"
    caminho_resumo = "data/resumo_tela_principal.json"
    
    historico = []
    
    # Se o histórico já existe, carrega a base atual
    if os.path.exists(caminho_historico):
        with open(caminho_historico, "r", encoding="utf-8") as f:
            try:
                historico = json.load(f)
            except json.JSONDecodeError:
                historico = []
                
    # Cria um Set com os números dos concursos para verificação rápida
    concursos_existentes = {item["concurso"] for item in historico}
    
    # Adiciona os resultados novos varrendo de trás para frente (garante a sequência temporal)
    for item in reversed(novos_resultados):
        if item["concurso"] not in concursos_existentes:
            historico.insert(0, item) 
            
    # Ordena do maior concurso (mais recente) para o menor
    historico.sort(key=lambda x: int(x["concurso"]), reverse=True)

    # Cria a pasta data/ caso o diretório não exista
    os.makedirs("data", exist_ok=True)
    
    # 1. Salva o histórico de todos os concursos
    with open(caminho_historico, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=4, ensure_ascii=False)
        
    # 2. Salva o arquivo focado apenas na Tela Principal (Top 10)
    resumo_tela = historico[:10]
    with open(caminho_resumo, "w", encoding="utf-8") as f:
        json.dump(resumo_tela, f, indent=4, ensure_ascii=False)
        
    print("Arquivos atualizados com sucesso!")

if __name__ == "__main__":
    main()
