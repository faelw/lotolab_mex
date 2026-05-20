import csv
import json
import os
import requests

# Configurações de Pastas e Arquivos
DATA_DIR = "data"
HISTORICO_FILE = f"{DATA_DIR}/historico_mexico.json"
RESUMO_FILE = f"{DATA_DIR}/resumo_tela_principal.json"

# Seu Dicionário ORIGINAL, agora com as URLs oficiais dos CSVs do governo
GAMES_CONFIG = {
    "MELATE": {
        "url": "https://www.loterianacional.gob.mx/Documentos/Historicos/Melate.csv",
        "file": "Melate.csv",
        "has_bonus": True,
        "date_index": 10,
        "bolsa_index": 9 
    },
    "REVANCHA": {
        "url": "https://www.loterianacional.gob.mx/Documentos/Historicos/Revancha.csv",
        "file": "Revancha.csv",
        "has_bonus": False,
        "date_index": 9,
        "bolsa_index": 8
    },
    "REVANCHITA": {
        "url": "https://www.loterianacional.gob.mx/Documentos/Historicos/Revanchita.csv",
        "file": "Revanchita.csv",
        "has_bonus": False,
        "date_index": 9,
        "bolsa_index": 8
    }
}

def garantir_pastas():
    os.makedirs(DATA_DIR, exist_ok=True)

def baixar_csvs_oficiais():
    print("=== Baixando arquivos CSV oficiais da Lotería Nacional ===")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for game_name, config in GAMES_CONFIG.items():
        try:
            print(f"Baixando {game_name}...")
            response = requests.get(config["url"], headers=headers, timeout=15)
            response.raise_for_status()
            
            with open(config["file"], "wb") as f:
                f.write(response.content)
            print(f" [✓] {config['file']} baixado com sucesso.")
        except Exception as e:
            print(f" [!] Erro ao baixar {game_name}: {e}")

def formatar_moeda(valor_str):
    try:
        valor_float = float(valor_str)
        return f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

def converter_csvs_para_json():
    print("\n=== Iniciando processamento dos CSVs ===")
    banco_final = {}
    
    for game_name, config in GAMES_CONFIG.items():
        csv_file = config["file"]
        has_bonus = config["has_bonus"]
        idx_data = config["date_index"]
        idx_bolsa = config["bolsa_index"]
        
        resultados = []
        
        try:
            # Usando a mesma codificação (utf-8-sig) do seu script original
            with open(csv_file, mode='r', encoding='utf-8-sig') as arquivo_csv:
                leitor = csv.reader(arquivo_csv, delimiter=',') 
                next(leitor, None) # Pula cabeçalho
                
                for linha in leitor:
                    if not linha or len(linha) < 8:
                        continue
                    
                    concurso = str(linha[1]).strip()
                    if not concurso.isdigit():
                        continue # Pula sujeiras e linhas em branco
                        
                    # Puxa e adiciona o '0' na frente se for número único (ex: '4' vira '04')
                    bolas_principais = [str(x).strip().zfill(2) for x in linha[2:8]]
                    
                    bola_bonus = []
                    if has_bonus and len(linha) > 8:
                        bola_bonus = [str(linha[8]).strip().zfill(2)]
                        
                    valor_bolsa = str(linha[idx_bolsa]).strip() if len(linha) > idx_bolsa else "0"
                    data_bruta = str(linha[idx_data]).strip() if len(linha) > idx_data else ""
                    
                    data_formatada = data_bruta
                    if "/" in data_bruta:
                        partes = data_bruta.split("/")
                        if len(partes) == 3:
                            data_formatada = f"{partes[2]}-{partes[1]}-{partes[0]}"
                            
                    sorteio = {
                        "drawNumber": concurso,
                        "drawDate": data_formatada,
                        "balls": bolas_principais,
                        "bonusBalls": bola_bonus,
                        "prizeValue": valor_bolsa
                    }
                    resultados.append(sorteio)
                    
            # Ordena do mais recente para o mais antigo
            resultados = sorted(resultados, key=lambda x: int(x["drawNumber"]), reverse=True)
            banco_final[game_name] = resultados
            print(f" [✓] {len(resultados)} sorteios de {game_name} convertidos!")
            
            # Remove o arquivo CSV que foi baixado para não subir no GitHub
            if os.path.exists(csv_file):
                os.remove(csv_file)
                
        except Exception as e:
            print(f" [!] Erro ao converter {game_name}: {e}")
            
    if banco_final:
        with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
            json.dump(banco_final, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Banco Histórico unificado salvo em: {HISTORICO_FILE}")
        
    return banco_final

def gerar_resumo_tela_principal(banco_completo):
    print("\n=== Gerando Resumo para a Tela Inicial ===")
    resumo = {}

    for game_name, lista_sorteios in banco_completo.items():
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
        
    print(f"✅ Resumo leve (10 últimos) salvo em: {RESUMO_FILE}")

if __name__ == "__main__":
    garantir_pastas()
    baixar_csvs_oficiais()
    banco_unificado = converter_csvs_para_json()
    if banco_unificado:
        gerar_resumo_tela_principal(banco_unificado)
        print("\n🚀 Todos os dados atualizados a partir da fonte oficial do México!")
