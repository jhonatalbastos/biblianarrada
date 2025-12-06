import sqlite3
import json
import os
from datetime import datetime

# Define o caminho para a pasta 'data' e o arquivo do banco
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'liturgia.db')

def get_connection():
    # Garante que a pasta data existe
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Tabela Histórico (Cache da API)
    c.execute('''CREATE TABLE IF NOT EXISTS historico
                 (data_liturgia TEXT PRIMARY KEY, json_completo TEXT, cor TEXT, ultimo_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela Status de Produção (Controle interno)
    c.execute('''CREATE TABLE IF NOT EXISTS producao_status
                 (chave_leitura TEXT PRIMARY KEY, data_liturgia TEXT, tipo_leitura TEXT, progresso TEXT, em_producao INTEGER, ultimo_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# --- FUNÇÕES DE HISTÓRICO (LITURGIA) ---

def salvar_liturgia(data_str, json_data):
    conn = get_connection()
    c = conn.cursor()
    json_str = json.dumps(json_data)
    cor = json_data.get('cor', 'Branco') 
    c.execute('''INSERT OR REPLACE INTO historico (data_liturgia, json_completo, cor, ultimo_acesso) VALUES (?, ?, ?, CURRENT_TIMESTAMP)''', (data_str, json_str, cor))
    conn.commit()
    conn.close()

def carregar_liturgia(data_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
    res = c.fetchone()
    conn.close()
    return json.loads(res[0]) if res else None

def listar_historico():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT data_liturgia, cor, ultimo_acesso FROM historico ORDER BY data_liturgia DESC')
    rows = c.fetchall()
    conn.close()
    lista = []
    for data, cor, acesso in rows:
        try:
            # Formata data se possível
            data_acesso = datetime.strptime(str(acesso).split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        except:
            data_acesso = acesso
        lista.append({'Data': data, 'Cor Litúrgica': cor, 'Último Acesso': data_acesso})
    return lista

# --- FUNÇÕES DE STATUS DE PRODUÇÃO ---

def load_status(chave=None):
    conn = get_connection()
    c = conn.cursor()
    if chave:
        c.execute('SELECT progresso, em_producao FROM producao_status WHERE chave_leitura = ?', (chave,))
        res = c.fetchone()
        conn.close()
        return (json.loads(res[0]), res[1]) if res else (None, 0)
    else:
        # Carrega tudo que está em produção ou modificado
        default_json = json.dumps({"roteiro": False, "imagens": False, "audio": False, "overlay": False, "legendas": False, "video": False, "publicacao": False})
        c.execute(f'SELECT chave_leitura, data_liturgia, tipo_leitura, progresso, em_producao FROM producao_status WHERE em_producao = 1 OR progresso != ?', (default_json,))
        rows = c.fetchall()
        conn.close()
        all_status = {}
        for row in rows:
            all_status[row[0]] = {'data_liturgia': row[1], 'tipo_leitura': row[2], 'progresso': json.loads(row[3]), 'em_producao': row[4]}
        return all_status

def update_status(chave, data_liturgia, tipo_leitura, progresso_dict, em_producao):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO producao_status (chave_leitura, data_liturgia, tipo_leitura, progresso, em_producao, ultimo_acesso) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', 
              (chave, data_liturgia, tipo_leitura, json.dumps(progresso_dict), 1 if em_producao else 0))
    conn.commit()
    conn.close()
