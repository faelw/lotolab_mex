import os
import json
import requests
import pandas as pd
from io import StringIO
import re

# Configurações de Pastas e Arquivos
DATA_DIR = "data"
HISTORICO_FILE = f"{DATA_DIR}/historico_mexico.json"
RESUMO_FILE = f"{DATA_DIR}/resumo_tela_principal.json"

# Nomes dos jogos na ordem exata em que as tabelas aparecem no site oficial
JOGOS_ORDEM = ["MELATE", "REVANCHA", "REVANCHITA"]

def garantir_pastas():
    os.makedirs(DATA_DIR, exist_ok=True)

def formatar_moeda(valor_str):
    try:
        valor_float = float(valor_str)
        return f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

def main():
    print("=== Iniciando atualização web (Melate, Revancha e Revanchita) ===")
    garantir_pastas()
    
    banco_final = {
        "MELATE": [],
        "REVANCHA": [],
        "REVANCHITA": []
    }
    
    # Carrega o histórico existente
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            try:
                dados_carregados = json.load(f)
                if isinstance(dados_carregados, dict):
                    banco_final.update(dados_carregados)
            except json.JSONDecodeError:
                print("Aviso: JSON antigo vazio ou corrompido.")

    # Busca a página que contém os 3 jogos
    url_resultados = "https://www.loterianacional.gob.mx/Melate/Resultados"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url_resultados, headers=headers)
        response.raise_for_status()
        # Coleta todas as tabelas da página
        tabelas = pd.read_html(StringIO(response.text))
    except Exception as e:
        print(f"[!] Erro ao raspar dados da página: {e}")
        return

    # Varre as tabelas usando a ordem mapeada
    for i, nome_jogo in enumerate(JOGOS_ORDEM):
        if i >= len(tabelas):
            print(f"[!] Tabela para {nome_jogo} não encontrada na página.")
            continue
            
        df_jogo = tabelas[i]
        novos_resultados = []
        
        for index, row in df_jogo.iterrows():
            try:
                linha = [str(x).strip() for x in row.values]
                concurso = str(linha[0])
                
                # Ignora linhas de cabeçalho duplicadas no meio da tabela HTML
                if not concurso.isdigit():
                    continue 
                    
                data_bruta = str(linha[1])
                data_formatada = data_bruta
                
                # Formata a data
                if "/" in data_bruta:
                    partes = data_bruta.split("/")
                    if len(partes) == 3:
                        data_formatada = f"{partes[2]}-{partes[1]}-{partes[0]}"
                        
                # Extrai os números (serve tanto para as 7 do Melate quanto as 6 da Revancha/Revanchita)
                numeros_encontrados = []
                for val in linha[2:]:
                    numeros_encontrados.extend(re.findall(r'\d+', val))
                    
                bolas_principais = numeros_encontrados[:6] if len(numeros_encontrados) >= 6 else numeros_encontrados
                bola_bonus = [numeros_encontrados[6]] if len(numeros_encontrados) >= 7 else []
                
                bolas_principais = [str(b).zfill(2) for b in bolas_principais]
                bola_bonus = [str(b).zfill(2) for b in bola_bonus]
                
                # Fallback de bolsa pois as tabelas rápidas não mostram a premiação final
                valor_bolsa = "0"
                
                sorteio = {
                    "drawNumber": concurso,
                    "drawDate": data_formatada,
                    "balls": bolas_principais,
                    "bonusBalls": bola_bonus,
                    "prizeValue": valor_bolsa
                }
                novos_resultados.append(sorteio)
            except Exception:
                continue

        # Verifica duplicidade para o jogo atual do loop
        concursos_existentes = {
            str(item.get("drawNumber")) 
            for item in banco_final.get(nome_jogo, []) 
            if isinstance(item, dict)
        }
        
        for item in reversed(novos_resultados):
            if item["drawNumber"] not in concursos_existentes:
                banco_final[nome_jogo].insert(0, item)
                
        # Ordena a modalidade atualizada
        banco_final[nome_jogo] = sorted(banco_final[nome_jogo], key=lambda x: int(x["drawNumber"]), reverse=True)
        print(f"✅ {nome_jogo}: {len(novos_resultados)} últimos resultados validados da web.")

    # Salva o arquivo final com todas as 3 modalidades
    with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
        json.dump(banco_final, f, indent=4, ensure_ascii=False)
    print(f"\n💾 Banco Histórico unificado salvo em: {HISTORICO_FILE}")

    # Gera o resumo para a tela inicial abrangendo os 3 jogos
    print("\n=== Gerando Resumo para a Tela Inicial ===")
    resumo = {}

    for game_name, lista_sorteios in banco_final.items():
        resumo[game_name] = []
        ultimos_10 = lista_sorteios[:10]

        for draw in ultimos_10:
            valor_formatado = formatar_moeda(draw.get("prizeValue", "0"))
            sorteio_enxuto = {
                "drawNumber": draw.get("drawNumber"),
                "drawDate": draw.get("drawDate"),
                "balls": draw.get("balls", []),
                "bonusBalls": draw.get("bonusBalls", []),
                "prizeValue": draw.get("prizeValue"),
                "prizeFormatted": f"${valor_formatado}" 
            }
            resumo[game_name].append(sorteio_enxuto)

    with open(RESUMO_FILE, "w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=4, ensure_ascii=False)
        
    print(f"💾 Resumo leve (10 últimos) salvo em: {RESUMO_FILE}")
    print("\n🚀 Atualização de todos os jogos finalizada com sucesso!")

if __name__ == "__main__":
    main()
