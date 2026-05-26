import streamlit as st
from datetime import datetime, date, timedelta
from supabase import create_client, Client
import json

# ====================== SUPABASE ======================
SUPABASE_URL = "https://kecmxzamzkgnwlfyadjt.supabase.co"
SUPABASE_KEY = "sb_publishable_Xvf2dMiG6_vKh25LRQFmQA_8efs__ff"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="meu-treino-app", page_icon="🏋️‍♂️", layout="centered")

# ====================== EXERCÍCIOS POR GRUPO ======================
EXERCICIOS = {
    "🦵 Pernas": ["Agachamento Livre","Leg Press","Cadeira Extensora","Mesa Flexora","Stiff","Avanço","Afundo","Panturrilha na Máquina","Hack Squat"],
    "🫁 Peito":  ["Supino Reto","Supino Inclinado","Supino Declinado","Crucifixo","Crossover","Peck Deck","Flexão","Pullover"],
    "🔙 Costas": ["Puxada Frontal","Remada Curvada","Remada Unilateral","Levantamento Terra","Serrote","Puxada Fechada","Remada na Máquina","Pull-up"],
    "💪 Bíceps": ["Rosca Direta","Rosca Alternada","Rosca Martelo","Rosca Concentrada","Rosca 21","Rosca na Polia"],
    "💪 Tríceps":["Tríceps Corda","Tríceps Testa","Tríceps Francês","Mergulho","Tríceps na Polia Alta","Tríceps Coice"],
    "🏔️ Ombros": ["Desenvolvimento","Elevação Lateral","Elevação Frontal","Remada Alta","Encolhimento","Crucifixo Inverso"],
    "🎯 Abdômen":["Abdominal Crunch","Prancha","Abdominal Oblíquo","Elevação de Pernas","Abdominal na Máquina","Russian Twist"],
}
TODOS_EXERCICIOS = sorted({e for lst in EXERCICIOS.values() for e in lst})
OBJETIVOS = ["Hipertrofia", "Emagrecimento", "Condicionamento", "Forca"]
TEMPOS    = ["45 min", "1h", "1h15", "1h30", "2h"]

# ====================== ESTADOS ======================
defaults = {
    "tela_atual": "login",
    "usuario_logado": None,
    "perfil": None,
    "treino_exercicios": [],
    "editando_perfil": False,
    "plano_exercicios_tmp": [],  # exercícios sendo montados no plano
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
        supabase.table("treinos").delete().eq("id", treino_id).execute(); return True
    except Exception as e:
        st.error(f"Erro ao deletar treino: {e}"); return False

# ── PLANOS ──
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
        supabase.table("planos").delete().eq("id", plano_id).execute(); return True
    except Exception as e:
        st.error(f"Erro ao deletar plano: {e}"); return False

# ====================== CSS ======================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Nunito:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Nunito', sans-serif; background-color: #0a0a0f; }
h1, h2, h3 { font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 0.04em; }
div[role="radiogroup"] > label { border-radius: 99px !important; padding: 6px 18px !important; font-weight: 600 !important; font-size: 0.85rem !important; }
.metric-card { background:#111118; border:1px solid #222230; border-radius:18px; padding:18px 12px; text-align:center; position:relative; overflow:hidden; }
.metric-card::before { content:''; position:absolute; top:-30px; left:50%; transform:translateX(-50%); width:80px; height:80px; background:radial-gradient(circle,rgba(255,160,0,.18) 0%,transparent 70%); border-radius:50%; }
.metric-value { font-family:'Bebas Neue',sans-serif; font-size:2.6rem; color:#FFA500; line-height:1; }
.metric-label { font-size:0.72rem; color:#666; margin-top:4px; text-transform:uppercase; letter-spacing:.1em; }
.ex-card { background:#111118; border-left:3px solid #FFA500; border-radius:0 12px 12px 0; padding:12px 16px; margin-bottom:8px; }
.ex-title { font-family:'Bebas Neue',sans-serif; font-size:1.1rem; color:#FFA500; letter-spacing:.05em; }
.ex-detail { font-size:0.82rem; color:#888; margin-top:2px; }
.hist-card { background:#0f0f18; border:1px solid #1e1e2e; border-radius:16px; padding:16px 18px; margin-bottom:4px; }
.hist-meta { font-size:0.8rem; color:#555; margin-top:2px; }
.profile-header { background:linear-gradient(135deg,#111118 0%,#1a1020 100%); border:1px solid #2a1a30; border-radius:20px; padding:28px 24px; text-align:center; margin-bottom:20px; }
.profile-avatar { font-size:4rem; line-height:1; margin-bottom:8px; }
.profile-name { font-family:'Bebas Neue',sans-serif; font-size:2rem; color:#fff; letter-spacing:.06em; }
.profile-username { font-size:0.85rem; color:#555; }
.profile-badge { display:inline-block; background:rgba(255,165,0,.12); border:1px solid rgba(255,165,0,.3); color:#FFA500; font-size:0.8rem; font-weight:700; padding:4px 14px; border-radius:99px; margin-top:10px; letter-spacing:.06em; }
.info-row { display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid #1a1a25; font-size:0.9rem; }
.info-row:last-child { border-bottom:none; }
.info-label { color:#555; } .info-value { color:#ddd; font-weight:600; }
.plano-card { background:#0f0f18; border:1px solid #1e1e2e; border-radius:16px; padding:18px 20px; margin-bottom:12px; transition:border-color .2s; }
.plano-card:hover { border-color:rgba(255,165,0,.35); }
.plano-nome { font-family:'Bebas Neue',sans-serif; font-size:1.4rem; color:#FFA500; letter-spacing:.05em; }
.plano-desc { font-size:0.82rem; color:#666; margin-top:2px; }
hr { border-color:#1a1a25 !important; }
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:#0a0a0f; }
::-webkit-scrollbar-thumb { background:#333; border-radius:4px; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# TELA LOGIN
# ═══════════════════════════════════════════════════════
if st.session_state.tela_atual == "login":
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h1 style="font-family:Bebas Neue,sans-serif;font-size:3rem;letter-spacing:.06em">🏋️‍♂️ MEU TREINO</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#555;margin-top:-10px;margin-bottom:24px">Registre. Evolua. Domine.</p>', unsafe_allow_html=True)
    usuario = st.text_input("Usuário", placeholder="edigar.silva").lower().strip()
    senha   = st.text_input("Senha", type="password", max_chars=10)
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

# ═══════════════════════════════════════════════════════
# ONBOARDING
# ═══════════════════════════════════════════════════════
elif st.session_state.tela_atual == "onboarding":
    st.markdown('<h1 style="font-family:Bebas Neue,sans-serif;font-size:2.2rem">Vamos configurar seu perfil</h1>', unsafe_allow_html=True)
    nome     = st.text_input("Nome completo")
    username = st.text_input("Usuário (login)", placeholder="edigar.silva").lower().strip()
    senha    = st.text_input("Senha", type="password", max_chars=10)
    objetivo = st.selectbox("Objetivo Principal", OBJETIVOS)
    dias     = st.selectbox("Dias de treino por semana", [3,4,5,6])
    tempo    = st.selectbox("Tempo por treino", TEMPOS)
    if st.button("Concluir Cadastro →", type="primary", use_container_width=True):
        if nome and username and senha:
            novo = criar_usuario(username, senha, nome, objetivo, dias, tempo)
            if novo:
                st.session_state.usuario_logado = username
                st.session_state.perfil = novo
                st.session_state.tela_atual = "dashboard"; st.rerun()
        else:
            st.warning("Preencha todos os campos.")
    if st.button("← Voltar ao login"):
        st.session_state.tela_atual = "login"; st.rerun()

# ═══════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════
elif st.session_state.tela_atual == "dashboard":
    username = st.session_state.usuario_logado
    perfil   = st.session_state.perfil or {}
    nome_exibido = perfil.get("nome", username).split()[0] if perfil else username

    col_titulo, col_sair = st.columns([8,1])
    with col_titulo:
        hora = datetime.now().hour
        saudacao = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")
        st.markdown(f'<h1 style="font-family:Bebas Neue,sans-serif;font-size:2rem;letter-spacing:.06em;margin-bottom:0">💪 {saudacao.upper()}, {nome_exibido.upper()}!</h1>', unsafe_allow_html=True)
    with col_sair:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sair"):
            for k in ["usuario_logado","perfil","treino_exercicios","plano_exercicios_tmp"]:
                st.session_state[k] = None if k not in ["treino_exercicios","plano_exercicios_tmp"] else []
            st.session_state.tela_atual = "login"; st.rerun()

    abas = ["🏋️ Treino", "📅 Planos", "📋 Histórico", "📊 Stats", "👤 Perfil"]
    aba  = st.radio("", abas, horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    # ══════════════════════════════════════════════════════
    # ABA: TREINO
    # ══════════════════════════════════════════════════════
    if aba == "🏋️ Treino":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Registrar Treino de Hoje</h2>', unsafe_allow_html=True)

        # Carregar a partir de um plano
        planos = buscar_planos(username)
        if planos:
            with st.expander("📥  Carregar a partir de um Plano"):
                nomes_planos = [p["nome"] for p in planos]
                plano_sel = st.selectbox("Selecione o plano", nomes_planos, key="carregar_plano_sel")
                if st.button("Carregar Plano →", use_container_width=True):
                    plano_obj = next((p for p in planos if p["nome"] == plano_sel), None)
                    if plano_obj:
                        st.session_state.treino_exercicios = [
                            {"nome": ex["nome"], "grupo": ex.get("grupo",""), "series": ex.get("series",3), "reps": ex.get("reps",12), "peso": ex.get("peso",0.0)}
                            for ex in plano_obj.get("exercicios",[])
                        ]
                        st.success(f"Plano '{plano_sel}' carregado! Ajuste os pesos abaixo.")
                        st.rerun()

        grupo     = st.selectbox("Grupo Muscular", list(EXERCICIOS.keys()))
        exercicio = st.selectbox("Exercício", EXERCICIOS[grupo])
        c1,c2,c3  = st.columns(3)
        with c1: series = st.number_input("Séries", min_value=1, max_value=10, value=3)
        with c2: reps   = st.number_input("Reps",   min_value=1, max_value=50, value=12)
        with c3: peso   = st.number_input("Peso (kg)", min_value=0.0, max_value=500.0, value=0.0, step=0.5)

        if st.button("➕  Adicionar Exercício", use_container_width=True):
            st.session_state.treino_exercicios.append({"nome":exercicio,"grupo":grupo,"series":int(series),"reps":int(reps),"peso":float(peso)})
            st.success(f"✅ {exercicio} adicionado!")

        if st.session_state.treino_exercicios:
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;margin-top:20px">Exercícios do treino</h3>', unsafe_allow_html=True)
            for i, ex in enumerate(st.session_state.treino_exercicios):
                col_ex, col_del = st.columns([10,1])
                with col_ex:
                    vol = ex["series"]*ex["reps"]*ex["peso"]
                    vol_str = f" &nbsp;—&nbsp; <b>{round(vol):,} kg</b>" if ex["peso"]>0 else ""
                    st.markdown(f'<div class="ex-card"><div class="ex-title">{ex["nome"]}</div><div class="ex-detail">{ex["series"]} séries × {ex["reps"]} reps × {ex["peso"]} kg{vol_str}</div></div>', unsafe_allow_html=True)
                with col_del:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑", key=f"del_{i}"):
                        st.session_state.treino_exercicios.pop(i); st.rerun()

            st.markdown("---")
            duracao = st.number_input("Duração total (minutos)", min_value=10, max_value=300, value=60)
            notas   = st.text_area("Observações (opcional)", placeholder="Como foi o treino?", height=80)
            if st.button("💾  Salvar Treino", type="primary", use_container_width=True):
                resultado = salvar_treino(username, st.session_state.treino_exercicios, duracao, notas)
                if resultado:
                    st.success("🎉 Treino salvo!"); st.balloons()
                    st.session_state.treino_exercicios = []; st.rerun()
        else:
            st.info("Adicione exercícios ou carregue um plano para começar.")

    # ══════════════════════════════════════════════════════
    # ABA: PLANOS
    # ══════════════════════════════════════════════════════
    elif aba == "📅 Planos":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Planos de Treino</h2>', unsafe_allow_html=True)

        planos = buscar_planos(username)

        # Lista planos existentes
        if planos:
            for p in planos:
                exercicios_p = p.get("exercicios", [])
                grupos_p = list({ex.get("grupo","").split()[-1] for ex in exercicios_p if ex.get("grupo")})
                st.markdown(
                    f'<div class="plano-card">'
                    f'<div class="plano-nome">{p["nome"]}</div>'
                    f'<div class="plano-desc">{p.get("descricao","") or ""}</div>'
                    f'<div style="font-size:.8rem;color:#555;margin-top:6px">'
                    f'{len(exercicios_p)} exercício(s) · {", ".join(grupos_p) if grupos_p else "—"}'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                with st.expander(f"Ver exercícios do plano '{p['nome']}'"):
                    for ex in exercicios_p:
                        st.markdown(
                            f'<div class="ex-card"><div class="ex-title">{ex.get("nome","?")}</div>'
                            f'<div class="ex-detail">{ex.get("series","?")}×{ex.get("reps","?")} — {ex.get("peso",0)} kg base</div></div>',
                            unsafe_allow_html=True,
                        )
                    if st.button(f"🗑 Deletar plano '{p['nome']}'", key=f"del_plano_{p['id']}"):
                        if deletar_plano(p["id"]):
                            st.success("Plano deletado."); st.rerun()
        else:
            st.info("Nenhum plano criado ainda. Crie seu primeiro plano abaixo!")

        st.markdown("---")
        st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">➕ Criar Novo Plano</h3>', unsafe_allow_html=True)

        nome_plano = st.text_input("Nome do plano", placeholder="Ex: Treino A — Peito e Tríceps")
        desc_plano = st.text_input("Descrição (opcional)", placeholder="Ex: Push day, foco em hipertrofia")

        # Montar exercícios do plano
        st.markdown("**Exercícios do plano:**")
        grupo_p    = st.selectbox("Grupo", list(EXERCICIOS.keys()), key="plano_grupo")
        ex_p       = st.selectbox("Exercício", EXERCICIOS[grupo_p], key="plano_ex")
        cp1,cp2,cp3 = st.columns(3)
        with cp1: s_p = st.number_input("Séries", min_value=1, max_value=10, value=3, key="plano_series")
        with cp2: r_p = st.number_input("Reps",   min_value=1, max_value=50, value=12, key="plano_reps")
        with cp3: p_p = st.number_input("Peso base (kg)", min_value=0.0, max_value=500.0, value=0.0, step=0.5, key="plano_peso")

        if st.button("➕  Adicionar ao Plano", use_container_width=True):
            st.session_state.plano_exercicios_tmp.append({"nome":ex_p,"grupo":grupo_p,"series":int(s_p),"reps":int(r_p),"peso":float(p_p)})
            st.success(f"✅ {ex_p} adicionado ao plano!")

        if st.session_state.plano_exercicios_tmp:
            for i, ex in enumerate(st.session_state.plano_exercicios_tmp):
                col_pex, col_pdel = st.columns([10,1])
                with col_pex:
                    st.markdown(f'<div class="ex-card"><div class="ex-title">{ex["nome"]}</div><div class="ex-detail">{ex["series"]}×{ex["reps"]} @ {ex["peso"]} kg</div></div>', unsafe_allow_html=True)
                with col_pdel:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑", key=f"pdel_{i}"):
                        st.session_state.plano_exercicios_tmp.pop(i); st.rerun()

            col_sv, col_cl = st.columns(2)
            with col_sv:
                if st.button("💾  Salvar Plano", type="primary", use_container_width=True):
                    if not nome_plano:
                        st.warning("Dê um nome ao plano.")
                    else:
                        resultado = salvar_plano(username, nome_plano, desc_plano, st.session_state.plano_exercicios_tmp)
                        if resultado:
                            st.success(f"Plano '{nome_plano}' salvo!")
                            st.session_state.plano_exercicios_tmp = []; st.rerun()
            with col_cl:
                if st.button("Limpar", use_container_width=True):
                    st.session_state.plano_exercicios_tmp = []; st.rerun()

    # ══════════════════════════════════════════════════════
    # ABA: HISTÓRICO
    # ══════════════════════════════════════════════════════
    elif aba == "📋 Histórico":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Histórico de Treinos</h2>', unsafe_allow_html=True)
        treinos = buscar_treinos(username, limit=30)
        if not treinos:
            st.info("Nenhum treino registrado ainda. Bora começar! 💪")
        else:
            for t in treinos:
                exercicios   = t.get("exercicios",[])
                volume_total = sum(ex.get("series",0)*ex.get("reps",0)*ex.get("peso",0) for ex in exercicios)
                grupos       = list({ex.get("grupo","").split()[-1] for ex in exercicios if ex.get("grupo")})
                try:
                    data_fmt   = datetime.strptime(t["data"],"%Y-%m-%d").strftime("%d/%m/%Y")
                    dia_semana = datetime.strptime(t["data"],"%Y-%m-%d").strftime("%A")
                    dias_pt    = {"Monday":"Seg","Tuesday":"Ter","Wednesday":"Qua","Thursday":"Qui","Friday":"Sex","Saturday":"Sáb","Sunday":"Dom"}
                    dia_semana = dias_pt.get(dia_semana, dia_semana)
                except:
                    data_fmt = t.get("data","—"); dia_semana = ""

                with st.expander(f"📅  {dia_semana} {data_fmt} — {len(exercicios)} exercício(s) | {t.get('duracao_min','?')} min"):
                    st.markdown(f'<div class="hist-card"><div class="hist-meta">Grupos: {", ".join(grupos) if grupos else "—"} &nbsp;·&nbsp; Volume: <b style="color:#FFA500">{round(volume_total):,} kg</b></div></div>', unsafe_allow_html=True)
                    for ex in exercicios:
                        v = ex.get("series",0)*ex.get("reps",0)*ex.get("peso",0)
                        vol_str = f" &nbsp;—&nbsp; <b>{round(v):,} kg</b>" if ex.get("peso",0)>0 else ""
                        st.markdown(f'<div class="ex-card"><div class="ex-title">{ex.get("nome","?")}</div><div class="ex-detail">{ex.get("series","?")}×{ex.get("reps","?")} @ {ex.get("peso","?")} kg{vol_str}</div></div>', unsafe_allow_html=True)
                    if t.get("notas"):
                        st.caption(f"📝 {t['notas']}")
                    if st.button("🗑 Deletar este treino", key=f"del_treino_{t['id']}"):
                        if deletar_treino(t["id"]):
                            st.success("Treino deletado."); st.rerun()

    # ══════════════════════════════════════════════════════
    # ABA: STATS
    # ══════════════════════════════════════════════════════
    elif aba == "📊 Stats":
        import pandas as pd
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Suas Estatísticas</h2>', unsafe_allow_html=True)
        treinos = buscar_treinos(username, limit=200)

        if not treinos:
            st.info("Registre treinos para ver suas estatísticas aqui.")
        else:
            hoje = date.today()
            datas = []
            for t in treinos:
                try: datas.append(datetime.strptime(t["data"],"%Y-%m-%d").date())
                except: pass
            datas_set = set(datas)

            inicio_semana  = hoje - timedelta(days=hoje.weekday())
            treinos_semana = sum(1 for d in datas if d >= inicio_semana)
            volume_total   = sum(ex.get("series",0)*ex.get("reps",0)*ex.get("peso",0) for t in treinos for ex in t.get("exercicios",[]))

            streak = 0
            check  = hoje
            while check in datas_set: streak += 1; check -= timedelta(days=1)
            if streak == 0 and (hoje - timedelta(days=1)) in datas_set:
                check = hoje - timedelta(days=1)
                while check in datas_set: streak += 1; check -= timedelta(days=1)

            contagem = {}
            for t in treinos:
                for ex in t.get("exercicios",[]):
                    n = ex.get("nome","?"); contagem[n] = contagem.get(n,0)+1
            top_ex = sorted(contagem.items(), key=lambda x:x[1], reverse=True)[:5]

            # Métricas
            c1,c2,c3,c4 = st.columns(4)
            mets = [
                (treinos_semana, "Esta semana"),
                (f"{round(volume_total/1000,1)}t" if volume_total>=1000 else f"{round(volume_total):,} kg", "Volume total"),
                (f"{'🔥' if streak>=3 else '⚡' if streak>=1 else '💤'} {streak}", "Streak dias"),
                (len(treinos), "Total treinos"),
            ]
            for col,(val,lbl) in zip([c1,c2,c3,c4], mets):
                with col:
                    st.markdown(f'<div class="metric-card"><div class="metric-value">{val}</div><div class="metric-label">{lbl}</div></div>', unsafe_allow_html=True)

            # Treinos por semana
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;margin-top:24px">Treinos por Semana</h3>', unsafe_allow_html=True)
            semanas = []
            for i in range(7,-1,-1):
                ini = hoje - timedelta(days=hoje.weekday()) - timedelta(weeks=i)
                fim = ini + timedelta(days=6)
                semanas.append({"semana": ini.strftime("%d/%m"), "treinos": sum(1 for d in datas if ini<=d<=fim)})
            st.bar_chart(pd.DataFrame(semanas).set_index("semana"), color="#FFA500")

            # Top exercícios
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;">Top Exercícios</h3>', unsafe_allow_html=True)
            medalhas = ["🥇","🥈","🥉","4️⃣","5️⃣"]
            max_qtd  = max(c for _,c in top_ex) if top_ex else 1
            for rank,(nome,qtd) in enumerate(top_ex,1):
                col_r,col_b = st.columns([3,7])
                with col_r: st.markdown(f"**{medalhas[rank-1]} {nome}**"); st.caption(f"{qtd} vez{'es' if qtd>1 else ''}")
                with col_b: st.progress(qtd/max_qtd)

            # ── EVOLUÇÃO DE CARGA ──────────────────────────────
            st.markdown("---")
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;">📈 Evolução de Carga</h3>', unsafe_allow_html=True)
            st.caption("Veja como o peso máximo de um exercício evoluiu ao longo do tempo.")

            ex_escolhido = st.selectbox("Selecione o exercício", TODOS_EXERCICIOS, key="evolucao_ex")

            # Coleta dados: data → peso máximo naquele treino
            registros = {}
            for t in treinos:
                try: dt = datetime.strptime(t["data"],"%Y-%m-%d").date()
                except: continue
                for ex in t.get("exercicios",[]):
                    if ex.get("nome") == ex_escolhido and ex.get("peso",0) > 0:
                        registros[dt] = max(registros.get(dt, 0), ex.get("peso",0))

            if not registros:
                st.info(f"Nenhum registro de '{ex_escolhido}' com peso > 0 encontrado.")
            else:
                df_ev = pd.DataFrame(
                    sorted(registros.items()),
                    columns=["data","peso_max"]
                ).set_index("data")

                # Destaque: PR (peso máximo histórico)
                pr = df_ev["peso_max"].max()
                pr_data = df_ev["peso_max"].idxmax()

                col_pr1, col_pr2 = st.columns(2)
                with col_pr1:
                    st.markdown(f'<div class="metric-card"><div class="metric-value">🏆 {pr} kg</div><div class="metric-label">Recorde pessoal (PR)</div></div>', unsafe_allow_html=True)
                with col_pr2:
                    pr_fmt = pr_data.strftime("%d/%m/%Y") if hasattr(pr_data,"strftime") else str(pr_data)
                    st.markdown(f'<div class="metric-card"><div class="metric-value">{pr_fmt}</div><div class="metric-label">Data do PR</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.line_chart(df_ev, color="#FFA500")

                # Tabela resumida
                with st.expander("Ver tabela de registros"):
                    df_show = df_ev.copy()
                    df_show.index = [d.strftime("%d/%m/%Y") if hasattr(d,"strftime") else str(d) for d in df_show.index]
                    df_show.columns = ["Peso Máximo (kg)"]
                    st.dataframe(df_show, use_container_width=True)

    # ══════════════════════════════════════════════════════
    # ABA: PERFIL
    # ══════════════════════════════════════════════════════
    elif aba == "👤 Perfil":
        perfil = st.session_state.perfil or {}
        objetivo_atual = perfil.get("objetivo","—")
        emoji_obj = {"Hipertrofia":"💪","Emagrecimento":"🔥","Condicionamento":"⚡","Forca":"🏋️"}.get(objetivo_atual,"🎯")

        st.markdown(
            f'<div class="profile-header">'
            f'<div class="profile-avatar">🧑‍💪</div>'
            f'<div class="profile-name">{perfil.get("nome",username)}</div>'
            f'<div class="profile-username">@{username}</div>'
            f'<div class="profile-badge">{emoji_obj} {objetivo_atual}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if not st.session_state.editando_perfil:
            st.markdown(
                f'<div style="background:#0f0f18;border:1px solid #1e1e2e;border-radius:16px;padding:8px 20px;margin-bottom:20px">'
                f'<div class="info-row"><span class="info-label">Dias por semana</span><span class="info-value">{perfil.get("dias_por_semana","—")} dias</span></div>'
                f'<div class="info-row"><span class="info-label">Tempo por treino</span><span class="info-value">{perfil.get("tempo_disponivel","—")}</span></div>'
                f'<div class="info-row"><span class="info-label">Objetivo</span><span class="info-value">{perfil.get("objetivo","—")}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("✏️  Editar Perfil", use_container_width=True):
                st.session_state.editando_perfil = True; st.rerun()
        else:
            st.markdown('<h3 style="font-family:Bebas Neue,sans-serif;">Editar Informações</h3>', unsafe_allow_html=True)
            novo_nome     = st.text_input("Nome completo", value=perfil.get("nome",""))
            novo_objetivo = st.selectbox("Objetivo", OBJETIVOS, index=OBJETIVOS.index(perfil.get("objetivo",OBJETIVOS[0])) if perfil.get("objetivo") in OBJETIVOS else 0)
            novo_dias     = st.selectbox("Dias por semana", [3,4,5,6], index=[3,4,5,6].index(perfil.get("dias_por_semana",3)) if perfil.get("dias_por_semana") in [3,4,5,6] else 0)
            novo_tempo    = st.selectbox("Tempo por treino", TEMPOS, index=TEMPOS.index(perfil.get("tempo_disponivel",TEMPOS[0])) if perfil.get("tempo_disponivel") in TEMPOS else 0)
            st.markdown("---")
            st.markdown("**Alterar senha** *(deixe em branco para manter a atual)*")
            nova_senha = st.text_input("Nova senha", type="password", max_chars=10)
            confirmar  = st.text_input("Confirmar nova senha", type="password", max_chars=10)
            col_sv, col_cl = st.columns(2)
            with col_sv:
                if st.button("💾  Salvar", type="primary", use_container_width=True):
                    if nova_senha and nova_senha != confirmar:
                        st.error("As senhas não coincidem.")
                    elif not novo_nome:
                        st.warning("Nome não pode estar vazio.")
                    else:
                        atualizado = atualizar_perfil(username, novo_nome, novo_objetivo, novo_dias, novo_tempo, senha_nova=nova_senha if nova_senha else None)
                        if atualizado:
                            st.session_state.perfil = atualizado
                            st.session_state.editando_perfil = False
                            st.success("✅ Perfil atualizado!"); st.rerun()
            with col_cl:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.editando_perfil = False; st.rerun()

else:
    st.info("Em desenvolvimento...")