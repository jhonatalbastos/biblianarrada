import sqlite3
import json
import os

# Nome do arquivo do banco de dados
DB_FILE = "liturgia.db"

def get_connection():
    """Conecta ao banco e garante que as tabelas existam."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    # Sempre que conectar, garantimos que a tabela existe
    create_tables(conn)
    return conn

def create_tables(conn):
    """Cria a tabela 'historico' se ela não existir."""
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            data_liturgia TEXT PRIMARY KEY,
            json_completo TEXT
        )
    ''')
    conn.commit()

def salvar_liturgia(data_str, json_data):
    """Salva o JSON da liturgia no banco."""
    conn = get_connection()
    c = conn.cursor()
    try:
        # Converte o dicionário Python para string JSON
        json_text = json.dumps(json_data, ensure_ascii=False)
        c.execute('''
            INSERT OR REPLACE INTO historico (data_liturgia, json_completo)
            VALUES (?, ?)
        ''', (data_str, json_text))
        conn.commit()
    except Exception as e:
        print(f"Erro ao salvar no BD: {e}")
    finally:
        conn.close()

def carregar_liturgia(data_str):
    """Carrega o JSON da liturgia do banco, se existir."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT json_completo FROM historico WHERE data_liturgia = ?', (data_str,))
        row = c.fetchone()
        
        if row:
            # Converte a string JSON de volta para dicionário Python
            return json.loads(row[0])
        return None
    except Exception as e:
        print(f"Erro ao ler do BD: {e}")
        return None
    finally:
        conn.close()