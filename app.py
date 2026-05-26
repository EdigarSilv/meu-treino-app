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
EXERCICIOS = {
    "🦵 Pernas": ["Agachamento Livre","Leg Press","Cadeira Extensora","Mesa Flexora","Stiff","Avanço","Afundo","Panturrilha na Máquina","Hack Squat"],
    "🫁 Peito": ["Supino Reto","Supino Inclinado","Supino Declinado","Crucifixo","Crossover","Peck Deck","Flexão","Pullover"],
    "🔙 Costas": ["Puxada Frontal","Remada Curvada","Remada Unilateral","Levantamento Terra","Serrote","Puxada Fechada","Remada na Máquina","Pull-up"],
    "💪 Bíceps": ["Rosca Direta","Rosca Alternada","Rosca Martelo","Rosca Concentrada","Rosca 21","Rosca na Polia"],
    "💪 Tríceps": ["Tríceps Corda","Tríceps Testa","Tríceps Francês","Mergulho","Tríceps na Polia Alta","Tríceps Coice"],
    "🏔️ Ombros": ["Desenvolvimento","Elevação Lateral","Elevação Frontal","Remada Alta","Encolhimento","Crucifixo Inverso"],
    "🎯 Abdômen": ["Abdominal Crunch","Prancha","Abdominal Oblíquo","Elevação de Pernas","Abdominal na Máquina","Russian Twist"],
}

TODOS_EXERCICIOS = sorted({e for lst in EXERCICIOS.values() for e in lst})
OBJETIVOS = ["Hipertrofia", "Emagrecimento", "Condicionamento", "Força"]
TEMPOS = ["45 min", "1h", "1h15", "1h30", "2h"]

# ====================== SESSION STATE ======================
defaults = {
    "tela_atual": "login",
    "usuario_logado": None,
    "perfil": None,
    "treino_exercicios": [],
    "plano_exercicios_tmp": [],
    "editando_perfil": False,
    "aba_atual": "🏋️ Treino",  # Estado para controlar a aba ativa voluntariamente
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

def deletar_treino(treino_id):
    try:
        supabase.table("treinos").delete().eq("id", treino_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar treino: {e}")
        return False

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
    except Exception as e:
        st.error(f"Erro ao buscar treinos: {e}")
        return []

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
    ref = date.today()
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

# ====================== SAUDAÇÃO ======================
def get_saudacao(hora):
    if hora < 12:
        return "BOM DIA"
    elif hora < 18:
        return "BOA TARDE"
    else:
        return "BOA NOITE"

# ====================== TRACKER SEMANAL ======================
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

# ====================== CSS ======================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Nunito:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Nunito', sans-serif; background-color: #0a0a0f; }
h1, h2, h3 { font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 0.04em; }
.ex-card {
    background:#111118; border-left:4px solid #FFA500;
    border-radius:12px; padding:14px 16px; margin-bottom:10px;
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
            st.session_state.tela_atual = "dashboard"
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    if st.button("Criar Nova Conta", use_container_width=True):
        st.session_state.tela_atual = "onboarding"
        st.rerun()

elif st.session_state.tela_atual == "onboarding":
    st.markdown('<h1 style="font-family:Bebas Neue,sans-serif;font-size:2.2rem">Vamos configure seu perfil</h1>', unsafe_allow_html=True)
    nome     = st.text_input("Nome completo")
    username = st.text_input("Usuário (login)", placeholder="edigar.silva").lower().strip()
    senha    = st.text_input("Senha", type="password", max_chars=10)
    objetivo = st.selectbox("Objetivo Principal", OBJETIVOS)
    dias     = st.selectbox("Dias de treino por semana", [3,4,5,6])
    tempo    = st.selectbox("Tempo por treino", TEMPOS)
    if st.button("Concluir Cadastro →", type="primary", use_container_width=True):
        if nome and username and senha:
            novo = criar_usuario(username, senha, nome, objective, dias, tempo)
            if novo:
                st.session_state.usuario_logado = username
                st.session_state.perfil = novo
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

    # --- PROCESSAMENTO DO HORÁRIO ---
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
            st.rerun()

    # --- CONTROLE DE NAVEGAÇÃO DINÂMICA DAS ABAS ---
    abas = ["🏋️ Treino", "📅 Planos", "📋 Histórico", "📊 Stats", "👤 Perfil"]
    
    # Encontra o índice da aba salva no state
    try:
        idx_inicial = abas.index(st.session_state.aba_atual)
    except ValueError:
        idx_inicial = 0

    aba = st.radio("", abas, horizontal=True, label_visibility="collapsed", index=idx_inicial)
    st.session_state.aba_atual = aba  # Atualiza o state conforme clique manual
    st.markdown("---")

    # ── ABA TREINO ──────────────────────────────────────────────────────────────
    if aba == "🏋️ Treino":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Registrar Treino de Hoje</h2>', unsafe_allow_html=True)
        treinos_semana = buscar_treinos(username, limit=30)
        render_weekly_tracker(treinos_semana)

        grupo     = st.selectbox("Grupo Muscular", list(EXERCICIOS.keys()))
        exercicio = st.selectbox("Exercício", EXERCICIOS[grupo])
        ultimo_peso = get_ultimo_peso(username, exercicio)
        sugestao    = round(ultimo_peso + 2.5, 1) if ultimo_peso > 0 else 0.0

        c1, c2, c3 = st.columns(3)
        with c1:
            series = st.number_input("Séries", min_value=1, max_value=10, value=3)
        with c2:
            reps = st.number_input("Reps", min_value=1, max_value=50, value=12)
        with c3:
            peso = st.number_input("Peso (kg)", min_value=0.0, max_value=500.0, value=sugestao, step=0.5)

        if ultimo_peso > 0 and st.button("🔄 Usar último peso"):
            peso = ultimo_peso
            st.rerun()

        if st.button("➕ Adicionar Exercício", use_container_width=True, type="primary"):
            st.session_state.treino_exercicios.append({
                "nome": exercicio, "grupo": grupo,
                "series": int(series), "reps": int(reps), "peso": float(peso)
            })
            st.success(f"{exercicio} adicionado!")
            st.rerun()

        if st.session_state.treino_exercicios:
            st.markdown("---")
            st.subheader("Exercícios adicionados")
            for i, ex in enumerate(st.session_state.treino_exercicios):
                col1, col2 = st.columns([9, 1])
                with col1:
                    st.markdown(
                        '<div class="ex-card"><strong>' + ex["nome"] + '</strong><br>'
                        + str(ex["series"]) + '×' + str(ex["reps"]) + ' @ ' + str(ex["peso"]) + 'kg</div>',
                        unsafe_allow_html=True
                    )
                with col2:
                    if st.button("🗑", key=f"del_{i}_{ex['nome']}"):
                        st.session_state.treino_exercicios.pop(i)
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            
            # Form seguro para submissão dos dados no banco
            with st.form("form_finalizar_treino"):
                st.markdown("### Finalizar Treino")
                duracao = st.number_input("Duração do treino (min)", value=60, min_value=1)
                notas   = st.text_area("Observações (opcional)", placeholder="Como foi o treino hoje?", height=80)
                
                botao_salvar = st.form_submit_button("💾 Salvar Treino", type="primary", use_container_width=True)
                
                if botao_salvar:
                    resposta = salvar_treino(username, st.session_state.treino_exercicios, duracao, notas)
                    if resposta:
                        st.success("Treino salvo com sucesso! 💪")
                        st.session_state.treino_exercicios = []
                        st.rerun()
                    else:
                        st.error("Erro ao salvar o treino. Verifique os campos ou o console do Supabase.")

    # ── ABA PLANOS ──────────────────────────────────────────────────────────────
    elif aba == "📅 Planos":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Meus Planos de Treino</h2>', unsafe_allow_html=True)

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
                        # LOGICA CORRIGIDA: Salva e força redirecionamento automático de aba
                        if st.button("▶ Usar este plano hoje", key="usar_" + str(plano["id"]), use_container_width=True, type="primary"):
                            st.session_state.treino_exercicios = [dict(e) for e in exs]
                            st.session_state.aba_atual = "🏋️ Treino"
                            st.rerun()
                    with col_del:
                        if st.button("🗑 Excluir", key="dplano_" + str(plano["id"]), use_container_width=True):
                            deletar_plano(plano["id"])
                            st.rerun()
                    st.markdown("---")

    # ── ABA HISTÓRICO ────────────────────────────────────────────────────────────
    elif aba == "📋 Histórico":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Histórico de Treinos</h2>', unsafe_allow_html=True)
        treinos = buscar_treinos(username, limit=100)
        if not treinos:
            st.info("Nenhum treino registrado ainda.")
        else:
            meses_disponiveis = sorted(
                {t["data"][:7] for t in treinos if t.get("data")}, reverse=True
            )
            labels_meses = [datetime.strptime(m, "%Y-%m").strftime("%B %Y").capitalize() for m in meses_disponiveis]
            mes_idx = st.selectbox("Filtrar por mês", range(len(meses_disponiveis)), format_func=lambda i: labels_meses[i])
            mes_sel = meses_disponiveis[mes_idx]
            treinos_filtrados = [t for t in treinos if t.get("data","").startswith(mes_sel)]

            st.markdown(
                '<div style="color:#888;font-size:0.85rem;margin-bottom:12px;">'
                + str(len(treinos_filtrados)) + ' treino(s) em ' + labels_meses[mes_idx] + '</div>',
                unsafe_allow_html=True
            )

            for t in treinos_filtrados:
                data_fmt = datetime.strptime(t["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
                exs      = t.get("exercicios", [])
                duracao  = t.get("duracao_min", 0) or 0
                notas    = t.get("notas", "") or ""

                with st.expander(data_fmt + "  •  " + str(len(exs)) + " exercícios  •  " + str(duracao) + " min"):
                    for ex in exs:
                        vol = ex.get("series",0) * ex.get("reps",0) * float(ex.get("peso",0))
                        st.markdown(
                            '<div style="padding:8px 12px;margin-bottom:6px;background:#1a1a28;border-radius:8px;">'
                            '<strong>' + ex.get("nome","") + '</strong>'
                            '<span style="color:#888;font-size:0.85rem;"> — '
                            + str(ex.get("series","")) + '×' + str(ex.get("reps",""))
                            + ' @ ' + str(ex.get("peso","")) + 'kg'
                            + ' | vol: ' + str(round(vol,0)) + 'kg</span></div>',
                            unsafe_allow_html=True
                        )
                    if notas:
                        st.markdown(
                            '<div style="margin-top:8px;padding:8px 12px;background:#0f1a0f;border-radius:8px;'
                            'color:#888;font-size:0.85rem;">📝 ' + notas + '</div>',
                            unsafe_allow_html=True
                        )
                    if st.button("🗑 Deletar este treino", key="hdel_" + str(t.get("id",""))):
                        deletar_treino(t["id"])
                        st.rerun()

    # ── ABA STATS ───────────────────────────────────────────────────────────────
    elif aba == "📊 Stats":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Estatísticas</h2>', unsafe_allow_html=True)

        stats = get_stats_gerais(username)
        if not stats:
            st.info("Registre treinos para ver suas estatísticas.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(
                    '<div class="stat-card">'
                    '<div style="font-size:1.8rem;font-weight:700;color:#FFA500;">' + str(stats["total_treinos"]) + '</div>'
                    '<div style="color:#888;font-size:0.8rem;margin-top:4px;">TREINOS TOTAIS</div>'
                    '</div>', unsafe_allow_html=True
                )
            with c2:
                st.markdown(
                    '<div class="stat-card">'
                    '<div style="font-size:1.8rem;font-weight:700;color:#22c55e;">' + str(stats["total_horas"]) + 'h</div>'
                    '<div style="color:#888;font-size:0.8rem;margin-top:4px;">HORAS TREINADAS</div>'
                    '</div>', unsafe_allow_html=True
                )
            with c3:
                st.markdown(
                    '<div class="stat-card">'
                    '<div style="font-size:1.8rem;font-weight:700;color:#a855f7;">' + str(stats["total_series"]) + '</div>'
                    '<div style="color:#888;font-size:0.8rem;margin-top:4px;">SÉRIES TOTAIS</div>'
                    '</div>', unsafe_allow_html=True
                )
            with c4:
                st.markdown(
                    '<div class="stat-card">'
                    '<div style="font-size:1.8rem;font-weight:700;color:#f59e0b;">' + str(stats["streak"]) + '🔥</div>'
                    '<div style="color:#888;font-size:0.8rem;margin-top:4px;">DIAS SEGUIDOS</div>'
                    '</div>', unsafe_allow_html=True
                )

            st.markdown("<br>", unsafe_allow_html=True)

            if stats.get("grupos_count"):
                st.markdown("#### Grupos Musculares Mais Treinados")
                df_grupos = pd.DataFrame(
                    list(stats["grupos_count"].items()), columns=["Grupo", "Exercícios"]
                ).sort_values("Exercícios", ascending=False)
                chart_grupos = alt.Chart(df_grupos).mark_bar(color="#FFA500", opacity=0.85).encode(
                    x=alt.X("Exercícios:Q", title="Qtd. de exercícios"),
                    y=alt.Y("Grupo:N", sort="-x", title=""),
                    tooltip=["Grupo", "Exercícios"]
                ).properties(height=280).interactive()
                st.altair_chart(chart_grupos, use_container_width=True)

            if stats.get("datas"):
                st.markdown("#### Treinos por Semana")
                df_datas = pd.DataFrame({"data": list(stats["datas"])})
                df_datas["data"] = pd.to_datetime(df_datas["data"])
                df_datas["semana"] = df_datas["data"].dt.to_period("W").apply(lambda r: r.start_time)
                df_sem = df_datas.groupby("semana").size().reset_index(name="treinos").tail(8)
                chart_sem = alt.Chart(df_sem).mark_bar(color="#22c55e", opacity=0.85).encode(
                    x=alt.X("semana:T", title="Semana", axis=alt.Axis(format="%d/%m")),
                    y=alt.Y("treinos:Q", title="Treinos", axis=alt.Axis(tickMinStep=1)),
                    tooltip=[alt.Tooltip("semana:T", format="%d/%m/%Y"), "treinos"]
                ).properties(height=220).interactive()
                st.altair_chart(chart_sem, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📈 Evolução de Carga por Exercício")
        ex_sel = st.selectbox("Selecione o exercício", TODOS_EXERCICIOS)
        df = get_evolucao_carga(username, ex_sel)
        if df.empty:
            st.info("Sem registros de carga para este exercício.")
        else:
            df_chart = df.copy()
            df_chart["data"] = pd.to_datetime(df_chart["data"])
            df_chart = df_chart.sort_values("data")

            chart_peso = alt.Chart(df_chart).mark_line(point=True, strokeWidth=3).encode(
                x=alt.X("data:T", title="Data", axis=alt.Axis(format="%d/%m", labelAngle=-45)),
                y=alt.Y("peso:Q", title="Peso (kg)", scale=alt.Scale(zero=False)),
                color=alt.value("#FFA500"),
                tooltip=[
                    alt.Tooltip("data:T", title="Data", format="%d/%m/%Y"),
                    alt.Tooltip("peso:Q", title="Peso (kg)", format=".1f"),
                    alt.Tooltip("series:Q", title="Séries"),
                    alt.Tooltip("reps:Q", title="Reps"),
                ]
            ).properties(title="Evolução de Carga — " + ex_sel, height=300).interactive()
            st.altair_chart(chart_peso, use_container_width=True)
