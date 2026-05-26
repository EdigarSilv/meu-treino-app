import streamlit as st
from datetime import datetime, date, timedelta
from supabase import create_client, Client
import json

# ====================== SUPABASE ======================
SUPABASE_URL = "https://kecmxzamzkgnwlfyadjt.supabase.co"
SUPABASE_KEY = "sb_publishable_Xvf2dMiG6_vKh25LRQFmQA_8efs__ff"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="meu-treino-app", page_icon="🏋️‍♂️", layout="centered")

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

# ====================== ESTADOS ======================
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

# ====================== FUNÇÕES DB ======================
def criar_usuario(username, senha, nome, objetivo, dias, tempo):
    try:
        r = supabase.table("perfis").insert({
            "username": username, "nome": nome, "objetivo": objetivo,
            "dias_por_semana": dias, "tempo_disponivel": tempo,
            "onboarding_concluido": True, "senha": senha
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao criar conta: {e}"); return None

def login_usuario(username, senha):
    try:
        r = supabase.table("perfis").select("*").eq("username", username).execute()
        if r.data:
            u = r.data[0]
            if u.get("senha") == senha: return u
        return None
    except Exception as e:
        st.error(f"Erro no login: {e}"); return None

def atualizar_perfil(username, nome, objetivo, dias, tempo, senha_nova=None):
    try:
        dados = {"nome": nome, "objetivo": objetivo, "dias_por_semana": dias, "tempo_disponivel": tempo}
        if senha_nova: dados["senha"] = senha_nova
        r = supabase.table("perfis").update(dados).eq("username", username).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao atualizar perfil: {e}"); return None

def salvar_treino(username, exercicios, duracao_min, notas=""):
    try:
        r = supabase.table("treinos").insert({
            "username": username, "data": date.today().isoformat(),
            "exercicios": json.dumps(exercicios, ensure_ascii=False),
            "duracao_min": duracao_min, "notas": notas,
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao salvar treino: {e}"); return None

def buscar_treinos(username, limit=200):
    try:
        r = supabase.table("treinos").select("*").eq("username", username).order("data", desc=True).limit(limit).execute()
        treinos = r.data or []
        for t in treinos:
            if isinstance(t.get("exercicios"), str):
                try: t["exercicios"] = json.loads(t["exercicios"])
                except: t["exercicios"] = []
        return treinos
    except Exception as e:
        st.error(f"Erro ao buscar treinos: {e}"); return []

def deletar_treino(treino_id):
    try:
        supabase.table("treinos").delete().eq("id", treino_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar treino: {e}"); return False

def buscar_planos(username):
    try:
        r = supabase.table("planos").select("*").eq("username", username).order("criado_em", desc=False).execute()
        planos = r.data or []
        for p in planos:
            if isinstance(p.get("exercicios"), str):
                try: p["exercicios"] = json.loads(p["exercicios"])
                except: p["exercicios"] = []
        return planos
    except Exception as e:
        st.error(f"Erro ao buscar planos: {e}"); return []

def salvar_plano(username, nome, descricao, exercicios):
    try:
        r = supabase.table("planos").insert({
            "username": username, "nome": nome, "descricao": descricao,
            "exercicios": json.dumps(exercicios, ensure_ascii=False),
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        st.error(f"Erro ao salvar plano: {e}"); return None

def deletar_plano(plano_id):
    try:
        supabase.table("planos").delete().eq("id", plano_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar plano: {e}"); return False

# ====================== PROGRESSÃO DE CARGA ======================
def get_ultimo_peso(username, exercicio_nome):
    """Retorna o maior peso já registrado para o exercício"""
    try:
        r = supabase.table("treinos")\
            .select("exercicios")\
            .eq("username", username)\
            .order("data", desc=True)\
            .limit(50)\
            .execute()
        
        peso_max = 0.0
        for treino in r.data:
            exercicios = treino.get("exercicios", [])
            if isinstance(exercicios, str):
                exercicios = json.loads(exercicios)
            
            for ex in exercicios:
                if ex.get("nome") == exercicio_nome:
                    peso = float(ex.get("peso", 0))
                    if peso > peso_max:
                        peso_max = peso
        return peso_max
    except:
        return 0.0

# ====================== SAUDAÇÃO ======================
def get_saudacao():
    hora = datetime.now().hour
    if hora < 12: return "Bom dia"
    elif hora < 18: return "Boa tarde"
    else: return "Boa noite"

# ====================== TRACKER SEMANAL (MELHORADO) ======================
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
            cor_ponto = "#f59e0b"  # Laranja para hoje (ainda não treinado)
            cor_texto = "#f59e0b"
            cor_fundo = "rgba(245,158,11,0.12)"
            borda = "2px solid #f59e0b"
        else:
            cor_ponto = "#ef4444"
            cor_texto = "#ef4444"
            cor_fundo = "rgba(239,68,68,0.08)"
            borda = "1px solid rgba(239,68,68,0.3)"

        sombra = "box-shadow: 0 0 12px rgba(245,158,11,0.3);" if is_hoje else ""

        dias_html += f"""
        <div style="display:flex; flex-direction:column; align-items:center; gap:6px;
                    background:{cor_fundo}; border:{borda}; border-radius:14px;
                    padding:10px 8px; flex:1; {sombra}">
            <div style="width:10px; height:10px; border-radius:50%; background:{cor_ponto};
                        {'box-shadow:0 0 6px ' + cor_ponto + ';' if not is_futuro else ''}"></div>
            <span style="font-size:0.7rem; font-weight:700; color:{cor_texto}; letter-spacing:.05em;">
                {dia_nome}
            </span>
            <span style="font-size:0.65rem; color:#666;">
                {dia_data.strftime('%d')}
            </span>
        </div>
        """

    st.markdown(f"""
    <div style="margin:16px 0 20px 0;">
        <div style="font-size:0.72rem; color:#555; text-transform:uppercase; letter-spacing:.12em; margin-bottom:10px;">
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
.metric-card, .ex-card, .plano-card, .hist-card, .greeting-block, .profile-header { border-radius: 18px; }
.ex-title { font-family:'Bebas Neue',sans-serif; font-size:1.1rem; color:#FFA500; }
</style>
""", unsafe_allow_html=True)

# ====================== TELAS ======================
if st.session_state.tela_atual == "login":
    # ... (código de login permanece igual)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h1 style="font-family:Bebas Neue,sans-serif;font-size:3rem;letter-spacing:.06em">🏋️‍♂️ MEU TREINO</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#555;margin-top:-10px;margin-bottom:24px">Registre. Evolua. Domine.</p>', unsafe_allow_html=True)
    
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
            st.error("Usuário não encontrado ou senha incorreta.")
    
    if st.button("Criar Nova Conta", use_container_width=True):
        st.session_state.tela_atual = "onboarding"; st.rerun()

elif st.session_state.tela_atual == "onboarding":
    # ... (onboarding permanece igual)
    st.markdown('<h1 style="font-family:Bebas Neue,sans-serif;font-size:2.2rem">Vamos configurar seu perfil</h1>', unsafe_allow_html=True)
    nome = st.text_input("Nome completo")
    username = st.text_input("Usuário (login)", placeholder="edigar.silva").lower().strip()
    senha = st.text_input("Senha", type="password", max_chars=10)
    objetivo = st.selectbox("Objetivo Principal", OBJETIVOS)
    dias = st.selectbox("Dias de treino por semana", [3,4,5,6])
    tempo = st.selectbox("Tempo por treino", TEMPOS)
    
    if st.button("Concluir Cadastro →", type="primary", use_container_width=True):
        if nome and username and senha:
            novo = criar_usuario(username, senha, nome, objetivo, dias, tempo)
            if novo:
                st.session_state.usuario_logado = username
                st.session_state.perfil = novo
                st.session_state.tela_atual = "dashboard"
                st.rerun()
        else:
            st.warning("Preencha todos os campos.")
    
    if st.button("← Voltar ao login"):
        st.session_state.tela_atual = "login"; st.rerun()

# ====================== DASHBOARD ======================
elif st.session_state.tela_atual == "dashboard":
    username = st.session_state.usuario_logado
    perfil = st.session_state.perfil or {}
    nome_completo = perfil.get("nome", username) if perfil else username
    primeiro_nome = nome_completo.split()[0] if nome_completo else username

    # Saudação
    col_titulo, col_sair = st.columns([8,1])
    with col_titulo:
        saudacao = get_saudacao()
        agora = datetime.now()
        hora_fmt = agora.strftime("%H:%M")
        data_fmt = agora.strftime("%A, %d de %B").capitalize()
        st.markdown(f"""
        <div class="greeting-block">
            <div class="greeting-time">🕐 {hora_fmt} · {data_fmt}</div>
            <div class="greeting-main">{saudacao.upper()}, <span>{primeiro_nome.upper()}!</span></div>
            <div class="greeting-sub">Pronto para mais um treino? 💪</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_sair:
        if st.button("Sair"):
            for k in ["usuario_logado","perfil","treino_exercicios","plano_exercicios_tmp"]:
                st.session_state[k] = None if k not in ["treino_exercicios","plano_exercicios_tmp"] else []
            st.session_state.tela_atual = "login"
            st.rerun()

    abas = ["🏋️ Treino", "📅 Planos", "📋 Histórico", "📊 Stats", "👤 Perfil"]
    aba = st.radio("", abas, horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    # ====================== TREINO ======================
    if aba == "🏋️ Treino":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Registrar Treino de Hoje</h2>', unsafe_allow_html=True)
        
        treinos_semana = buscar_treinos(username, limit=30)
        render_weekly_tracker(treinos_semana)

        # Carregar plano
        planos = buscar_planos(username)
        if planos:
            with st.expander("📥 Carregar a partir de um Plano"):
                nomes_planos = [p["nome"] for p in planos]
                plano_sel = st.selectbox("Selecione o plano", nomes_planos, key="carregar_plano_sel")
                if st.button("Carregar Plano →", use_container_width=True):
                    plano_obj = next((p for p in planos if p["nome"] == plano_sel), None)
                    if plano_obj:
                        st.session_state.treino_exercicios = [
                            {"nome": ex["nome"], "grupo": ex.get("grupo",""), "series": ex.get("series",3), 
                             "reps": ex.get("reps",12), "peso": ex.get("peso",0.0)}
                            for ex in plano_obj.get("exercicios",[])
                        ]
                        st.success(f"Plano '{plano_sel}' carregado!")
                        st.rerun()

        # Seleção de exercício com progressão automática
        grupo = st.selectbox("Grupo Muscular", list(EXERCICIOS.keys()))
        exercicio = st.selectbox("Exercício", EXERCICIOS[grupo])

        ultimo_peso = get_ultimo_peso(username, exercicio)
        sugestao = round(ultimo_peso + 2.5, 1) if ultimo_peso > 0 else 0.0

        c1, c2, c3 = st.columns(3)
        with c1:
            series = st.number_input("Séries", min_value=1, max_value=10, value=3)
        with c2:
            reps = st.number_input("Reps", min_value=1, max_value=50, value=12)
        with c3:
            peso = st.number_input(
                "Peso (kg)", 
                min_value=0.0, 
                max_value=500.0, 
                value=sugestao,
                step=0.5,
                help=f"Último peso: {ultimo_peso} kg → Sugerido: {sugestao} kg"
            )

        if ultimo_peso > 0:
            if st.button("🔄 Usar último peso", use_container_width=True):
                peso = ultimo_peso
                st.rerun()

        if st.button("➕ Adicionar Exercício", use_container_width=True, type="primary"):
            st.session_state.treino_exercicios.append({
                "nome": exercicio,
                "grupo": grupo,
                "series": int(series),
                "reps": int(reps),
                "peso": float(peso)
            })
            st.success(f"✅ {exercicio} adicionado com {peso}kg!")
            st.rerun()

        # Lista de exercícios adicionados
        if st.session_state.treino_exercicios:
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;margin-top:20px">Exercícios do treino</h3>', unsafe_allow_html=True)
            for i, ex in enumerate(st.session_state.treino_exercicios):
                col_ex, col_del = st.columns([10,1])
                with col_ex:
                    vol = ex["series"] * ex["reps"] * ex["peso"]
                    st.markdown(f'''
                    <div class="ex-card">
                        <div class="ex-title">{ex["nome"]}</div>
                        <div class="ex-detail">{ex["series"]}×{ex["reps"]} @ {ex["peso"]}kg — <b>{round(vol):,} kg</b></div>
                    </div>''', unsafe_allow_html=True)
                with col_del:
                    if st.button("🗑", key=f"del_{i}"):
                        st.session_state.treino_exercicios.pop(i)
                        st.rerun()

            st.markdown("---")
            duracao = st.number_input("Duração total (minutos)", min_value=10, max_value=300, value=60)
            notas = st.text_area("Observações", placeholder="Como foi o treino?", height=80)

            if st.button("💾 Salvar Treino", type="primary", use_container_width=True):
                resultado = salvar_treino(username, st.session_state.treino_exercicios, duracao, notas)
                if resultado:
                    st.success("🎉 Treino salvo com sucesso!")
                    st.balloons()
                    st.session_state.treino_exercicios = []
                    st.rerun()
        else:
            st.info("Adicione exercícios para registrar o treino de hoje.")

    # Outras abas (Planos, Histórico, Stats, Perfil) permanecem iguais ao seu código original
    # ... (você pode colar o resto do seu código aqui se quiser, mas para brevidade não repeti tudo)

    else:
        st.info("Funcionalidade em desenvolvimento...")

else:
    st.info("Em desenvolvimento...")
