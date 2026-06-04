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

def atualizar_perfil(username, nome, objetivo, dias, tempo):
    try:
        r = supabase.table("perfis").update({
            "nome": nome, "objetivo": objetivo,
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

def buscar_exercicios_custom(username):
    try:
        r = supabase.table("exercicios_custom").select("*").eq("username", username).order("nome").execute()
        resultado = {}
        for row in (r.data or []):
            grupo = row["grupo"]
            if grupo not in resultado:
                resultado[grupo] = []
            resultado[grupo].append(row["nome"])
        return resultado
    except Exception as e:
        st.error(f"Erro ao buscar exercícios custom: {e}")
        return {}

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

# ====================== CSS ======================
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
    opacity: 0.5;
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
    background:#111118; border:1px solid #2a1f3a;
    border-left:4px solid #e53935; border-radius:14px;
    padding:16px 18px; margin-bottom:16px;
}
div[data-testid="stForm"] { border: 1px solid #1e1e2e !important; }
</style>
""", unsafe_allow_html=True)

# ====================== TEMPLATE DAS TELAS ======================
if st.session_state.tela_atual == "login":
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h1 style="font-family:Bebas Neue,sans-serif;font-size:3rem;letter-spacing:.06em;text-align:center">🏋️‍♂️ MEU TREINO</h1>', unsafe_allow_html=True)
    usuario = st.text_input("Usuário", placeholder="edigar.silva").lower().strip()
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
    st.markdown('<h1 style="font-family:Bebas Neue,sans-serif;font-size:2.2rem">Vamos configure o seu perfil</h1>', unsafe_allow_html=True)
    nome     = st.text_input("Nome completo")
    username = st.text_input("Usuário (login)", placeholder="edigar.silva").lower().strip()
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
        if st.button("Sair"):
            st.session_state.tela_atual = "login"
            st.session_state.usuario_logado = None
            st.session_state.perfil = None
            st.session_state.treino_exercicios = []
            st.session_state.exercicios_custom = {}
            st.query_params.clear()
            st.rerun()

    abas = ["🏋️ Treino", "📅 Planos", "📋 Histórico", "📊 Stats", "⚖️ Medidas", "👤 Perfil"]
    
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

        opcoes_exercicio = EXERCICIOS[grupo] + ["➕ Criar novo exercício..."]
        exercicio_sel = st.selectbox("Exercício", opcoes_exercicio)

        if exercicio_sel != "➕ Criar novo exercício...":
            st.session_state.mostrar_form_novo_ex = False

        if exercicio_sel == "➕ Criar novo exercício...":
            st.session_state.mostrar_form_novo_ex = True

        if st.session_state.mostrar_form_novo_ex:
            st.markdown('<div class="novo-ex-box">', unsafe_allow_html=True)
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;margin-top:0;">Cadastrar Novo Exercício</h3>', unsafe_allow_html=True)

            with st.form("form_novo_exercicio", clear_on_submit=True):
                nome_novo_ex = st.text_input(
                    "Nome do exercício",
                    placeholder="Ex: Rosca Scott com Haltere",
                    max_chars=80,
                )
                grupo_novo_ex = st.selectbox(
                    "Grupo Muscular",
                    GRUPOS_MUSCULARES,
                    index=GRUPOS_MUSCULARES.index(grupo) if grupo in GRUPOS_MUSCULARES else 0,
                    key="grupo_novo_ex_select"
                )

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

        if not st.session_state.mostrar_form_novo_ex and exercicio_sel != "➕ Criar novo exercício...":
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
                    novo_peso = st.number_input(
                        "Carga (kg)", 
                        min_value=0.0, 
                        max_value=500.0, 
                        step=0.5, 
                        value=float(ex.get("peso", 0.0)),
                        key=inp_key
                    )
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
                        st.success("Treino salvo! 💪")
                        for k in list(st.session_state.keys()):
                            if "render_chk_" in k or "render_peso_" in k:
                                st.session_state.pop(k, None)
                        st.session_state.treino_exercicios = []
                        persistir_rascunho_treino(username, [])
                        st.rerun()
                    else:
                        st.error("Erro ao salvar o treino.")

    # ── ABA PLANOS ──────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "📅 Planos":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Meus Planos de Treino</h2>', unsafe_allow_html=True)

        EXERCICIOS = get_exercicios_merged(username)

        with st.expander("➕ Criar Novo Plano", expanded=False):
            nome_plano  = st.text_input("Nome do plano", placeholder="Ex: Treino A - Peito e Tríceps")
            descricao   = st.text_input("Descrição", placeholder="Ex: Foco em hipertrofia")

            grupo_p     = st.selectbox("Grupo Muscular", list(EXERCICIOS.keys()), key="plano_grupo")
            exercicio_p = st.selectbox("Exercício", EXERCICIOS[grupo_p], key="plano_ex")
            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                series_p = st.number_input("Séries", 1, 10, 3, key="plano_series")
            with cp2:
                reps_p = st.number_input("Reps", 1, 50, 12, key="plano_reps")
            with cp3:
                peso_p = st.number_input("Peso ref. (kg)", 0.0, 500.0, 0.0, 0.5, key="plano_peso")

            if st.button("➕ Adicionar ao Plano", use_container_width=True):
                st.session_state.plano_exercicios_tmp.append({
                    "nome": exercicio_p, "grupo": grupo_p,
                    "series": int(series_p), "reps": int(reps_p), "peso": float(peso_p)
                })
                st.rerun()

            if st.session_state.plano_exercicios_tmp:
                st.markdown("**Exercícios no plano:**")
                for i, ex in enumerate(st.session_state.plano_exercicios_tmp):
                    cp_a, cp_b = st.columns([9, 1])
                    with cp_a:
                        st.markdown(
                            '<div class="ex-card"><strong>' + ex["nome"] + '</strong><br>'
                            + str(ex["series"]) + '×' + str(ex["reps"]) + ' @ ' + str(ex["peso"]) + 'kg</div>',
                            unsafe_allow_html=True
                        )
                    with cp_b:
                        if st.button("🗑", key="pdel" + str(i)):
                            st.session_state.plano_exercicios_tmp.pop(i)
                            st.rerun()

                col_salvar, col_limpar = st.columns(2)
                with col_salvar:
                    if st.button("💾 Salvar Plano", type="primary", use_container_width=True):
                        if nome_plano:
                            salvar_plano(username, nome_plano, descricao, st.session_state.plano_exercicios_tmp)
                            st.success("Plano salvo!")
                            st.session_state.plano_exercicios_tmp = []
                            st.rerun()
                        else:
                            st.warning("Dê um nome ao plano.")
                with col_limpar:
                    if st.button("🗑 Limpar tudo", use_container_width=True):
                        st.session_state.plano_exercicios_tmp = []
                        st.rerun()

        st.markdown("### Planos Salvos")
        planos = buscar_planos(username)
        if not planos:
            st.info("Nenhum plano criado ainda.")
        else:
            for plano in planos:
                with st.container():
                    st.markdown(
                        '<div class="plano-card">'
                        '<strong style="font-size:1.05rem;">' + plano.get("nome", "") + '</strong><br>'
                        '<span style="color:#888;font-size:0.85rem;">' + (plano.get("descricao") or "") + '</span>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    exs = plano.get("exercicios", [])
                    for ex in exs:
                        st.markdown(
                            '<div style="padding:6px 12px;margin-bottom:4px;background:#1a1a28;border-radius:8px;font-size:0.9rem;">'
                            + ex.get("nome","") + ' — ' + str(ex.get("series","")) + '×' + str(ex.get("reps",""))
                            + (' @ ' + str(ex.get("peso","")) + 'kg' if ex.get("peso",0) > 0 else "")
                            + '</div>',
                            unsafe_allow_html=True
                        )

                    col_usar, col_del = st.columns([3, 1])
                    with col_usar:
                        if st.button("▶️ Usar este plano hoje", key="usar_" + str(plano["id"]), use_container_width=True, type="primary"):
                            st.session_state.treino_exercicios = []
                            for k in list(st.session_state.keys()):
                                if "render_chk_" in k or "render_peso_" in k:
                                    st.session_state.pop(k, None)
                            for e in exs:
                                item = dict(e)
                                item["feito"] = False
                                st.session_state.treino_exercicios.append(item)
                            persistir_rascunho_treino(username, st.session_state.treino_exercicios)
                            st.rerun()
                    with col_del:
                        if st.button("🗑", key="del_plano_" + str(plano["id"]), use_container_width=True):
                            deletar_plano(plano["id"])
                            st.rerun()

    # ── ABA HISTÓRICO ───────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "📋 Histórico":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Histórico de Treinos</h2>', unsafe_allow_html=True)
        treinos = buscar_treinos(username, limit=50)
        
        if not treinos:
            st.info("Você ainda não registrou nenhum treino.")
        else:
            for t in treinos:
                dt = datetime.strptime(t["data"], "%Y-%m-%d")
                dt_str = f"{dt.day} de {MESES_BR[dt.month]} de {dt.year}"
                
                with st.container():
                    st.markdown(
                        f'<div class="hist-card">'
                        f'<div style="display:flex;justify-content:between;align-items:center;">'
                        f'<strong style="font-size:1.1rem;color:#FFA500;">⏱️ {t.get("duracao_min", 60)} min</strong>'
                        f'<span style="color:#666;font-size:0.85rem;margin-left:auto;">{dt_str}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    if t.get("notas"):
                        st.markdown(f'<div style="color:#aaa;font-size:0.9rem;font-style:italic;margin:6px 0;">💬 {t["notas"]}</div>', unsafe_allow_html=True)
                    
                    exs = t.get("exercicios", [])
                    for ex in exs:
                        st.markdown(
                            f'<div style="font-size:0.9rem;padding:2px 0;">'
                            f'• <strong>{ex.get("nome","")}</strong>: {ex.get("series")}×{ex.get("reps")} @ {ex.get("peso")}kg'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                    # ── BOTÕES DO CARD ──────────────────────────────────────────
                    col_salvar_plano, col_deletar = st.columns([3, 1])

                    with col_salvar_plano:
                        chave_toggle = f"mostrar_salvar_plano_{t['id']}"

                        if chave_toggle not in st.session_state:
                            st.session_state[chave_toggle] = False

                        if not st.session_state[chave_toggle]:
                            if st.button("📋 Salvar como Plano", key=f"btn_plano_{t['id']}", use_container_width=True):
                                st.session_state[chave_toggle] = True
                                st.rerun()
                        else:
                            with st.form(f"form_plano_{t['id']}"):
                                nome_plano_hist = st.text_input(
                                    "Nome do plano",
                                    value=f"Treino {dt_str}",
                                    placeholder="Ex: Treino de Pernas",
                                )
                                desc_plano_hist = st.text_input(
                                    "Descrição (opcional)",
                                    placeholder="Ex: Foco em volume",
                                )
                                col_conf, col_canc = st.columns(2)
                                with col_conf:
                                    confirmar = st.form_submit_button("💾 Confirmar", type="primary", use_container_width=True)
                                with col_canc:
                                    cancelar = st.form_submit_button("Cancelar", use_container_width=True)

                                if confirmar:
                                    if nome_plano_hist.strip():
                                        exercicios_plano = [
                                            {k: ex[k] for k in ("nome", "grupo", "series", "reps", "peso") if k in ex}
                                            for ex in exs
                                        ]
                                        resultado = salvar_plano(username, nome_plano_hist.strip(), desc_plano_hist.strip(), exercicios_plano)
                                        if resultado:
                                            st.success(f'Plano "{nome_plano_hist}" salvo! Veja na aba 📅 Planos.')
                                            st.session_state[chave_toggle] = False
                                            st.rerun()
                                    else:
                                        st.warning("Digite um nome para o plano.")

                                if cancelar:
                                    st.session_state[chave_toggle] = False
                                    st.rerun()

                    with col_deletar:
                        if st.button("Deletar", key=f"del_t_{t['id']}", use_container_width=True, type="secondary"):
                            if deletar_treino(t["id"]):
                                st.rerun()

    # ── ABA STATS ───────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "📊 Stats":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Estatísticas e Cargas</h2>', unsafe_allow_html=True)
        stats = get_stats_gerais(username)
        
        TODOS_EXERCICIOS_MERGED = sorted({e for lst in get_exercicios_merged(username).values() for e in lst})

        if not stats:
            st.info("Dados insuficientes para gerar relatórios.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f'<div class="stat-card"><span style="font-size:0.8rem;color:#888;">TREINOS</span><br><strong style="font-size:1.8rem;color:#a855f7;">{stats["total_treinos"]}</strong></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="stat-card"><span style="font-size:0.8rem;color:#888;">HORAS</span><br><strong style="font-size:1.8rem;color:#22c55e;">{stats["total_horas"]}h</strong></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="stat-card"><span style="font-size:0.8rem;color:#888;">SÉRIES TOTAL</span><br><strong style="font-size:1.8rem;color:#3b82f6;">{stats["total_series"]}</strong></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="stat-card"><span style="font-size:0.8rem;color:#888;">STREAK</span><br><strong style="font-size:1.8rem;color:#f59e0b;">🔥 {stats["streak"]}</strong></div>', unsafe_allow_html=True)
                
            st.markdown("### Evolução de Carga")
            ex_alvo = st.selectbox("Selecione o Exercício para o Gráfico", TODOS_EXERCICIOS_MERGED)
            df_carga = get_evolucao_carga(username, ex_alvo)
            
            if df_carga.empty:
                st.warning("Sem registros de peso significativos para este exercício.")
            else:
                df_carga["data"] = pd.to_datetime(df_carga["data"])
                chart = alt.Chart(df_carga).mark_line(point=True, color="#FFA500").encode(
                    x=alt.X("data:T", title="Data"),
                    y=alt.Y("peso:Q", title="Carga máxima (kg)"),
                    tooltip=["data", "peso", "series", "reps"]
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)

    # ── ABA MEDIDAS ─────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "⚖️ Medidas":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Histórico Corporal</h2>', unsafe_allow_html=True)

        with st.expander("📝 Registrar Novas Medidas", expanded=False):
            with st.form("form_medidas"):
                peso_m = st.number_input("Peso Atual (kg)", min_value=10.0, max_value=300.0, value=75.0, step=0.1)
                bf_m = st.number_input("Percentual de Gordura / BF (%)", 0.0, 70.0, 0.0, 0.1)
                c1, c2 = st.columns(2)
                with c1:
                    ombro_m  = st.number_input("Ombro (cm)", 0.0, 250.0, 0.0, 0.5)
                    peito_m  = st.number_input("Peitoral (cm)", 0.0, 250.0, 0.0, 0.5)
                    braco_d  = st.number_input("Braço Direito (cm)", 0.0, 80.0, 0.0, 0.5)
                    coxa_d   = st.number_input("Coxa Direita (cm)", 0.0, 120.0, 0.0, 0.5)
                    pant_d   = st.number_input("Panturrilha Direita (cm)", 0.0, 80.0, 0.0, 0.5)
                with c2:
                    cintura_m = st.number_input("Cintura (cm)", 0.0, 200.0, 0.0, 0.5)
                    quadril_m = st.number_input("Quadril (cm)", 0.0, 200.0, 0.0, 0.5)
                    braco_e   = st.number_input("Braço Esquerdo (cm)", 0.0, 80.0, 0.0, 0.5)
                    coxa_e    = st.number_input("Coxa Esquerda (cm)", 0.0, 120.0, 0.0, 0.5)
                    pant_e    = st.number_input("Panturrilha Esquerda (cm)", 0.0, 80.0, 0.0, 0.5)
                if st.form_submit_button("💾 Guardar Avaliação", type="primary", use_container_width=True):
                    if salvar_medidas(username, peso_m, cintura_m, braco_d, braco_e, bf_m, coxa_d, coxa_e, pant_d, pant_e, quadril_m, peito_m, ombro_m):
                        st.success("Avaliação salva com sucesso!")
                        st.rerun()

        medidas_hist = buscar_historico_medidas(username)

        if not medidas_hist:
            st.info("Nenhuma medida cadastrada até agora.")
        else:
            CAMPOS_MEDIDAS = {
                "peso":               ("⚖️ Peso", "kg"),
                "percentual_gordura": ("🔥 BF", "%"),
                "ombro":              ("🏔️ Ombro", "cm"),
                "peito":              ("🫁 Peito", "cm"),
                "cintura":            ("📏 Cintura", "cm"),
                "quadril":            ("🍑 Quadril", "cm"),
                "braço_direito":      ("💪 Braço Dir.", "cm"),
                "braço_esquerdo":     ("💪 Braço Esq.", "cm"),
                "coxa_direita":       ("🦵 Coxa Dir.", "cm"),
                "coxa_esquerda":      ("🦵 Coxa Esq.", "cm"),
                "panturrilha_direita":("🦶 Pant. Dir.", "cm"),
                "panturrilha_esquerda":("🦶 Pant. Esq.", "cm"),
            }

            medidas_ord = list(reversed(medidas_hist))
            primeiro    = medidas_ord[0]
            ultimo      = medidas_ord[-1]

            sub = st.radio("", ["📊 Progresso", "📋 Registros"], horizontal=True,
                           label_visibility="collapsed", key="sub_medidas")
            st.markdown("---")

            if sub == "📊 Progresso":
                pesos_df = pd.DataFrame([
                    {"data": datetime.strptime(m["data_registro"], "%Y-%m-%d"), "peso": float(m["peso"])}
                    for m in medidas_ord if m.get("peso")
                ])
                if not pesos_df.empty:
                    st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;">PESO CORPORAL</h3>', unsafe_allow_html=True)
                    chart_peso = (
                        alt.Chart(pesos_df)
                        .mark_line(point=True, color="#22c55e", strokeWidth=2)
                        .encode(
                            x=alt.X("data:T", title="Data"),
                            y=alt.Y("peso:Q", title="Peso (kg)", scale=alt.Scale(zero=False)),
                            tooltip=[alt.Tooltip("data:T", title="Data"), alt.Tooltip("peso:Q", title="Peso (kg)")]
                        )
                        .properties(height=220)
                    )
                    st.altair_chart(chart_peso, use_container_width=True)

                campos_disponiveis = [
                    (k, v) for k, v in CAMPOS_MEDIDAS.items()
                    if k != "peso" and any(m.get(k) for m in medidas_ord)
                ]
                if campos_disponiveis:
                    st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;">EVOLUÇÃO DE MEDIDAS</h3>', unsafe_allow_html=True)
                    opcoes_label  = [v[0] for _, v in campos_disponiveis]
                    opcoes_chaves = [k for k, _ in campos_disponiveis]
                    sel_label = st.selectbox("Selecione a medida", opcoes_label, key="sel_medida_grafico")
                    sel_campo = opcoes_chaves[opcoes_label.index(sel_label)]
                    unidade   = CAMPOS_MEDIDAS[sel_campo][1]

                    df_med = pd.DataFrame([
                        {"data": datetime.strptime(m["data_registro"], "%Y-%m-%d"), "valor": float(m[sel_campo])}
                        for m in medidas_ord if m.get(sel_campo)
                    ])
                    chart_med = (
                        alt.Chart(df_med)
                        .mark_line(point=True, color="#a855f7", strokeWidth=2)
                        .encode(
                            x=alt.X("data:T", title="Data"),
                            y=alt.Y("valor:Q", title=f"{sel_label} ({unidade})", scale=alt.Scale(zero=False)),
                            tooltip=[alt.Tooltip("data:T", title="Data"), alt.Tooltip("valor:Q", title=f"{sel_label}")]
                        )
                        .properties(height=220)
                    )
                    st.altair_chart(chart_med, use_container_width=True)

                if len(medidas_ord) >= 2:
                    st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;">ANTES vs AGORA</h3>', unsafe_allow_html=True)
                    d_ini = datetime.strptime(primeiro["data_registro"], "%Y-%m-%d")
                    d_fim = datetime.strptime(ultimo["data_registro"],  "%Y-%m-%d")
                    dias_entre = (d_fim - d_ini).days

                    st.markdown(
                        f'<div style="background:#111118;border:1px solid #1e1e2e;border-radius:12px;'
                        f'padding:10px 16px;margin-bottom:16px;font-size:0.85rem;color:#888;">'
                        f'📅 Primeiro registro: <strong style="color:#fff;">'
                        f'{d_ini.day} de {MESES_BR[d_ini.month]} de {d_ini.year}</strong>'
                        f'&nbsp;&nbsp;→&nbsp;&nbsp;'
                        f'Último: <strong style="color:#fff;">'
                        f'{d_fim.day} de {MESES_BR[d_fim.month]} de {d_fim.year}</strong>'
                        f'&nbsp;&nbsp;•&nbsp;&nbsp;{dias_entre} dias de acompanhamento</div>',
                        unsafe_allow_html=True
                    )

                    cards_html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px;">'
                    algum_card = False

                    for campo, (label, unidade) in CAMPOS_MEDIDAS.items():
                        v_ini = primeiro.get(campo)
                        v_fim = ultimo.get(campo)
                        if not v_ini or not v_fim:
                            continue
                        v_ini = float(v_ini)
                        v_fim = float(v_fim)
                        diff  = v_fim - v_ini
                        pct   = (diff / v_ini * 100) if v_ini else 0

                        campos_reduzir = {"cintura", "quadril", "percentual_gordura", "peso"}
                        if campo in campos_reduzir:
                            cor_diff = "#22c55e" if diff < 0 else ("#ef4444" if diff > 0 else "#888")
                        else:
                            cor_diff = "#22c55e" if diff > 0 else ("#ef4444" if diff < 0 else "#888")

                        sinal = "+" if diff > 0 else ""
                        algum_card = True
                        cards_html += (
                            f'<div style="background:#111118;border:1px solid #1e1e2e;border-radius:14px;padding:14px;">'
                            f'<div style="font-size:0.75rem;color:#666;margin-bottom:4px;">{label}</div>'
                            f'<div style="display:flex;justify-content:space-between;align-items:flex-end;">'
                            f'<div>'
                            f'<span style="font-size:0.8rem;color:#555;">Antes </span>'
                            f'<span style="font-size:1rem;color:#aaa;">{v_ini:.1f}{unidade}</span><br>'
                            f'<span style="font-size:0.8rem;color:#555;">Agora </span>'
                            f'<span style="font-size:1.15rem;font-weight:700;color:#fff;">{v_fim:.1f}{unidade}</span>'
                            f'</div>'
                            f'<div style="text-align:right;">'
                            f'<span style="font-size:1rem;font-weight:700;color:{cor_diff};">{sinal}{diff:.1f}{unidade}</span><br>'
                            f'<span style="font-size:0.75rem;color:{cor_diff};">{sinal}{pct:.1f}%</span>'
                            f'</div>'
                            f'</div>'
                            f'</div>'
                        )

                    cards_html += '</div>'
                    if algum_card:
                        st.markdown(cards_html, unsafe_allow_html=True)
                    else:
                        st.info("Registre pelo menos 2 avaliações para ver o comparativo.")
                else:
                    st.info("Registre pelo menos 2 avaliações para ver o progresso completo.")

            else:
                for m in medidas_hist:
                    d_m   = datetime.strptime(m["data_registro"], "%Y-%m-%d")
                    d_str = f"{d_m.day} de {MESES_BR[d_m.month]} de {d_m.year}"
                    with st.container():
                        st.markdown(
                            f'<div class="hist-card">'
                            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px;">'
                            f'<strong style="font-size:1.1rem;color:#22c55e;">⚖️ {m["peso"]} kg</strong>'
                            f'<span style="color:#666;font-size:0.85rem;">{d_str}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if m.get("percentual_gordura"): st.write(f"**BF:** {m['percentual_gordura']}%")
                            if m.get("ombro"):              st.write(f"**Ombro:** {m['ombro']}cm")
                            if m.get("peito"):              st.write(f"**Peito:** {m['peito']}cm")
                            if m.get("cintura"):            st.write(f"**Cintura:** {m['cintura']}cm")
                        with c2:
                            if m.get("braço_direito"):  st.write(f"**Braço Dir:** {m['braço_direito']}cm")
                            if m.get("braço_esquerdo"): st.write(f"**Braço Esq:** {m['braço_esquerdo']}cm")
                            if m.get("quadril"):        st.write(f"**Quadril:** {m['quadril']}cm")
                        with c3:
                            if m.get("coxa_direita"):         st.write(f"**Coxa Dir:** {m['coxa_direita']}cm")
                            if m.get("coxa_esquerda"):        st.write(f"**Coxa Esq:** {m['coxa_esquerda']}cm")
                            if m.get("panturrilha_direita"):  st.write(f"**Pant. Dir:** {m['panturrilha_direita']}cm")
                            if m.get("panturrilha_esquerda"): st.write(f"**Pant. Esq:** {m['panturrilha_esquerda']}cm")
                        st.markdown('</div>', unsafe_allow_html=True)
                        if st.button("Excluir Registro", key=f"del_m_{m['id']}"):
                            if deletar_medida(m["id"]):
                                st.rerun()

    # ── ABA PERFIL ──────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "👤 Perfil":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Meu Perfil</h2>', unsafe_allow_html=True)
        
        if not st.session_state.editando_perfil:
            st.write(f"**Nome:** {perfil.get('nome')}")
            st.write(f"**Usuário:** {perfil.get('username')}")
            st.write(f"**Objetivo:** {perfil.get('objetivo')}")
            st.write(f"**Frequência Semanal:** {perfil.get('dias_por_semana', 4)} dias")
            st.write(f"**Duração Alvo:** {perfil.get('tempo_disponivel')}")
            
            if st.button("📝 Editar Dados", use_container_width=True):
                st.session_state.editando_perfil = True
                st.rerun()

            st.markdown("---")
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;">Meus Exercícios Personalizados</h3>', unsafe_allow_html=True)

            custom = buscar_exercicios_custom(username)
            if not custom:
                st.info("Você ainda não criou nenhum exercício personalizado.")
            else:
                for grupo_c, nomes in custom.items():
                    st.markdown(f"**{grupo_c}**")
                    for nome_c in nomes:
                        col_nome, col_del = st.columns([8, 1])
                        with col_nome:
                            st.markdown(
                                f'<div style="background:#111118;border-left:3px solid #e53935;'
                                f'border-radius:8px;padding:8px 12px;margin-bottom:4px;font-size:0.9rem;">'
                                f'{nome_c}</div>',
                                unsafe_allow_html=True
                            )
                        with col_del:
                            if st.button("🗑", key=f"del_custom_{grupo_c}_{nome_c}"):
                                if deletar_exercicio_custom(username, nome_c, grupo_c):
                                    invalidar_cache_custom()
                                    st.rerun()
        else:
            nome_e = st.text_input("Nome", value=perfil.get("nome", ""))
            obj_e = st.selectbox("Objetivo", OBJETIVOS, index=OBJETIVOS.index(perfil.get("objetivo")) if perfil.get("objetivo") in OBJETIVOS else 0)
            dias_e = st.selectbox("Dias por Semana", [3,4,5,6], index=[3,4,5,6].index(perfil.get("dias_por_semana")) if perfil.get("dias_por_semana") in [3,4,5,6] else 1)
            tempo_e = st.selectbox("Tempo Estimado", TEMPOS, index=TEMPOS.index(perfil.get("tempo_disponivel")) if perfil.get("tempo_disponivel") in TEMPOS else 1)
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
                    up = atualizar_perfil(username, nome_e, obj_e, dias_e, tempo_e)
                    if up:
                        st.session_state.perfil = up
                        st.session_state.editando_perfil = False
                        st.success("Configurações atualizadas!")
                        st.rerun()
            with col_s2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.editando_perfil = False
                    st.rerun()
