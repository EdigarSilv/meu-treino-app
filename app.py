import streamlit as st
from datetime import datetime, date, timedelta
from supabase import create_client, Client
import json
import pandas as pd

# ====================== CONFIGURAÇÕES ======================
SUPABASE_URL = "https://kecmxzamzkgnwlfyadjt.supabase.co"
SUPABASE_KEY = "sb_publishable_Xvf2dMiG6_vKh25LRQFmQA_8efs__ff"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Meu Treino", page_icon="🏋️‍♂️", layout="centered")

# ====================== DADOS ======================
EXERCICIOS = {
    "🦵 Pernas": ["Agachamento Livre","Leg Press","Cadeira Extensora","Mesa Flexora","Stiff","Avanço","Afundo","Panturrilha na Máquina","Hack Squat"],
    "🫁 Peito": ["Supino Reto","Supino Inclinado","Supino Declinado","Crucifixo","Crossover","Peck Deck","Flexão","Pullover"],
    "🔙 Costas": ["Puxada Frontal","Remada Curvada","Remada Unilateral","Levantamento Terra","Serrote","Puxada Fechada","Remada na Máquina","Pull-up"],
    "💪 Bíceps": ["Rosca Direta","Rosca Alternada","Rosca Martelo","Rosca Concentrada","Rosca 21","Rosca na Polia"],
    "💪 Tríceps":["Tríceps Corda","Tríceps Testa","Tríceps Francês","Mergulho","Tríceps na Polia Alta","Tríceps Coice"],
    "🏔️ Ombros": ["Desenvolvimento","Elevação Lateral","Elevação Frontal","Remada Alta","Encolhimento","Crucifixo Inverso"],
    "🎯 Abdômen":["Abdominal Crunch","Prancha","Abdominal Oblíquo","Elevação de Pernas","Abdominal na Máquina","Russian Twist"],
}

TODOS_EXERCICIOS = sorted({e for lst in EXERCICIOS.values() for e in lst})
OBJETIVOS = ["Hipertrofia", "Emagrecimento", "Condicionamento", "Forca"]
TEMPOS = ["45 min", "1h", "1h15", "1h30", "2h"]

# ====================== SESSION STATE ======================
defaults = {
    "tela_atual": "login",
    "usuario_logado": None,
    "perfil": None,
    "treino_exercicios": [],
    "editando_perfil": False,
    "plano_exercicios_tmp": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ====================== FUNÇÕES DO BANCO ======================
def criar_usuario(username, senha, nome, objetivo, dias, tempo):
    try:
        r = supabase.table("perfis").insert({
            "username": username, "nome": nome, "objetivo": objetivo,
            "dias_por_semana": dias, "tempo_disponivel": tempo,
            "onboarding_concluido": True, "senha": senha
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

def salvar_treino(username, exercicios, duracao_min, notas=""):
    try:
        r = supabase.table("treinos").insert({
            "username": username,
            "data": date.today().isoformat(),
            "exercicios": json.dumps(exercicios, ensure_ascii=False),
            "duracao_min": duracao_min,
            "notas": notas,
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao salvar treino: {e}")
        return None

def buscar_treinos(username, limit=200):
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
    except:
        return []

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
                data = datetime.strptime(t["data"], "%Y-%m-%d").date()
                for ex in t.get("exercicios", []):
                    if ex.get("nome") == exercicio_nome and float(ex.get("peso", 0)) > 0:
                        volume = ex.get("series", 0) * ex.get("reps", 0) * float(ex.get("peso", 0))
                        registros.append({
                            "data": data,
                            "peso": float(ex.get("peso", 0)),
                            "volume": volume,
                            "series": ex.get("series"),
                            "reps": ex.get("reps")
                        })
            except:
                continue
        return pd.DataFrame(registros)
    except:
        return pd.DataFrame()

# ====================== COMPONENTES VISUAIS ======================
def get_saudacao():
    hora = datetime.now().hour
    if hora < 12: return "Bom dia"
    elif hora < 18: return "Boa tarde"
    else: return "Boa noite"

def render_weekly_tracker(treinos):
    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    datas_treino = {datetime.strptime(t["data"], "%Y-%m-%d").date() for t in treinos if t.get("data")}

    dias_abrev = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    dias_html = ""

    for i, dia_nome in enumerate(dias_abrev):
        dia_data = inicio_semana + timedelta(days=i)
        is_hoje = dia_data == hoje
        is_futuro = dia_data > hoje

        if is_futuro:
            cor_ponto = "#2a2a3a"
            cor_texto = "#444"
            cor_fundo = "transparent"
            borda = "1px solid #1e1e2e"
        elif dia_data in datas_treino:
            cor_ponto = "#22c55e"
            cor_texto = "#22c55e"
            cor_fundo = "rgba(34,197,94,0.12)"
            borda = "1px solid rgba(34,197,94,0.4)"
        elif is_hoje:
            cor_ponto = "#f59e0b"
            cor_texto = "#f59e0b"
            cor_fundo = "rgba(245,158,11,0.15)"
            borda = "2px solid #f59e0b"
        else:
            cor_ponto = "#ef4444"
            cor_texto = "#ef4444"
            cor_fundo = "rgba(239,68,68,0.08)"
            borda = "1px solid rgba(239,68,68,0.3)"

        sombra = "box-shadow: 0 0 12px rgba(245,158,11,0.4);" if is_hoje else ""
        dias_html += f"""
        <div style="display:flex; flex-direction:column; align-items:center; gap:6px;
                    background:{cor_fundo}; border:{borda}; border-radius:14px;
                    padding:10px 8px; flex:1; {sombra}">
            <div style="width:10px; height:10px; border-radius:50%; background:{cor_ponto};
                        {'box-shadow:0 0 6px ' + cor_ponto + ';' if not is_futuro else ''}"></div>
            <span style="font-size:0.7rem; font-weight:700; color:{cor_texto}; letter-spacing:.05em;">{dia_nome}</span>
            <span style="font-size:0.65rem; color:#666;">{dia_data.strftime('%d')}</span>
        </div>
        """

    st.markdown(f"""
    <div style="margin:20px 0 24px 0;">
        <div style="font-size:0.75rem; color:#666; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; font-weight:600;">
            SEMANA ATUAL
        </div>
        <div style="display:flex; gap:6px;">
            {dias_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ====================== CSS ======================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Nunito:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Nunito', sans-serif; background-color: #0a0a0f; }
h1, h2, h3 { font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 0.04em; }
.ex-card { background:#111118; border-left:4px solid #FFA500; border-radius:12px; padding:14px 16px; margin-bottom:10px; }
.ex-title { font-family:'Bebas Neue',sans-serif; font-size:1.15rem; color:#FFA500; }
.greeting-block { background: linear-gradient(135deg, #111118 0%, #1a1428 100%); border: 1px solid #2a1f3a; border-radius: 18px; padding: 20px 24px; }
</style>
""", unsafe_allow_html=True)

# ====================== TELAS ======================
if st.session_state.tela_atual == "login":
    st.markdown('<h1 style="text-align:center; font-size:3rem;">🏋️‍♂️ MEU TREINO</h1>', unsafe_allow_html=True)
    usuario = st.text_input("Usuário", placeholder="edigar.silva").lower().strip()
    senha = st.text_input("Senha", type="password", max_chars=10)
    
    if st.button("Entrar →", use_container_width=True, type="primary"):
        user = login_usuario(usuario, senha)
        if user:
            st.session_state.usuario_logado = usuario
            st.session_state.perfil = user
            st.session_state.tela_atual = "dashboard"
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

    if st.button("Criar Nova Conta"):
        st.session_state.tela_atual = "onboarding"
        st.rerun()

elif st.session_state.tela_atual == "onboarding":
    st.markdown('<h1 style="font-size:2.3rem">Configurar Perfil</h1>', unsafe_allow_html=True)
    nome = st.text_input("Nome completo")
    username = st.text_input("Usuário", placeholder="edigar.silva").lower().strip()
    senha = st.text_input("Senha", type="password", max_chars=10)
    objetivo = st.selectbox("Objetivo", OBJETIVOS)
    dias = st.selectbox("Dias por semana", [3,4,5,6])
    tempo = st.selectbox("Tempo por treino", TEMPOS)
    
    if st.button("Concluir Cadastro →", type="primary", use_container_width=True):
        if nome and username and senha:
            novo = criar_usuario(username, senha, nome, objetivo, dias, tempo)
            if novo:
                st.session_state.usuario_logado = username
                st.session_state.perfil = novo
                st.session_state.tela_atual = "dashboard"
                st.rerun()
    if st.button("Voltar"):
        st.session_state.tela_atual = "login"
        st.rerun()

# ====================== DASHBOARD ======================
else:
    username = st.session_state.usuario_logado
    perfil = st.session_state.perfil or {}
    primeiro_nome = (perfil.get("nome") or username).split()[0]

    col1, col2 = st.columns([9,1])
    with col1:
        st.markdown(f"""
        <div class="greeting-block">
            <div style="color:#888; font-size:0.8rem;">{datetime.now().strftime('%H:%M')} • {datetime.now().strftime('%d de %B %Y')}</div>
            <h2 style="margin:8px 0 0 0;">{get_saudacao()}, {primeiro_nome.upper()}!</h2>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("Sair"):
            st.session_state.tela_atual = "login"
            st.rerun()

    aba = st.radio("", ["🏋️ Treino", "📅 Planos", "📋 Histórico", "📊 Stats", "👤 Perfil"], 
                   horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    # ====================== TREINO ======================
    if aba == "🏋️ Treino":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Registrar Treino de Hoje</h2>', unsafe_allow_html=True)
        
        treinos_semana = buscar_treinos(username, 30)
        render_weekly_tracker(treinos_semana)

        grupo = st.selectbox("Grupo Muscular", list(EXERCICIOS.keys()))
        exercicio = st.selectbox("Exercício", EXERCICIOS[grupo])

        ultimo_peso = get_ultimo_peso(username, exercicio)
        sugestao = round(ultimo_peso + 2.5, 1) if ultimo_peso > 0 else 0.0

        c1, c2, c3 = st.columns(3)
        with c1: series = st.number_input("Séries", min_value=1, max_value=10, value=3)
        with c2: reps = st.number_input("Repetições", min_value=1, max_value=50, value=12)
        with c3: peso = st.number_input("Peso (kg)", min_value=0.0, max_value=500.0, value=sugestao, step=0.5)

        if ultimo_peso > 0 and st.button("🔄 Usar último peso"):
            peso = ultimo_peso
            st.rerun()

        if st.button("➕ Adicionar Exercício", type="primary", use_container_width=True):
            st.session_state.treino_exercicios.append({
                "nome": exercicio, "grupo": grupo, "series": int(series),
                "reps": int(reps), "peso": float(peso)
            })
            st.success(f"{exercicio} adicionado!")
            st.rerun()

        if st.session_state.treino_exercicios:
            st.markdown("### Exercícios adicionados")
            for i, ex in enumerate(st.session_state.treino_exercicios):
                col_ex, col_del = st.columns([9,1])
                with col_ex:
                    st.markdown(f"""
                    <div class="ex-card">
                        <div class="ex-title">{ex['nome']}</div>
                        <div>{ex['series']} séries × {ex['reps']} reps × {ex['peso']} kg</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    if st.button("🗑", key=f"del_{i}"):
                        st.session_state.treino_exercicios.pop(i)
                        st.rerun()

            duracao = st.number_input("Duração (min)", value=60)
            notas = st.text_area("Observações", placeholder="Como foi o treino?")
            if st.button("💾 Salvar Treino", type="primary", use_container_width=True):
                salvar_treino(username, st.session_state.treino_exercicios, duracao, notas)
                st.success("Treino salvo com sucesso!")
                st.session_state.treino_exercicios = []
                st.rerun()

    # ====================== STATS ======================
    elif aba == "📊 Stats":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;">📈 Evolução de Carga</h2>', unsafe_allow_html=True)
        
        ex_escolhido = st.selectbox("Selecione o exercício", TODOS_EXERCICIOS)
        df = get_evolucao_carga(username, ex_escolhido)

        if df.empty:
            st.info(f"Ainda não há registros para **{ex_escolhido}**.")
        else:
            pr = df["peso"].max()
            pr_data = df.loc[df["peso"].idxmax(), "data"]
            
            c1, c2 = st.columns(2)
            with c1: st.metric("🏆 Recorde Pessoal", f"{pr} kg", f"{pr_data.strftime('%d/%m/%Y')}")
            with c2: st.metric("Total de Registros", len(df))

            chart_data = df.groupby("data").agg({"peso": "max", "volume": "sum"}).reset_index()
            st.line_chart(chart_data.set_index("data"), color=["#FFA500", "#22c55e"])

            with st.expander("Ver tabela completa"):
                df_show = df.copy()
                df_show["data"] = df_show["data"].dt.strftime("%d/%m/%Y")
                st.dataframe(df_show, use_container_width=True, hide_index=True)

    else:
        st.info("Esta aba ainda está em desenvolvimento.")
