import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

def login():
    # Se a senha já foi validada antes, não pede de novo
    if st.session_state.get("autenticado"):
        return True

    st.title("🔒 Acesso Restrito")
    senha_digitada = st.text_input("Digite a senha para acessar o painel:", type="password")
    
    # BUSCANDO A SENHA DO COFRE (SECRETS), NÃO DO CÓDIGO
    if st.button("Entrar"):
        if senha_digitada == st.secrets["password"]:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    return False

    # SÓ EXECUTA O APP SE O LOGIN DER TRUE
if login():
    def main():
        st.set_page_config(page_title="Controle Financeiro", layout="wide")
        
        # --- INICIALIZAÇÃO DO ESTADO ---
        if "form_count" not in st.session_state:
            st.session_state.form_count = 0

        st.title("💰 Controle Financeiro Pessoal")

        # Conectando à planilha
        conn = st.connection("gsheets", type=GSheetsConnection)

        # Função para ler dados com cache para performance
        @st.cache_data(ttl=60) # Atualiza a cada 1 min ou quando st.cache_data.clear() for chamado
        def get_data():
            try:
                return conn.read(ttl=0)
            except:
                return pd.DataFrame()

        df_historico = get_data()

        if not df_historico.empty:
            # --- PRÉ-PROCESSAMENTO DE DADOS ---
            # Garantir que a coluna Data é datetime
            df_historico["Data"] = pd.to_datetime(df_historico["Data"], dayfirst=True, errors='coerce')
            df_historico = df_historico.dropna(subset=["Data"]) # Remove linhas com datas inválidas
            
            # Filtros de Tempo
            hoje = datetime.now()
            mes_atual = hoje.month
            ano_atual = hoje.year

            # DataFrames Auxiliares
            df_pago = df_historico[df_historico["Pago"] == "Sim"]
            df_mes_atual = df_historico[
                (df_historico["Data"].dt.month == mes_atual) & 
                (df_historico["Data"].dt.year == ano_atual)
            ]
            df_pago_mes = df_mes_atual[df_mes_atual["Pago"] == "Sim"]

            
            
            # --- CÁLCULOS DE MÉTRICAS ---
            df_cartao = df_historico[df_historico["Forma de Pagamento"] == "Cartão de Crédito"]
            valor_cartao = abs(df_cartao["Valor"].sum())



            investimento = df_historico[(df_historico["Categoria"] == "Investimentos") & (df_historico["Pago"] == "Sim")]["Valor"].sum() 
            totalresgate = df_historico[(df_historico["Categoria"] == "Resgate Investimento") & (df_historico["Pago"] == "Sim")]["Valor"].sum() 
            totalinvestido = abs(investimento) - totalresgate
            
            caixinha = df_historico[(df_historico["Categoria"] == "Caixinha") & (df_historico["Pago"] == "Sim")]["Valor"].sum() 
            resgatecaixinha = df_historico[(df_historico["Categoria"] == "Resgate Caixinha") & (df_historico["Pago"] == "Sim")]["Valor"].sum() 
            totalcaixinha = abs(caixinha) - resgatecaixinha

            saldo_total = df_pago["Valor"].sum()
            total_pago_mes = df_pago_mes[df_pago_mes["Valor"] < 0]["Valor"].sum()
            receita_mes = df_pago_mes[df_pago_mes["Valor"] > 0]["Valor"].sum()
            
            faltapagar = df_historico[(df_historico["Pago"] == "Não") & (df_historico["Valor"] < 0)]["Valor"].sum()
            areceber = df_historico[(df_historico["Pago"] == "Não") & (df_historico["Valor"] > 0)]["Valor"].sum()
            saldofuturo = saldo_total + faltapagar + areceber

            # --- EXIBIÇÃO DE MÉTRICAS ---
            m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
            m1.metric("Saldo Atual", f"R$ {saldo_total:,.2f}")
            m2.metric("Falta Pagar", f"R$ {abs(faltapagar):,.2f}", delta_color="inverse")
            m3.metric("Pago (Mês)", f"R$ {abs(total_pago_mes):,.2f}")
            m4.metric("Cartão de Crédito", f"R$ {valor_cartao:,.2f}")
            m5.metric("Saldo Futuro", f"R$ {saldofuturo:,.2f}")
            m6.metric("Investido", f"R$ {totalinvestido:,.2f}")
            m7.metric("Caixinha", f"R$ {totalcaixinha:,.2f}")

            st.divider()

            # --- TABS ---
            tab_analise, tab_registro, tab_hist, tab_cartao = st.tabs([
                "📈 Análises", "📝 Registro", "📊 Histórico/Edição", "💳 Cartão"
            ])

            with tab_analise:
                st.header("Análise Mensal")
                c1, c2 = st.columns(2)

                with c1:
                    # Gráfico de Saldo Acumulado
                    df_acumulado = df_historico[df_historico["Pago"] == "Sim"].copy()
                    df_acumulado = df_acumulado.copy()
                    df_acumulado["Mes/Ano"] = df_acumulado["Data"].dt.to_period("M").dt.strftime("%m/%Y")
                    df_mes_agrupado = df_acumulado.groupby("Mes/Ano")["Valor"].sum().reset_index()
                    df_mes_agrupado["SaldoAcumulado"] = df_mes_agrupado["Valor"].cumsum()
                    
                # 1. Criar o gráfico de linha
                    fig_line = px.line(
                        df_mes_agrupado, 
                        x="Mes/Ano", 
                        y="SaldoAcumulado", 
                        title="Evolução do Saldo Acumulado", 
                        markers=True,
                        text="SaldoAcumulado" # <--- Define qual valor será o rótulo
                    )

                    # 2. Ajustar a fonte e a posição do texto
                    fig_line.update_traces(
                        textposition="top center", # Posição do número em relação ao ponto
                        texttemplate='R$ %{text:.2f}', # Formata como moeda no rótulo
                        textfont_size=12,           # Tamanho da fonte solicitado
                        cliponaxis=False            # Impede que o número seja cortado nas bordas
                    )

                    st.plotly_chart(fig_line, use_container_width=True)

                with c2:
                # --- GRÁFICO DE RECEITA VS DESPESA (MÊS ATUAL) ---
                    if not df_pago_mes.empty:
                        # 1. Agrupar os dados para consolidar os valores por tipo
                        df_resumo_atual = df_pago_mes.groupby("Tipo")["Valor"].sum().abs().reset_index()

                        fig_bar = px.bar(
                            df_resumo_atual, 
                            x="Tipo", 
                            y="Valor", 
                            color="Tipo",
                            text_auto='.2f',  # <--- ESSENCIAL: Habilita o rótulo de dados
                            title="Distribuição Receita/Despesa (Mês Atual)",
                            color_discrete_map={"Receita": "#2ecc71", "Despesa": "#e74c3c"}
                        )

                        # 2. Aplicar a configuração da fonte e posição do texto
                        fig_bar.update_traces(
                            textfont_size=12,      # Tamanho da fonte conforme solicitado
                            textangle=0,           # Mantém o texto reto para leitura fácil
                            textposition="outside", # Garante que o texto fique acima da barra
                            cliponaxis=False       # Evita que o número seja cortado no topo
                        )

                        # 3. Limpar o layout (opcional: remove a legenda já que o eixo X já identifica)
                        fig_bar.update_layout(showlegend=False, yaxis_title="Total (R$)")

                        st.plotly_chart(fig_bar, use_container_width=True)

                #Categorias mais gastas
                df_cat = df_historico[df_historico["Valor"] < 0].groupby("Categoria")["Valor"].sum().abs().reset_index().sort_values(by="Valor", ascending=False)
                fig_cat = px.bar(df_cat, x="Valor", y="Categoria",orientation='h',
                            title="Categorias com Maior Despesa", color="Valor", text_auto=True,
                            color_continuous_scale="Reds")
                fig_cat.update_traces(
                    textfont_size=12,      # Tamanho da fonte
                    textposition="outside" # Garante que o texto fique fora da barra se ela for pequena
                )
                fig_cat.update_layout(
                    yaxis={'categoryorder':'total ascending'}, # Ordena as categorias pelo valor total
                    coloraxis_showscale=False # Oculta a barra de escala de cor lateral para limpar o visual
                )
                st.plotly_chart(fig_cat, use_container_width=True)



                # Comparativo Mensal
                df_yoy = df_historico.copy()

                # 1. Ordenar por data antes de converter para string (garante ordem cronológica no gráfico)
                df_yoy = df_yoy.sort_values("Data")
                df_yoy["Mes/Ano"] = df_yoy["Data"].dt.to_period("M").astype(str)

                # 2. Agrupar e pivotar
                pivot_yoy = df_yoy.groupby(["Mes/Ano", "Tipo"])["Valor"].sum().abs().unstack().fillna(0).reset_index()

                # 3. Gerar o gráfico com text_auto ativado
                fig_comp = px.bar(
                    pivot_yoy, 
                    x="Mes/Ano", 
                    y=["Receita", "Despesa"], 
                    barmode="group", 
                    text_auto='.2f',  # <--- ESSENCIAL para mostrar os números
                    title="Planejamento Mensal: Receita vs Despesa",
                    color_discrete_map={"Receita": "#2ecc71", "Despesa": "#e74c3c"}
                )

                # 4. Ajustar estilo dos rótulos
                fig_comp.update_traces(
                    textfont_size=12,      
                    textangle=0,           # Mantém o texto na horizontal
                    textposition="outside", 
                    cliponaxis=False
                )

                fig_comp.update_layout(
                    yaxis_title="Valor (R$)",
                    xaxis_title="Mês",
                    legend_title="Tipo"
                )

                st.plotly_chart(fig_comp, use_container_width=True)

            
            with tab_registro:
                with st.form(key=f"form_{st.session_state.form_count}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        data_reg = st.date_input("Data", datetime.now())
                        cat_reg = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", 
                                                            "Fatura Cartão de Crédito", "Salário", "Investimentos",
                                                            "Resgate Investimento", "Caixinha", "Resgate Caixinha", "Outros"])
                    with col_b:
                        valor_reg = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
                        pago_reg = st.radio("Pago?", ["Sim", "Não"], horizontal=True)
                    
                    desc_reg = st.text_input("Descrição")
                    forma_reg = st.selectbox("Forma de Pagamento", ["Pix", "Dinheiro", "Cartão de Crédito", "Outros"])
                    obs_reg = st.text_area("Observação")
                    
                    if st.form_submit_button("🚀 Registrar"):
                        if desc_reg and valor_reg > 0:
                            # Lógica de sinal
                            valor_final = valor_reg if cat_reg in ['Salário', 'Resgate Investimento', 'Resgate Caixinha'] else -valor_reg
                            tipo_final = "Receita" if valor_final > 0 else "Despesa"
                            
                            new_row = pd.DataFrame([{
                                "Data": data_reg.strftime("%d/%m/%Y"),
                                "Descrição": desc_reg,
                                "Categoria": cat_reg,
                                "Valor": valor_final,
                                "Tipo": tipo_final,
                                "Pago": pago_reg,
                                "Observação": obs_reg,
                                "Forma de Pagamento": forma_reg
                            }])
                            
                            updated_df = pd.concat([df_historico, new_row], ignore_index=True)
                            conn.update(data=updated_df)
                            st.cache_data.clear()
                            st.session_state.form_count += 1
                            st.success("Registrado!")
                            st.rerun()
                        else:
                            st.error("Preencha descrição e valor!")

            with tab_hist:
                st.subheader("Editor de Dados")
                df_edit = st.data_editor(df_historico, use_container_width=True, num_rows="dynamic")
                if st.button("💾 Salvar Alterações"):
                    conn.update(data=df_edit)
                    st.cache_data.clear()
                    st.success("Atualizado!")
                    st.rerun()

            with tab_cartao:
                df_cartao = df_historico[df_historico["Forma de Pagamento"] == "Cartão de Crédito"]
                valor_cartao = abs(df_cartao["Valor"].sum())
                st.metric("Total Acumulado no Cartão", f"R$ {valor_cartao:,.2f}")
                st.dataframe(df_cartao, use_container_width=True)

        else:
            st.info("Nenhum dado encontrado. Comece registrando um lançamento.")
            # Replicar formulário de registro aqui se necessário...

    if __name__ == "__main__":
        main()