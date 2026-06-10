import streamlit as st
from datetime import datetime, date, timedelta
from supabase import create_client, Client
import json
import pandas as pd
import altair as alt
import pytz

# ====================== CONFIGURAÇÃO DE FUSO HORÁRIO ======================
FUSO = pytz.timezone("America/Fortaleza")

MESES_BR = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# ====================== SUPABASE ======================
SUPABASE_URL = "https://kecmxzamzkgnwlfyadjt.supabase.co"
SUPABASE_KEY = "sb_publishable_Xvf2dMiG6_vKh25LRQFmQA_8efs__ff"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="meu-treino-app", page_icon="🏋️‍♂️", layout="centered")
alt.themes.enable("dark")

# ====================== DADOS ======================
EXERCICIOS_BASE = {
    "🦵 Pernas": ["Agachamento Livre","Leg Press","Cadeira Extensora","Mesa Flexora","Stiff","Avanço","Afundo","Panturrilha na Máquina","Hack Squat"],
    "🫁 Peito": ["Supino Reto","Supino Inclinado","Supino Declinado","Crucifixo","Crossover","Peck Deck","Flexão","Pullover","Crucifixo Máquina (Peck Deck)","Desenvolvimento com Halteres","Elevação Lateral (Halteres ou Polia)"],
    "🔙 Costas": ["Puxada Frontal","Remada Curvada","Remada Unilateral","Levantamento Terra","Serrote","Puxada Fechada","Remada na Máquina","Pull-up"],
    "💪 Bíceps": ["Rosca Direta","Rosca Alternada","Rosca Martelo","Rosca Concentrada","Rosca 21","Rosca na Polia","Tríceps Pulley (Barra ou Corda)"],
    "💪 Tríceps": ["Tríceps Corda","Tríceps Testa","Tríceps Francês","Mergulho","Tríceps na Polia Alta","Tríceps Coice","Tríceps Pulley (Barra ou Corda)"],
    "🏔️ Ombros": ["Desenvolvimento","Elevação Lateral","Elevação Frontal","Remada Alta","Encolhimento","Crucifixo Inverso"],
    "🎯 Abdômen": ["Abdominal Crunch","Prancha","Abdominal Oblíquo","Elevação de Pernas","Abdominal na Máquina","Russian Twist"],
}

GRUPOS_MUSCULARES = list(EXERCICIOS_BASE.keys())
OBJETIVOS = ["Hipertrofia", "Emagrecimento", "Condicionamento", "Força"]
TEMPOS = ["45 min", "1h", "1h15", "1h30", "2h"]

# ====================== SESSION STATE & AUTO-LOGIN ======================
defaults = {
    "tela_atual": "login",
    "usuario_logado": None,
    "perfil": None,
    "treino_exercicios": [],
    "plano_exercicios_tmp": [],
    "editando_perfil": False,
    "aba_atual": "🏋️ Treino",
    "mostrar_form_novo_ex": False,
    "exercicios_custom": {},
    "editando_ex_id": None,  # Controla qual exercício customizado está sendo renomeado
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

query_params = st.query_params
if "user" in query_params and st.session_state.usuario_logado is None:
    user_url = query_params["user"]
    try:
        r = supabase.table("perfis").select("*").eq("username", user_url).execute()
        if r.data:
            user = r.data[0]
            st.session_state.usuario_logado = user_url
            st.session_state.perfil = user
            st.session_state.exercicios_custom = {}
            st.session_state.tela_atual = "dashboard"
            if user.get("treino_em_andamento"):
                try:
                    st.session_state.treino_exercicios = json.loads(user.get("treino_em_andamento"))
                except:
                    st.session_state.treino_exercicios = []
    except:
        pass

# ====================== FUNÇÕES DB ======================
def hoje_no_fuso():
    return datetime.now(FUSO).date()

def criar_usuario(username, senha, nome, objetivo, dias, tempo):
    try:
        r = supabase.table("perfis").insert({
            "username": username, "nome": nome, "objetivo": objetivo,
            "dias_por_semana": dias, "tempo_disponivel": tempo,
            "onboarding_concluido": True, "senha": senha, "treino_em_andamento": "[]"
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao criar conta: {e}")
        return None

def login_usuario(username, senha):
    try:
        r = supabase.table("perfis").select("*").eq("username", username).execute()
        if r.data:
            u = r.data[0]
            if u.get("senha") == senha:
                return u
        return None
    except Exception as e:
        st.error(f"Erro no login: {e}")
        return None

def atualizar_perfil(username, nome, objective, dias, tempo):
    try:
        r = supabase.table("perfis").update({
            "nome": nome, "objetivo": objective,
            "dias_por_semana": dias, "tempo_disponivel": tempo,
        }).eq("username", username).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao atualizar perfil: {e}")
        return None

def persistir_rascunho_treino(username, lista_exercicios):
    try:
        supabase.table("perfis").update({
            "treino_em_andamento": json.dumps(lista_exercicios, ensure_ascii=False)
        }).eq("username", username).execute()
    except:
        pass

def salvar_treino(username, exercicios, duracao_min, notas=""):
    try:
        r = supabase.table("treinos").insert({
            "username": username,
            "data": hoje_no_fuso().isoformat(),
            "exercicios": json.dumps(exercicios, ensure_ascii=False),
            "duracao_min": duracao_min,
            "notas": notas,
        }).execute()
        if r.data:
            persistir_rascunho_treino(username, [])
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao salvar treino: {e}")
        return None

def deletar_treino(treino_id):
    try:
        supabase.table("treinos").delete().eq("id", treino_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar treino: {e}")
        return False

def buscar_treinos(username, limit=30):
    try:
        r = supabase.table("treinos").select("*").eq("username", username).order("data", desc=True).limit(limit).execute()
        treinos = r.data or []
        for t in treinos:
            if isinstance(t.get("exercicios"), str):
                try:
                    t["exercicios"] = json.loads(t["exercicios"])
                except:
                    t["exercicios"] = []
        return treinos
    except Exception as e:
        st.error(f"Erro ao buscar treinos: {e}")
        return []

def salvar_medidas(username, peso, cintura, braco_dir, braco_esq, bf, coxa_dir, coxa_esq, panturrilha_dir, panturrilha_esq, quadril, peito, ombro):
    try:
        r = supabase.table("historico_corporal").insert({
            "username": username,
            "data_registro": hoje_no_fuso().isoformat(),
            "peso": float(peso),
            "cintura": float(cintura) if cintura else None,
            "braço_direito": float(braco_dir) if braco_dir else None,
            "braço_esquerdo": float(braco_esq) if braco_esq else None,
            "percentual_gordura": float(bf) if bf else None,
            "coxa_direita": float(coxa_dir) if coxa_dir else None,
            "coxa_esquerda": float(coxa_esq) if coxa_esq else None,
            "panturrilha_direita": float(panturrilha_dir) if panturrilha_dir else None,
            "panturrilha_esquerda": float(panturrilha_esq) if panturrilha_esq else None,
            "quadril": float(quadril) if quadril else None,
            "peito": float(peito) if peito else None,
            "ombro": float(ombro) if ombro else None
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao salvar medidas: {e}")
        return None

def buscar_historico_medidas(username):
    try:
        r = supabase.table("historico_corporal").select("*").eq("username", username).order("data_registro", desc=True).execute()
        return r.data or []
    except Exception as e:
        st.error(f"Erro ao buscar histórico de medidas: {e}")
        return []

def deletar_medida(medida_id):
    try:
        supabase.table("historico_corporal").delete().eq("id", medida_id).execute()
        return True
    except Exception:
        return False

def salvar_plano(username, nome_plano, descricao, exercicios):
    try:
        r = supabase.table("planos").insert({
            "username": username,
            "nome": nome_plano,
            "descricao": descricao,
            "exercicios": json.dumps(exercicios, ensure_ascii=False),
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao salvar plano: {e}")
        return None

def buscar_planos(username):
    try:
        r = supabase.table("planos").select("*").eq("username", username).order("id", desc=True).execute()
        planos = r.data or []
        for p in planos:
            if isinstance(p.get("exercicios"), str):
                try:
                    p["exercicios"] = json.loads(p["exercicios"])
                except:
                    p["exercicios"] = []
        return planos
    except Exception as e:
        st.error(f"Erro ao buscar planos: {e}")
        return []

def deletar_plano(plano_id):
    try:
        supabase.table("planos").delete().eq("id", plano_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar plano: {e}")
        return False

def get_ultimo_peso(username, exercicio_nome):
    try:
        r = supabase.table("treinos").select("exercicios").eq("username", username).order("data", desc=True).limit(50).execute()
        peso_max = 0.0
        for treino in r.data:
            exs = treino.get("exercicios", [])
            if isinstance(exs, str):
                exs = json.loads(exs)
            for ex in exs:
                if ex.get("nome") == exercicio_nome:
                    peso_max = max(peso_max, float(ex.get("peso", 0)))
        return peso_max
    except:
        return 0.0

def get_evolucao_carga(username, exercicio_nome):
    try:
        treinos = buscar_treinos(username, 200)
        registros = []
        for t in treinos:
            try:
                data_t = datetime.strptime(t["data"], "%Y-%m-%d").date()
                for ex in t.get("exercicios", []):
                    if ex.get("nome") == exercicio_nome and float(ex.get("peso", 0)) > 0:
                        registros.append({
                            "data": data_t,
                            "peso": float(ex.get("peso", 0)),
                            "volume": ex.get("series", 0) * ex.get("reps", 0) * float(ex.get("peso", 0)),
                            "series": ex.get("series"),
                            "reps": ex.get("reps"),
                        })
            except:
                continue
        return pd.DataFrame(registros)
    except:
        return pd.DataFrame()

def get_stats_gerais(username):
    treinos = buscar_treinos(username, 200)
    if not treinos:
        return {}
    total_treinos = len(treinos)
    total_min = sum(t.get("duracao_min", 0) or 0 for t in treinos)
    total_series = 0
    grupos_count = {}
    for t in treinos:
        for ex in t.get("exercicios", []):
            total_series += ex.get("series", 0)
            g = ex.get("grupo", "Outro")
            grupos_count[g] = grupos_count.get(g, 0) + 1
    datas = sorted({datetime.strptime(t["data"], "%Y-%m-%d").date() for t in treinos}, reverse=True)
    streak = 0
    ref = hoje_no_fuso()
    for d in datas:
        diff = (ref - d).days
        if diff <= 1:
            streak += 1
            ref = d
        else:
            break
    return {
        "total_treinos": total_treinos,
        "total_horas": round(total_min / 60, 1),
        "total_series": total_series,
        "streak": streak,
        "grupos_count": grupos_count,
        "datas": datas,
    }

def get_saudacao(hora):
    if hora < 12:
        return "BOM DIA"
    elif hora < 18:
        return "BOA TARDE"
    else:
        return "BOA NOITE"

def render_weekly_tracker(treinos):
    hoje = hoje_no_fuso()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    datas_treino = {datetime.strptime(t["data"], "%Y-%m-%d").date() for t in treinos if t.get("data")}
    dias_abrev = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    dias_html = ""
    for i, dia_nome in enumerate(dias_abrev):
        dia_data = inicio_semana + timedelta(days=i)
        is_hoje = dia_data == hoje
        is_futuro = dia_data > hoje
        if is_futuro:
            cor_ponto, cor_texto, cor_fundo = "#2a2a3a", "#444", "transparent"
            borda, sombra_card, glow_ponto = "1px solid #1e1e2e", "", ""
        elif dia_data in datas_treino:
            cor_ponto, cor_texto, cor_fundo = "#22c55e", "#22c55e", "rgba(34,197,94,0.12)"
            borda, sombra_card, glow_ponto = "1px solid rgba(34,197,94,0.4)", "", "box-shadow:0 0 6px #22c55e;"
        elif is_hoje:
            cor_ponto, cor_texto, cor_fundo = "#f59e0b", "#f59e0b", "rgba(245,158,11,0.15)"
            borda, sombra_card, glow_ponto = "2px solid #f59e0b", "box-shadow:0 0 12px rgba(245,158,11,0.4);", "box-shadow:0 0 6px #f59e0b;"
        else:
            cor_ponto, cor_texto, cor_fundo = "#ef4444", "#ef4444", "rgba(239,68,68,0.08)"
            borda, sombra_card, glow_ponto = "1px solid rgba(239,68,68,0.3)", "", "box-shadow:0 0 6px #ef4444;"
        card = "".join([
            '<div style="display:flex;flex-direction:column;align-items:center;gap:6px;',
            'background:', cor_fundo, ';border:', borda, ';',
            'border-radius:14px;padding:10px 8px;flex:1;', sombra_card, '">',
            '<div style="width:10px;height:10px;border-radius:50%;background:',
            cor_ponto, ';', glow_ponto, '"></div>',
            '<span style="font-size:0.75rem;font-weight:700;color:', cor_texto,
            ';letter-spacing:.05em;">', dia_nome, '</span>',
            '<span style="font-size:0.7rem;color:#666;">', dia_data.strftime('%d'), '</span>',
            '</div>',
        ])
        dias_html += card
    html = "".join([
        '<div style="margin:20px 0 24px 0;">',
        '<div style="font-size:0.75rem;color:#666;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">SEMANA ATUAL</div>',
        '<div style="display:flex;gap:8px;">', dias_html, '</div></div>',
    ])
    st.markdown(html, unsafe_allow_html=True)

# ====================== FUNÇÕES DE EXERCÍCIOS CUSTOM ======================
def buscar_exercicios_custom_raw(username):
    try:
        r = supabase.table("exercicios_custom").select("*").eq("username", username).order("nome").execute()
        return r.data or []
    except Exception as e:
        st.error(f"Erro ao buscar exercícios custom estruturados: {e}")
        return []

def buscar_exercicios_custom(username):
    data = buscar_exercicios_custom_raw(username)
    resultado = {}
    for row in data:
        grupo = row["grupo"]
        if grupo not in resultado:
            resultado[grupo] = []
        resultado[grupo].append(row["nome"])
    return resultado

def cadastrar_exercicio_custom(username, nome, grupo):
    try:
        r = supabase.table("exercicios_custom").select("id").eq("username", username).eq("nome", nome).eq("grupo", grupo).execute()
        if r.data:
            return False, "Exercício já existe neste grupo."
        supabase.table("exercicios_custom").insert({
            "username": username,
            "nome": nome,
            "grupo": grupo,
        }).execute()
        return True, "ok"
    except Exception as e:
        return False, str(e)

def atualizar_exercicio_custom(exercicio_id, novo_nome):
    try:
        supabase.table("exercicios_custom").update({"nome": novo_nome}).eq("id", exercicio_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao renomear: {e}")
        return False

def deletar_exercicio_custom(username, nome, grupo):
    try:
        supabase.table("exercicios_custom").delete().eq("username", username).eq("nome", nome).eq("grupo", grupo).execute()
        return True
    except:
        return False

def get_exercicios_merged(username):
    if not st.session_state.exercicios_custom:
        st.session_state.exercicios_custom = buscar_exercicios_custom(username)

    merged = {}
    for grupo, lista in EXERCICIOS_BASE.items():
        merged[grupo] = list(lista)

    for grupo, lista in st.session_state.exercicios_custom.items():
        if grupo in merged:
            for nome in lista:
                if nome not in merged[grupo]:
                    merged[grupo].append(nome)
        else:
            merged[grupo] = list(lista)

    return merged

def invalidar_cache_custom():
    st.session_state.exercicios_custom = {}

# ====================== CSS INJETADO (STYLING ATUALIZADO) ======================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Nunito:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Nunito', sans-serif; background-color: #0a0a0f; }
h1, h2, h3 { font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 0.04em; }

.ex-card {
    background:#111118; border-left:4px solid #FFA500;
    border-radius:12px; padding:12px 16px; margin-bottom:10px;
}
.ex-card-done {
    background:#0b130e; border-left:4px solid #22c55e;
    border-radius:12px; padding:12px 16px; margin-bottom:10px;
    opacity: 0.6;
}
.hist-card {
    background:#111118; border:1px solid #1e1e2e;
    border-radius:14px; padding:16px 18px; margin-bottom:12px;
}
.plano-card {
    background:#111118; border:1px solid #2a1f3a;
    border-left:4px solid #a855f7; border-radius:14px;
    padding:16px 18px; margin-bottom:12px;
}
.stat-card {
    background:#111118; border:1px solid #1e1e2e;
    border-radius:14px; padding:18px; text-align:center;
}
.novo-ex-box {
    background:#111118; border:1px solid #e53935;
    border-radius:14px; padding:20px; margin: 15px 0;
}
div[data-testid="stForm"] { border: 1px solid #1e1e2e !important; }

/* === NOVO SELETOR COMPATÍVEL STREAMLIT NAV (st.radio horizontal) === */
div[data-testid="stHorizontalBlock"] div[data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex;
    justify-content: space-between;
    gap: 6px;
    width: 100%;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label {
    background: #111118 !important;
    border: 1px solid #1e1e2e !important;
    padding: 8px 12px !important;
    border-radius: 20px !important;
    flex: 1;
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    transition: all 0.25s ease;
}
/* Alinhamento do conteúdo selecionado */
div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] {
    background: linear-gradient(135deg, #a855f7, #6366f1) !important;
    border-color: transparent !important;
    color: white !important;
    box-shadow: 0 0 10px rgba(168, 85, 247, 0.4);
}
/* Remove de forma definitiva os radio-buttons circulares nativos */
div[data-testid="stRadio"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"]::before,
div[data-testid="stRadio"] div[role="radiogroup"] label input[type="radio"],
div[data-testid="stRadio"] div[role="radiogroup"] label div[class*="StyledRadio"] {
    display: none !important;
    width: 0px !important;
    height: 0px !important;
    margin: 0px !important;
}

/* === CHECKBOX TOTALMENTE VERDE QUANDO MARCADO === */
div[data-testid="stCheckbox"] label span div {
    border-color: #22c55e !important;
}
div[data-testid="stCheckbox"] input[type="checkbox"]:checked + div {
    background-color: #22c55e !important;
    border-color: #22c55e !important;
}
</style>
""", unsafe_allow_html=True)

# ====================== TEMPLATE DAS TELAS ======================
if st.session_state.tela_atual == "login":
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h1 style="font-family:Bebas Neue,sans-serif;font-size:3rem;letter-spacing:.06em;text-align:center">🏋️‍♂️ MEU TREINO</h1>', unsafe_allow_html=True)
    usuario = st.text_input("Usuário", placeholder="seu.usuario").lower().strip()
    senha = st.text_input("Senha", type="password", max_chars=10)
    
    if st.button("Entrar →", use_container_width=True, type="primary"):
        user = login_usuario(usuario, senha)
        if user:
            st.session_state.usuario_logado = usuario
            st.session_state.perfil = user
            st.session_state.exercicios_custom = {}
            st.query_params["user"] = usuario
            if user.get("treino_em_andamento"):
                try:
                    st.session_state.treino_exercicios = json.loads(user.get("treino_em_andamento"))
                except:
                    st.session_state.treino_exercicios = []
            st.session_state.tela_atual = "dashboard"
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
            
    if st.button("Criar Nova Conta", use_container_width=True):
        st.session_state.tela_atual = "onboarding"
        st.rerun()

elif st.session_state.tela_atual == "onboarding":
    st.markdown('<h1 style="font-family:Bebas Neue,sans-serif;font-size:2.2rem">Vamos configurar o seu perfil</h1>', unsafe_allow_html=True)
    nome     = st.text_input("Nome completo")
    username = st.text_input("Usuário (login)", placeholder="Ex: joao.silva").lower().strip()
    senha    = st.text_input("Senha", type="password", max_chars=10)
    objetivo = st.selectbox("Objetivo Principal", OBJETIVOS)
    dias     = st.selectbox("Dias de treino por semana", [3,4,5,6])
    tempo    = st.selectbox("Tempo por treino", TEMPOS)
    
    if st.button("Concluir Cadastro →", type="primary", use_container_width=True):
        if nome and username and senha:
            novo = criar_usuario(username, senha, nome, objetivo=objetivo, dias=dias, tempo=tempo)
            if novo:
                st.session_state.usuario_logado = username
                st.session_state.perfil = novo
                st.session_state.exercicios_custom = {}
                st.query_params["user"] = username
                st.session_state.tela_atual = "dashboard"
                st.rerun()
                
    if st.button("← Voltar ao login"):
        st.session_state.tela_atual = "login"
        st.rerun()

# ====================== DASHBOARD ======================
else:
    username      = st.session_state.usuario_logado
    perfil        = st.session_state.perfil or {}
    primeiro_nome = (perfil.get("nome", username) or username).split()[0]

    agora_no_fuso = datetime.now(FUSO)
    hora_atual = agora_no_fuso.hour
    minuto_atual = agora_no_fuso.strftime('%M')
    dia_atual = agora_no_fuso.day
    mes_atual = MESES_BR[agora_no_fuso.month]
    
    texto_header = f"{hora_atual}:{minuto_atual} • {dia_atual} de {mes_atual}"

    col_titulo, col_sair = st.columns([8, 1])
    with col_titulo:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#111118,#1a1428);border:1px solid #2a1f3a;'
            'border-radius:18px;padding:20px 24px;">'
            '<div style="color:#888;font-size:0.8rem;">'
            + texto_header +
            '</div><h2 style="margin:8px 0 0 0;">'
            + get_saudacao(hora_atual) + ', ' + primeiro_nome.upper() + '!</h2></div>',
            unsafe_allow_html=True
        )
    with col_sair:
        st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
        if st.button("Sair"):
            st.session_state.tela_atual = "login"
            st.session_state.usuario_logado = None
            st.session_state.perfil = None
            st.session_state.treino_exercicios = []
            st.session_state.exercicios_custom = {}
            st.query_params.clear()
            st.rerun()

    abas = ["🏋️ Treino", "📋 Planos", "📜 Histórico", "📊 Stats", "📐 Medidas", "👤 Perfil"]
    
    if st.session_state.aba_atual not in abas:
        st.session_state.aba_atual = "🏋️ Treino"
        
    idx_inicial = abas.index(st.session_state.aba_atual)

    aba = st.radio(
        "", 
        abas, 
        horizontal=True, 
        label_visibility="collapsed", 
        index=idx_inicial,
        key=f"nav_radio_{st.session_state.aba_atual}" 
    )
    
    if aba != st.session_state.aba_atual:
        st.session_state.aba_atual = aba
        st.rerun()
        
    st.markdown("---")

    # ── ABA TREINO ──────────────────────────────────────────────────────────────
    if st.session_state.aba_atual == "🏋️ Treino":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Registrar Treino de Hoje</h2>', unsafe_allow_html=True)
        treinos_semana = buscar_treinos(username, limit=30)
        render_weekly_tracker(treinos_semana)

        EXERCICIOS = get_exercicios_merged(username)

        grupo = st.selectbox("Grupo Muscular", list(EXERCICIOS.keys()))

        if st.button("➕ Criar Novo Exercício Customizado", use_container_width=True):
            st.session_state.mostrar_form_novo_ex = True

        if st.session_state.mostrar_form_novo_ex:
            st.markdown('<div class="novo-ex-box">', unsafe_allow_html=True)
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;margin-top:0;">Cadastrar Novo Exercício</h3>', unsafe_allow_html=True)

            with st.form("form_novo_exercicio", clear_on_submit=True):
                nome_novo_ex = st.text_input("Nome do exercício", placeholder="Ex: Rosca Scott com Haltere", max_chars=80)
                grupo_novo_ex = st.selectbox("Grupo Muscular", GRUPOS_MUSCULARES, index=GRUPOS_MUSCULARES.index(grupo) if grupo in GRUPOS_MUSCULARES else 0)

                col_salvar_ex, col_cancelar_ex = st.columns(2)
                with col_salvar_ex:
                    salvar_novo = st.form_submit_button("💾 Salvar Exercício", type="primary", use_container_width=True)
                with col_cancelar_ex:
                    cancelar_novo = st.form_submit_button("Cancelar", use_container_width=True)

                if salvar_novo:
                    nome_limpo = nome_novo_ex.strip()
                    if not nome_limpo:
                        st.warning("Digite o nome do exercício.")
                    else:
                        ok, msg = cadastrar_exercicio_custom(username, nome_limpo, grupo_novo_ex)
                        if ok:
                            invalidar_cache_custom()
                            st.session_state.mostrar_form_novo_ex = False
                            st.success(f"✅ \"{nome_limpo}\" adicionado em {grupo_novo_ex}!")
                            st.rerun()
                        else:
                            st.error(f"Erro: {msg}")

                if cancelar_novo:
                    st.session_state.mostrar_form_novo_ex = False
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        opcoes_exercicio = EXERCICIOS[grupo]
        exercicio_sel = st.selectbox("Exercício", opcoes_exercicio)

        if exercicio_sel:
            exercicio = exercicio_sel
            ultimo_peso = get_ultimo_peso(username, exercicio)
            sugestao    = round(ultimo_peso + 2.5, 1) if ultimo_peso > 0 else 0.0

            peso_key     = f"input_peso_{exercicio.replace(' ', '_')}"
            peso_aux_key = f"peso_aux_{exercicio.replace(' ', '_')}"

            if peso_key not in st.session_state:
                st.session_state[peso_key] = sugestao

            if peso_aux_key in st.session_state:
                st.session_state[peso_key] = st.session_state.pop(peso_aux_key)

            c1, c2, c3 = st.columns(3)
            with c1:
                series = st.number_input("Séries", min_value=1, max_value=10, value=3)
            with c2:
                reps = st.number_input("Reps", min_value=1, max_value=50, value=12)
            with c3:
                peso = st.number_input("Peso (kg)", min_value=0.0, max_value=500.0, step=0.5, key=peso_key)

            if ultimo_peso > 0 and st.button("🔄 Usar último peso"):
                st.session_state[peso_aux_key] = ultimo_peso
                st.rerun()

            if st.button("➕ Adicionar Exercício", use_container_width=True, type="primary"):
                st.session_state.treino_exercicios.append({
                    "nome": exercicio, "grupo": grupo,
                    "series": int(series), "reps": int(reps), "peso": float(peso),
                    "feito": False
                })
                persistir_rascunho_treino(username, st.session_state.treino_exercicios)
                st.success(f"{exercicio} adicionado!")
                st.rerun()

        if st.session_state.treino_exercicios:
            st.markdown("---")
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;">EXERCÍCIOS ADICIONADOS / CHECKLIST</h3>', unsafe_allow_html=True)
            
            lista_atualizada = list(st.session_state.treino_exercicios)
            houve_mudanca = False

            for i, ex in enumerate(lista_atualizada):
                col_check, col_texto, col_peso_edit, col_del = st.columns([0.8, 5.2, 3, 1])
                chk_key = f"render_chk_{i}_{ex['nome'].replace(' ', '_')}"
                inp_key = f"render_peso_{i}_{ex['nome'].replace(' ', '_')}"

                with col_check:
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    feito = st.checkbox("", value=bool(ex.get("feito", False)), key=chk_key, label_visibility="collapsed")
                    if feito != ex.get("feito", False):
                        lista_atualizada[i]["feito"] = feito
                        houve_mudanca = True
                        
                with col_texto:
                    classe_css = "ex-card-done" if feito else "ex-card"
                    texto_concluido = " ~~(Feito)~~" if feito else ""
                    st.markdown(
                        f'<div class="{classe_css}"><strong>{ex["nome"]}{texto_concluido}</strong><br>'
                        f'<span style="font-size:0.85rem;color:#888;">{ex["series"]}×{ex["reps"]} séries</span></div>',
                        unsafe_allow_html=True
                    )
                    
                with col_peso_edit:
                    novo_peso = st.number_input("Carga (kg)", min_value=0.0, max_value=500.0, step=0.5, value=float(ex.get("peso", 0.0)), key=inp_key)
                    if novo_peso != ex.get("peso", 0.0):
                        lista_atualizada[i]["peso"] = novo_peso
                        houve_mudanca = True
                        
                with col_del:
                    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑", key=f"del_{i}_{ex['nome']}"):
                        lista_atualizada.pop(i)
                        st.session_state.treino_exercicios = lista_atualizada
                        persistir_rascunho_treino(username, lista_atualizada)
                        st.rerun()

            if houve_mudanca:
                st.session_state.treino_exercicios = lista_atualizada
                persistir_rascunho_treino(username, lista_atualizada)

            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.form("form_finalizar_treino"):
                st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;">FINALIZAR TREINO</h3>', unsafe_allow_html=True)
                duracao = st.number_input("Duração do treino (min)", value=60, min_value=1)
                notas   = st.text_area("Observações (opcional)", placeholder="Como foi o treino hoje?", height=80)
                
                botao_salvar = st.form_submit_button("💾 Salvar Treino", type="primary", use_container_width=True)
                
                if botao_salvar:
                    dados_para_salvar = []
                    for ex_salvar in st.session_state.treino_exercicios:
                        dados_para_salvar.append({
                            "nome": ex_salvar["nome"],
                            "grupo": ex_salvar["grupo"],
                            "series": ex_salvar["series"],
                            "reps": ex_salvar["reps"],
                            "peso": ex_salvar["peso"]
                        })
                        
                    resposta = salvar_treino(username, dados_para_salvar, duracao, notas)
                    if resposta:
                        st.success("Treino salvo com sucesso! 💪")
                        for k in list(st.session_state.keys()):
                            if "render_chk_" in k or "render_peso_" in k:
                                st.session_state.pop(k, None)
                        st.session_state.treino_exercicios = []
                        persistir_rascunho_treino(username, [])
                        st.rerun()
                    else:
                        st.error("Erro ao salvar o treino.")

    # ── ABA PLANOS ──────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "📋 Planos":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Meus Planos de Treino</h2>', unsafe_allow_html=True)
        EXERCICIOS = get_exercicios_merged(username)

        with st.expander("➕ Criar Novo Plano", expanded=False):
            nome_plano  = st.text_input("Nome do plano", placeholder="Ex: Treino A - Peito e Tríceps")
            descricao   = st.text_area("Descrição / Notas", placeholder="Ex: Foco em progressão de carga")
            
            st.markdown("---")
            st.markdown("#### Adicionar Exercícios ao Plano")
            p_grupo = st.selectbox("Grupo Muscular ", list(EXERCICIOS.keys()))
            p_exercicio = st.selectbox("Exercício ", EXERCICIOS[p_grupo])
            
            c1, c2, c3 = st.columns(3)
            with c1:
                p_series = st.number_input("Séries ", min_value=1, max_value=10, value=4)
            with c2:
                p_reps = st.number_input("Reps ", min_value=1, max_value=50, value=10)
            with c3:
                p_peso = st.number_input("Carga Sugerida (kg)", min_value=0.0, step=0.5, value=0.0)
                
            if st.button("➕ Vincular ao Plano"):
                st.session_state.plano_exercicios_tmp.append({
                    "nome": p_exercicio, "grupo": p_grupo,
                    "series": int(p_series), "reps": int(p_reps), "peso": float(p_peso)
                })
                st.success(f"{p_exercicio} adicionado à lista do plano!")
                st.rerun()
                
            if st.session_state.plano_exercicios_tmp:
                st.markdown("##### Exercícios Selecionados:")
                for idx, ex in enumerate(st.session_state.plano_exercicios_tmp):
                    col_t, col_b = st.columns([8, 2])
                    col_t.markdown(f"- **{ex['nome']}** ({ex['grupo']}): {ex['series']}x{ex['reps']} - {ex['peso']}kg")
                    if col_b.button("Remover", key=f"rem_plano_tmp_{idx}"):
                        st.session_state.plano_exercicios_tmp.pop(idx)
                        st.rerun()
                        
                if st.button("💾 Salvar Plano de Treino Completo", type="primary", use_container_width=True):
                    if nome_plano and st.session_state.plano_exercicios_tmp:
                        if salvar_plano(username, nome_plano, descricao, st.session_state.plano_exercicios_tmp):
                            st.success("Plano salvo!")
                            st.session_state.plano_exercicios_tmp = []
                            st.rerun()
                    else:
                        st.error("Preencha o nome e insira pelo menos um exercício.")

        planos = buscar_planos(username)
        if not planos:
            st.info("Nenhum plano cadastrado.")
        else:
            for p in planos:
                with st.container():
                    st.markdown(f'<div class="plano-card"><h3>📋 {p["nome"].upper()}</h3>', unsafe_allow_html=True)
                    if p.get("descricao"):
                        st.markdown(f"*{p['descricao']}*")
                    
                    exs = p.get("exercicios", [])
                    for ex in exs:
                        st.markdown(f"🏋️‍♂️ {ex['nome']} | {ex['series']}x{ex['reps']} — *{ex['peso']} kg*")
                    
                    c_iniciar, c_del = st.columns([7, 3])
                    if c_iniciar.button("⚡ Iniciar este Treino", key=f"start_plano_{p['id']}", use_container_width=True):
                        st.session_state.treino_exercicios = []
                        for ex in exs:
                            st.session_state.treino_exercicios.append({
                                "nome": ex["nome"], "grupo": ex.get("grupo", "Outro"),
                                "series": ex["series"], "reps": ex["reps"], "peso": ex["peso"],
                                "feito": False
                            })
                        persistir_rascunho_treino(username, st.session_state.treino_exercicios)
                        st.session_state.aba_atual = "🏋️ Treino"
                        st.success("Exercícios carregados na aba Treino!")
                        st.rerun()
                        
                    if c_del.button("Deletar Plano", key=f"del_plano_{p['id']}", use_container_width=True):
                        if deletar_plano(p["id"]):
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # ── ABA HISTÓRICO ───────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "📜 Histórico":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Meus Treinos Anteriores</h2>', unsafe_allow_html=True)
        treinos = buscar_treinos(username, limit=50)
        
        if not treinos:
            st.info("Você ainda não registrou nenhum treino.")
        else:
            for t in treinos:
                dt = datetime.strptime(t["data"], "%Y-%m-%d")
                data_formatada = f"{dt.day} de {MESES_BR[dt.month]} de {dt.year}"
                
                with st.container():
                    st.markdown(
                        f'<div class="hist-card"><div style="display:flex;justify-content:between;align-items:center;">'
                        f'<div><span style="color:#a855f7;font-weight:bold;font-size:1.1rem;">⚡ TREINO REALIZADO</span><br>'
                        f'<span style="color:#666;font-size:0.85rem;">{data_formatada} • 🕒 {t.get("duracao_min", 0)} min</span></div>'
                        f'</div><br>', 
                        unsafe_allow_html=True
                    )
                    
                    if t.get("notas"):
                        st.markdown(f"📝 *Observações: {t['notas']}*")
                        
                    exs = t.get("exercicios", [])
                    if exs:
                        df_ex = pd.DataFrame(exs)
                        if "peso" in df_ex.columns:
                            df_ex["peso"] = df_ex["peso"].astype(str) + " kg"
                        st.dataframe(df_ex[["nome", "grupo", "series", "reps", "peso"]].rename(
                            columns={"nome":"Exercício","grupo":"Grupo","series":"Séries","reps":"Reps","peso":"Carga"}
                        ), use_container_width=True, hide_index=True)
                        
                    if st.button("Deletar Registro", key=f"del_treino_{t['id']}", type="secondary"):
                        if deletar_treino(t["id"]):
                            st.success("Registro removido.")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # ── ABA STATS ───────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "📊 Stats":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Estatísticas e Evolução</h2>', unsafe_allow_html=True)
        stats = get_stats_gerais(username)
        
        if not stats:
            st.info("Sem dados suficientes para gerar estatísticas.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="stat-card"><span style="font-size:2rem;font-weight:bold;color:#a855f7;">{stats["total_treinos"]}</span><br><span style="font-size:0.8rem;color:#888;">Treinos Totais</span></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="stat-card"><span style="font-size:2rem;font-weight:bold;color:#22c55e;">{stats["total_horas"]}h</span><br><span style="font-size:0.8rem;color:#888;">Tempo Dedicado</span></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="stat-card"><span style="font-size:2rem;font-weight:bold;color:#3b82f6;">{stats["total_series"]}</span><br><span style="font-size:0.8rem;color:#888;">Séries Feitas</span></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="stat-card"><span style="font-size:2rem;font-weight:bold;color:#f59e0b;">{stats["streak"]} 🔥</span><br><span style="font-size:0.8rem;color:#888;">Frequência Atual</span></div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### Distribuição por Grupo Muscular")
            
            if stats["grupos_count"]:
                df_grupos = pd.DataFrame(list(stats["grupos_count"].items()), columns=["Grupo", "Quantidade"])
                chart_pizza = alt.Chart(df_grupos).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="Quantidade", type="quantitative"),
                    color=alt.Color(field="Grupo", type="nominal", scale=alt.Scale(scheme="purpleorange")),
                    tooltip=["Grupo", "Quantidade"]
                ).properties(height=300)
                st.altair_chart(chart_pizza, use_container_width=True)
                
            st.markdown("### Análise de Carga por Exercício")
            EXERCICIOS = get_exercicios_merged(username)
            g_sel = st.selectbox("Filtrar Grupo para Gráfico", list(EXERCICIOS.keys()))
            ex_sel = st.selectbox("Escolha o Exercício", EXERCICIOS[g_sel])
            
            if ex_sel:
                df_ev = get_evolucao_carga(username, ex_sel)
                if df_ev.empty:
                    st.info("Ainda sem registros com carga para esse exercício.")
                else:
                    df_ev["data"] = df_ev["data"].astype(str)
                    chart_linha = alt.Chart(df_ev).mark_line(point=True, color="#a855f7").encode(
                        x=alt.X("data:N", title="Data"),
                        y=alt.Y("peso:Q", title="Carga Máxima (kg)"),
                        tooltip=["data", "peso", "series", "reps"]
                    ).properties(height=300)
                    st.altair_chart(chart_linha, use_container_width=True)

    # ── ABA MEDIDAS ─────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "📐 Medidas":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Acompanhamento Corporal</h2>', unsafe_allow_html=True)
        
        with st.expander("📐 Registrar Novas Medidas", expanded=False):
            with st.form("form_medidas", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                p_atual = col1.number_input("Peso (kg) *", min_value=10.0, max_value=300.0, step=0.1, value=80.0)
                bf_atual = col2.number_input("Percentual de Gordura (% BF)", min_value=0.0, max_value=80.0, step=0.1, value=0.0)
                cint = col3.number_input("Cintura (cm)", min_value=0.0, step=0.1, value=0.0)
                
                col4, col5, col6 = st.columns(3)
                b_dir = col4.number_input("Braço Direito (cm)", min_value=0.0, step=0.1, value=0.0)
                b_esq = col5.number_input("Braço Esquerdo (cm)", min_value=0.0, step=0.1, value=0.0)
                peit = col6.number_input("Peitoral (cm)", min_value=0.0, step=0.1, value=0.0)
                
                col7, col8, col9 = st.columns(3)
                cx_dir = col7.number_input("Coxa Direita (cm)", min_value=0.0, step=0.1, value=0.0)
                cx_esq = col8.number_input("Coxa Esquerda (cm)", min_value=0.0, step=0.1, value=0.0)
                quad = col9.number_input("Quadril (cm)", min_value=0.0, step=0.1, value=0.0)
                
                col10, col11 = st.columns(2)
                p_dir = col10.number_input("Panturrilha Direita (cm)", min_value=0.0, step=0.1, value=0.0)
                p_esq = col11.number_input("Panturrilha Esquerda (cm)", min_value=0.0, step=0.1, value=0.0)
                
                omb = st.number_input("Ombro (cm)", min_value=0.0, step=0.1, value=0.0)
                
                salvar_m = st.form_submit_button("💾 Salvar Medidas", type="primary", use_container_width=True)
                
                if salvar_m:
                    res = salvar_medidas(
                        username, p_atual, cint if cint>0 else None, b_dir if b_dir>0 else None, b_esq if b_esq>0 else None,
                        bf_atual if bf_atual>0 else None, cx_dir if cx_dir>0 else None, cx_esq if cx_esq>0 else None,
                        p_dir if p_dir>0 else None, p_esq if p_esq>0 else None, quad if quad>0 else None, peit if peit>0 else None, omb if omb>0 else None
                    )
                    if res:
                        st.success("Medidas corporais registradas!")
                        st.rerun()

        historico_medidas = buscar_historico_medidas(username)
        if not historico_medidas:
            st.info("Nenhuma medida cadastrada até agora.")
        else:
            df_medidas = pd.DataFrame(historico_medidas)
            
            st.markdown("### Gráfico de Evolução de Peso")
            df_peso = df_medidas[["data_registro", "peso"]].copy()
            df_peso["data_registro"] = df_peso["data_registro"].astype(str)
            chart_peso = alt.Chart(df_peso).mark_line(point=True, color="#22c55e").encode(
                x=alt.X("data_registro:N", title="Data"),
                y=alt.Y("peso:Q", title="Peso (kg)", scale=alt.Scale(zero=False)),
                tooltip=["data_registro", "peso"]
            ).properties(height=250)
            st.altair_chart(chart_peso, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### Histórico de Medidas")
            for m in historico_medidas:
                dt_m = datetime.strptime(m["data_registro"], "%Y-%m-%d")
                data_m_formatada = f"{dt_m.day} de {MESES_BR[dt_m.month]} de {dt_m.year}"
                
                with st.expander(f"📋 Registro de {data_m_formatada} — {m['peso']} kg"):
                    c_l, c_r = st.columns(2)
                    with c_l:
                        st.write(f"**Peso:** {m['peso']} kg")
                        if m.get("percentual_gordura"): st.write(f"**BF (%):** {m['percentual_gordura']}%")
                        if m.get("cintura"): st.write(f"**Cintura:** {m['cintura']} cm")
                        if m.get("peito"): st.write(f"**Peitoral:** {m['peito']} cm")
                        if m.get("ombro"): st.write(f"**Ombro:** {m['ombro']} cm")
                        if m.get("quadril"): st.write(f"**Quadril:** {m['quadril']} cm")
                    with c_r:
                        if m.get("braço_direito") or m.get("braço_esquerdo"):
                            st.write(f"**Braço (D/E):** {m.get('braço_direito','-')}cm / {m.get('braço_esquerdo','-')}cm")
                        if m.get("coxa_direita") or m.get("coxa_esquerda"):
                            st.write(f"**Coxa (D/E):** {m.get('coxa_direita','-')}cm / {m.get('coxa_esquerda','-')}cm")
                        if m.get("panturrilha_direita") or m.get("panturrilha_esquerda"):
                            st.write(f"**Panturrilha (D/E):** {m.get('panturrilha_direita','-')}cm / {m.get('panturrilha_esquerda','-')}cm")
                    
                    if st.button("Deletar Medida", key=f"del_med_{m['id']}", type="secondary"):
                        if deletar_medida(m["id"]):
                            st.success("Medida removida.")
                            st.rerun()

    # ── ABA PERFIL ──────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "👤 Perfil":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Configurações do Meu Perfil</h2>', unsafe_allow_html=True)
        
        # MELHORIA: Envelopado dentro de um expander para não poluir a tela caso cresça muito
        with st.expander("🛠️ Ver / Gerenciar Exercícios Customizados", expanded=False):
            st.markdown("### Meus Exercícios Customizados")
            EXERCICIOS_RAW = buscar_exercicios_custom_raw(username)
            
            if not EXERCICIOS_RAW:
                st.info("Você ainda não criou nenhum exercício personalizado.")
            else:
                # Agrupando localmente para exibição estruturada
                grupos_vistos = {}
                for row in EXERCICIOS_RAW:
                    g = row["grupo"]
                    if g not in grupos_vistos:
                        grupos_vistos[g] = []
                    grupos_vistos[g].append(row)
                    
                for grupo_c, rows_c in grupos_vistos.items():
                    st.markdown(f"**{grupo_c}**")
                    for ex_row in rows_c:
                        id_c = ex_row["id"]
                        nome_c = ex_row["nome"]
                        
                        col_ex_nome, col_btn_edit, col_btn_del = st.columns([6, 2, 2])
                        
                        # Verifica se este exercício específico está em modo de edição
                        if st.session_state.editando_ex_id == id_c:
                            with col_ex_nome:
                                novo_nome_input = st.text_input("Novo nome", value=nome_c, key=f"edit_inp_{id_c}", label_visibility="collapsed")
                            with col_btn_edit:
                                if st.button("💾", key=f"save_ex_{id_c}", help="Salvar Alteração"):
                                    if novo_nome_input.strip() and novo_nome_input.strip() != nome_c:
                                        if atualizar_exercicio_custom(id_c, novo_nome_input.strip()):
                                            invalidar_cache_custom()
                                            st.session_state.editando_ex_id = None
                                            st.rerun()
                                    else:
                                        st.session_state.editando_ex_id = None
                                        st.rerun()
                            with col_btn_del:
                                if st.button("❌", key=f"cancel_ex_{id_c}", help="Cancelar"):
                                    st.session_state.editando_ex_id = None
                                    st.rerun()
                        else:
                            col_ex_nome.write(f"   - {nome_c}")
                            if col_btn_edit.button("Editar ✏️", key=f"btn_edit_trigger_{id_c}"):
                                st.session_state.editando_ex_id = id_c
                                st.rerun()
                            if col_btn_del.button("Remover", key=f"del_custom_list_{id_c}"):
                                if deletar_exercicio_custom(username, nome_c, grupo_c):
                                    invalidar_cache_custom()
                                    st.success(f"Removido: {nome_c}")
                                    st.rerun()

        st.markdown("---")
        st.markdown("### Dados da Conta")
        
        if not st.session_state.editando_perfil:
            st.write(f"**Nome:** {perfil.get('nome')}")
            st.write(f"**Objetivo:** {perfil.get('objetivo')}")
            st.write(f"**Frequência Desejada:** {perfil.get('dias_por_semana')} dias na semana")
            st.write(f"**Tempo Disponível:** {perfil.get('tempo_disponivel')}")
            
            if st.button("✏️ Editar Parâmetros do Perfil", use_container_width=True):
                st.session_state.editando_perfil = True
                st.rerun()
        else:
            with st.form("form_editar_perfil"):
                n_nome = st.text_input("Nome completo", value=perfil.get("nome",""))
                n_obj  = st.selectbox("Objetivo", OBJETIVOS, index=OBJETIVOS.index(perfil.get("objetivo")) if perfil.get("objetivo") in OBJETIVOS else 0)
                n_dias = st.selectbox("Dias por semana", [3,4,5,6], index=[3,4,5,6].index(perfil.get("dias_por_semana")) if perfil.get("dias_por_semana") in [3,4,5,6] else 0)
                n_temp = st.selectbox("Tempo disponível", TEMPOS, index=TEMPOS.index(perfil.get("tempo_disponivel")) if perfil.get("tempo_disponivel") in TEMPOS else 0)
                
                c_salvar, c_cancelar = st.columns(2)
                if c_salvar.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                    res_p = atualizar_perfil(username, n_nome, n_obj, n_dias, n_temp)
                    if res_p:
                        st.session_state.perfil = res_p
                        st.session_state.editando_perfil = False
                        st.success("Perfil updated!")
                        st.rerun()
                        
                if c_cancelar.form_submit_button("Cancelar", use_container_width=True):
                    st.session_state.editando_perfil = False
                    st.rerun()
