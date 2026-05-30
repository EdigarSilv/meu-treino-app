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
    "🫁 Peito": ["Supino Reto","Supino Inclinado","Supino Declinado","Crucifixo","Crossover","Peck Deck","Flexão","Pullover","Crucifixo Máquina (Peck Deck)","Desenvolvimento com Halteres","Elevação Lateral (Halteres ou Polia)"],
    "🔙 Costas": ["Puxada Frontal","Remada Curvada","Remada Unilateral","Levantamento Terra","Serrote","Puxada Fechada","Remada na Máquina","Pull-up"],
    "💪 Bíceps": ["Rosca Direta","Rosca Alternada","Rosca Martelo","Rosca Concentrada","Rosca 21","Rosca na Polia","Tríceps Pulley (Barra ou Corda)"],
    "💪 Tríceps": ["Tríceps Corda","Tríceps Testa","Tríceps Francês","Mergulho","Tríceps na Polia Alta","Tríceps Coice","Tríceps Pulley (Barra ou Corda)"],
    "🏔️ Ombros": ["Desenvolvimento","Elevação Lateral","Elevação Frontal","Remada Alta","Encolhimento","Crucifixo Inverso"],
    "🎯 Abdômen": ["Abdominal Crunch","Prancha","Abdominal Oblíquo","Elevação de Pernas","Abdominal na Máquina","Russian Twist"],
}

TODOS_EXERCICIOS = sorted({e for lst in EXERCICIOS.values() for e in lst})
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
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Recupera o usuário direto dos parâmetros da URL caso o State tenha limpado no mobile
query_params = st.query_params
if "user" in query_params and st.session_state.usuario_logado is None:
    user_url = query_params["user"]
    try:
        r = supabase.table("perfis").select("*").eq("username", user_url).execute()
        if r.data:
            user = r.data[0]
            st.session_state.usuario_logado = user_url
            st.session_state.perfil = user
            st.session_state.tela_atual = "dashboard"
            if user.get("treino_em_andamento"):
                try:
                    st.session_state.treino_exercicios = json.loads(user.get("treino_em_andamento"))
                except:
                    st.session_state.treino_exercicios = []
    except:
        pass

# ====================== FUNÇÕES DB ======================
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
            "data": date.today().isoformat(),
            "exercicios": json.dumps(exercicios, ensure_ascii=False),
            "duracao_min": duracao_min,
            "notas": notas,  # <-- Corrigido aqui de 'notes' para 'notas'
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
            "data_registro": date.today().isoformat(),
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

def get_saudacao(hora):
    if hora < 12:
        return "BOM DIA"
    elif hora < 18:
        return "BOA TARDE"
    else:
        return "BOA NOITE"

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
            
            # Adiciona o usuário na URL para persistir no celular
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
            novo = criar_usuario(username, senha, nome, objective=objetivo, dias=dias, tempo=tempo)
            if novo:
                st.session_state.usuario_logado = username
                st.session_state.perfil = novo
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

        grupo     = st.selectbox("Grupo Muscular", list(EXERCICIOS.keys()))
        exercicio = st.selectbox("Exercício", EXERCICIOS[grupo])
        ultimo_peso = get_ultimo_peso(username, exercicio)
        sugestao    = round(ultimo_peso + 2.5, 1) if ultimo_peso > 0 else 0.0

        if f"input_peso_{exercicio.replace(' ', '_')}" not in st.session_state:
            st.session_state[f"input_peso_{exercicio.replace(' ', '_')}"] = sugestao

        c1, c2, c3 = st.columns(3)
        with c1:
            series = st.number_input("Séries", min_value=1, max_value=10, value=3)
        with c2:
            reps = st.number_input("Reps", min_value=1, max_value=50, value=12)
        with c3:
            peso = st.number_input("Peso (kg)", min_value=0.0, max_value=500.0, step=0.5, key=f"input_peso_{exercicio.replace(' ', '_')}")

        if ultimo_peso > 0 and st.button("🔄 Usar último peso"):
            st.session_state[f"input_peso_{exercicio.replace(' ', '_')}"] = ultimo_peso
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
            
            # Criamos uma cópia para iterar com segurança
            lista_atualizada = list(st.session_state.treino_exercicios)
            houve_mudanca = False

            for i, ex in enumerate(lista_atualizada):
                col_check, col_texto, col_peso_edit, col_del = st.columns([0.8, 5.2, 3, 1])
                
                # Chaves limpas para os componentes
                chk_key = f"render_chk_{i}_{ex['nome'].replace(' ', '_')}"
                inp_key = f"render_peso_{i}_{ex['nome'].replace(' ', '_')}"

                with col_check:
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    # Checkbox simples sem callback agressivo
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
                    # Input de peso direto
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

            # Se o usuário alterou algum peso ou marcou o check, salva silenciosamente no banco
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
                        
                    # Aqui já está mapeado para a coluna correta "notas"
                    resposta = salvar_treino(username, dados_para_salvar, duracao, notas)
                    if resposta:
                        st.success("Treino salvo! 💪")
                        # Limpa as chaves antigas do estado
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
                                if "chk_estabilizado_" in k or "peso_estabilizado_" in k:
                                    st.session_state.pop(k, None)
                                    
                            for e in exs:
                                item = dict(e)
                                item["feito"] = False
                                st.session_state.treino_exercicios.append(item)
                            
                            persistir_rascunho_treino(username, st.session_state.treino_exercicios)
                            st.session_state.aba_atual = "🏋️ Treino"
                            st.rerun()
                    with col_del:
                        if st.button("🗑 Excluir", key="dplano_" + str(plano["id"]), use_container_width=True):
                            deletar_plano(plano["id"])
                            st.rerun()
                    st.markdown("---")

    # ── ABA HISTÓRICO ───────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "📋 Histórico":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Histórico de Treinos</h2>', unsafe_allow_html=True)
        historico = buscar_treinos(username, limit=50)
        if not historico:
            st.info("Nenhum treino registrado ainda.")
        else:
            for t in historico:
                try:
                    dt = datetime.strptime(t["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
                except:
                    dt = t["data"]
                
                with st.container():
                    st.markdown(
                        f'<div class="hist-card">'
                        f'<span style="color:#FFA500; font-weight:bold; font-size:1.1rem;">📅 {dt}</span> '
                        f'• ⏱️ {t.get("duracao_min", 0)} min<br>', 
                        unsafe_allow_html=True
                    )
                    if t.get("notes"):
                        st.markdown(f'<p style="color:#bbb; font-style:italic; font-size:0.9rem; margin: 4px 0;">Obs: {t.get("notes")}</p>', unsafe_allow_html=True)
                    
                    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
                    for ex in t.get("exercicios", []):
                        st.markdown(
                            f'💪 **{ex.get("nome")}** &rarr; {ex.get("series")}×{ex.get("reps")} '
                            f'({ex.get("peso")} kg)'
                        )
                    
                    ch1, ch2 = st.columns([7,1])
                    with ch2:
                        if st.button("🗑", key=f"del_t_{t['id']}"):
                            if deletar_treino(t["id"]):
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # ── ABA STATS ───────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "📊 Stats":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Estatísticas e Cargas</h2>', unsafe_allow_html=True)
        
        stats = get_stats_gerais(username)
        if not stats:
            st.info("Treine primeiro para ver estatísticas.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f'<div class="stat-card"><span style="font-size:0.8rem;color:#888;">TREINOS</span><br><b style="font-size:1.6rem;color:#FFA500;">{stats["total_treinos"]}</b></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="stat-card"><span style="font-size:0.8rem;color:#888;">HORAS</span><br><b style="font-size:1.6rem;color:#38bdf8;">{stats["total_horas"]}h</b></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="stat-card"><span style="font-size:0.8rem;color:#888;">SÉRIES</span><br><b style="font-size:1.6rem;color:#a855f7;">{stats["total_series"]}</b></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="stat-card"><span style="font-size:0.8rem;color:#888;">STREAK</span><br><b style="font-size:1.6rem;color:#22c55e;">{stats["streak"]}🔥</b></div>', unsafe_allow_html=True)
            
            st.markdown("### 📈 Evolução de Carga")
            ex_escolhido = st.selectbox("Selecione o Exercício para ver o gráfico", TODOS_EXERCICIOS)
            df_ev = get_evolucao_carga(username, ex_escolhido)
            
            if df_ev.empty:
                st.info("Nenhum dado de carga para este exercício.")
            else:
                df_ev["data"] = df_ev["data"].astype(str)
                chart = alt.Chart(df_ev).mark_line(point=True, color="#FFA500").encode(
                    x=alt.X("data:O", title="Data"),
                    y=alt.Y("peso:Q", title="Peso (kg)"),
                    tooltip=["data", "peso", "series", "reps"]
                ).properties(height=300).interactive()
                st.altair_chart(chart, use_container_width=True)

    # ── ABA MEDIDAS ─────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "⚖️ Medidas":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Histórico Corporal</h2>', unsafe_allow_html=True)
        
        with st.expander("➕ Registrar Novas Medidas", expanded=False):
            with st.form("form_medidas"):
                cm1, cm2, cm3 = st.columns(3)
                with cm1:
                    peso_m = st.number_input("Peso (kg)*", 30.0, 250.0, 75.0, 0.1)
                    bf_m = st.number_input("BF (%)", 0.0, 60.0, 0.0, 0.1)
                    peito_m = st.number_input("Peito (cm)", 0.0, 200.0, 0.0, 0.1)
                with cm2:
                    cintura_m = st.number_input("Cintura (cm)", 0.0, 200.0, 0.0, 0.1)
                    braco_d = st.number_input("Braço Dir (cm)", 0.0, 70.0, 0.0, 0.1)
                    braco_e = st.number_input("Braço Esq (cm)", 0.0, 70.0, 0.0, 0.1)
                with cm3:
                    ombro_m = st.number_input("Ombro (cm)", 0.0, 200.0, 0.0, 0.1)
                    quadril_m = st.number_input("Quadril (cm)", 0.0, 200.0, 0.0, 0.1)
                
                st.markdown("**Membros Inferiores**")
                cminf1, cminf2 = st.columns(2)
                with cminf1:
                    coxa_d = st.number_input("Coxa Dir (cm)", 0.0, 120.0, 0.0, 0.1)
                    pant_d = st.number_input("Panturrilha Dir (cm)", 0.0, 70.0, 0.0, 0.1)
                with cminf2:
                    coxa_e = st.number_input("Coxa Esq (cm)", 0.0, 120.0, 0.0, 0.1)
                    pant_e = st.number_input("Panturrilha Esq (cm)", 0.0, 70.0, 0.0, 0.1)
                    
                if st.form_submit_button("💾 Salvar Medidas", type="primary", use_container_width=True):
                    salvar_medidas(username, peso_m, cintura_m, braco_d, braco_e, bf_m, coxa_d, coxa_e, pant_d, pant_e, quadril_m, peito_m, ombro_m)
                    st.success("Medidas salvas!")
                    st.rerun()

        medidas = buscar_historico_medidas(username)
        if not medidas:
            st.info("Nenhuma medida registrada.")
        else:
            for m in medidas:
                try:
                    dt_m = datetime.strptime(m["data_registro"], "%Y-%m-%d").strftime("%d/%m/%Y")
                except:
                    dt_m = m["data_registro"]
                with st.container():
                    st.markdown(
                        f'<div class="hist-card">'
                        f'<b style="color:#22c55e;">⚖️ Registro: {dt_m}</b> &mdash; '
                        f'<b>Peso: {m["peso"]}kg</b> | BF: {m.get("percentual_gordura") or "-"}%<br>'
                        f'<span style="font-size:0.85rem;color:#aaa;">'
                        f'Braços: D {m.get("braço_direito") or "-"}cm / E {m.get("braço_esquerdo") or "-"}cm | '
                        f'Cintura: {m.get("cintura") or "-"}cm | Quadril: {m.get("quadril") or "-"}cm<br>'
                        f'Coxas: D {m.get("coxa_direita") or "-"}cm / E {m.get("coxa_esquerda") or "-"}cm | '
                        f'Panturrilhas: D {m.get("panturrilha_direita") or "-"}cm / E {m.get("panturrilha_esquerda") or "-"}cm'
                        f'</span></div>',
                        unsafe_allow_html=True
                    )
                    if st.button("🗑", key=f"del_m_{m['id']}"):
                        if deletar_medida(m["id"]):
                            st.rerun()

    # ── ABA PERFIL ──────────────────────────────────────────────────────────────
    elif st.session_state.aba_atual == "👤 Perfil":
        st.markdown('<h2 style="font-family:Bebas Neue,sans-serif;letter-spacing:.05em">Meu Perfil</h2>', unsafe_allow_html=True)
        
        if not st.session_state.editando_perfil:
            st.markdown(f"**Nome:** {perfil.get('nome')}")
            st.markdown(f"**Username:** {perfil.get('username')}")
            st.markdown(f"**Objetivo:** {perfil.get('objetivo')}")
            st.markdown(f"**Frequência Alvo:** {perfil.get('dias_por_semana')} dias/semana")
            st.markdown(f"**Tempo Disponível:** {perfil.get('tempo_disponivel')}")
            
            if st.button("✏️ Editar Perfil", type="primary", use_container_width=True):
                st.session_state.editando_perfil = True
                st.rerun()
        else:
            nome_ed     = st.text_input("Nome", value=perfil.get("nome",""))
            objetivo_ed = st.selectbox("Objetivo", OBJETIVOS, index=OBJETIVOS.index(perfil.get("objetivo")) if perfil.get("objetivo") in OBJETIVOS else 0)
            dias_ed     = st.selectbox("Dias por semana", [3,4,5,6], index=[3,4,5,6].index(perfil.get("dias_por_semana")) if perfil.get("dias_por_semana") in [3,4,5,6] else 0)
            tempo_ed    = st.selectbox("Tempo disponível", TEMPOS, index=TEMPOS.index(perfil.get("tempo_disponivel")) if perfil.get("tempo_disponivel") in TEMPOS else 0)
            
            c_salvar, c_cancelar = st.columns(2)
            with c_salvar:
                if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
                    res = atualizar_perfil(username, nome_ed, objetivo_ed, dias_ed, tempo_ed)
                    if res:
                        st.session_state.perfil = res
                        st.session_state.editando_perfil = False
                        st.success("Perfil atualizado!")
                        st.rerun()
            with c_cancelar:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.editando_perfil = False
                    st.rerun()
